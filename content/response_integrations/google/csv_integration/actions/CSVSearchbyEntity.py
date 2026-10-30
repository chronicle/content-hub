# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler

from TIPCommon.transformation import add_prefix_to_dict, construct_csv
from TIPCommon.extraction import extract_action_param

from csv_integration.core.constants import (
    SEARCH_BY_ENTITY_SCRIPT_NAME,
    RECORDS_TABLE_NAME,
    ENRICHMENT_PREFIX,
    FOUND_IN_CSV_INSIGHT_NAME,
)
from csv_integration.core.CSVManager import CSVManager, FILE_ENCODINGS_DEFAULT
from csv_integration.core.exceptions import CSVEncodingException
from csv_integration.core.utils import (
    get_encodings_or_raise,
    get_value_for_search,
    list_of_dict_to_single_dict,
    string_to_multi_value,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SEARCH_BY_ENTITY_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    csv_folder_or_file_path = extract_action_param(
        siemplify, param_name="CSV Path", print_value=True
    )
    searchable_columns = string_to_multi_value(
        extract_action_param(siemplify, param_name="CSV Column", print_value=True),
        only_unique=True,
    )
    days_back = extract_action_param(
        siemplify, param_name="Days Back", print_value=True
    )

    mark_as_suspicious = extract_action_param(
        siemplify,
        param_name="Mark As Suspicious",
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    enrich_entities = extract_action_param(
        siemplify,
        param_name="Enrich Entities",
        default_value=True,
        input_type=bool,
        print_value=True,
    )
    create_insight = extract_action_param(
        siemplify,
        param_name="Create Insight",
        default_value=True,
        input_type=bool,
        print_value=True,
    )
    fields_to_return = string_to_multi_value(
        extract_action_param(
            siemplify=siemplify, param_name="Fields To Return", print_value=True
        ),
        only_unique=True,
    )
    return_the_first_row = extract_action_param(
        siemplify,
        param_name="Return the first row only",
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    file_encodings_list = string_to_multi_value(
        extract_action_param(
            siemplify=siemplify,
            param_name="File Encoding Types",
            default_value=",".join(FILE_ENCODINGS_DEFAULT),
            print_value=True,
        )
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    (
        found_entities,
        not_found_entities,
        json_result,
        csv_tables_data,
        enrichments_data,
    ) = (set(), set(), {}, {}, {})
    entities_to_update = set()
    result_value = 0

    suitable_entities = {
        entity.identifier: entity for entity in siemplify.target_entities
    }

    try:
        file_encodings_list = get_encodings_or_raise(siemplify, file_encodings_list)

        manager = CSVManager(siemplify)

        for csv_path in manager.get_relevant_csv_files(
            csv_folder_or_file_path, days_back=days_back
        ):
            siemplify.LOGGER.info(f'Processing "{csv_path}"')
            try:
                for identifier, entity in suitable_entities.items():
                    search_result = manager.search_in_csv(
                        csv_content=manager.read_csv(csv_path, file_encodings_list),
                        value_to_search=get_value_for_search(identifier),
                        return_the_first_match=return_the_first_row,
                        searchable_columns=searchable_columns,
                    )
                    siemplify.LOGGER.info(
                        f'Found {len(search_result)} rows in file "{csv_path}" for value "{identifier}"'
                    )
                    if not search_result:
                        not_found_entities.add(identifier)
                        continue

                    found_entities.add(identifier)
                    json_result[identifier] = json_result.get(identifier, [])
                    csv_tables_data[identifier] = csv_tables_data.get(identifier, [])
                    enrichments_data[identifier] = enrichments_data.get(identifier, [])

                    for csv_item in search_result:
                        csv_item.additional_data = {"file_source_path": csv_path}
                        csv_item.column_filter = fields_to_return
                        csv_item.get_process_data()
                        json_result[identifier].append(csv_item.to_json())
                        if csv_item.filtered_data_exist:
                            csv_tables_data[identifier].append(csv_item.to_csv())
                            enrichments_data[identifier].append(
                                csv_item.get_enrichment_data()
                            )

                    if create_insight:
                        siemplify.add_entity_insight(
                            entity, FOUND_IN_CSV_INSIGHT_NAME.format(csv_path)
                        )

            except CSVEncodingException as e:
                siemplify.LOGGER.exception(e)
                siemplify.LOGGER.error(
                    "Please provide right encoding's for reading csv file's"
                )
                raise

        for entity_identifier, enrichment_data in enrichments_data.items():
            if not enrichment_data:
                continue
            entity = suitable_entities[entity_identifier]
            if enrich_entities:
                entity.is_enriched = True
                entity.additional_properties.update(
                    add_prefix_to_dict(
                        list_of_dict_to_single_dict(enrichment_data), ENRICHMENT_PREFIX
                    )
                )

            if mark_as_suspicious:
                siemplify.LOGGER.info(
                    f"Entity '{entity_identifier}' marked as suspicious."
                )
                entity.is_suspicious = True

            if enrich_entities or mark_as_suspicious:
                entities_to_update.add(entity)

        if found_entities:
            siemplify.LOGGER.info(f"Total updated entities: {len(entities_to_update)}.")
            siemplify.update_entities(entities_to_update)
            result_value = sum(map(len, json_result.values()))
            output_message = "Successfully found information about the following entities:\n   {}\n".format(
                "\n   ".join(found_entities)
            )
            not_found_entities_in_all_files = [
                value for value in not_found_entities if value not in found_entities
            ]
            if not_found_entities_in_all_files:
                output_message += "No information was found about the following entities:\n   {}\n".format(
                    "\n   ".join(not_found_entities_in_all_files)
                )
        else:
            output_message = "No information was found for the provided entities."

        for search_value, csv_table in csv_tables_data.items():
            if not csv_table:
                continue

            siemplify.result.add_data_table(
                RECORDS_TABLE_NAME.format(search_value), construct_csv(csv_table)
            )
        if json_result:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )

    except Exception as e:
        output_message = (
            f"Error executing action {SEARCH_BY_ENTITY_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
