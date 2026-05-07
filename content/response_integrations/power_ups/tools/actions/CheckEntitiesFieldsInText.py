# Copyright 2025 Google LLC
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

import copy
import json
import re
from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler

from ..core.ToolsCommon import (
    ExecutionScope,
    get_execution_scope,
    get_target_entities,
)


def get_entity_object_by_identifier(
    target_entities: list[Any], identifier: str
) -> Any | None:
    """Find an entity object in target entities list by case-insensitive identifier.

    Args:
        target_entities: Pre-extracted list of target entities to search.
        identifier: The target identifier to locate.

    Returns:
        The matching Entity SDK object if found, otherwise None.
    """
    for entity in target_entities:
        if identifier.lower() == entity.identifier.lower():
            return entity
    return None


@output_handler
def main() -> None:
    """Execute CheckEntitiesFieldsInText action."""
    siemplify = SiemplifyAction()

    try:
        status = EXECUTION_STATE_COMPLETED
        output_message = ""
        failed_entities = []
        successfull_entities = []
        json_result = {}

        fields_json = json.loads(siemplify.parameters.get("FieldsInput"))
        search_data_json = json.loads(siemplify.parameters.get("SearchInData"))
        enrich_key = siemplify.parameters.get("ShouldEnrichEntity", "")
        is_case_sensitive = (
            siemplify.parameters.get("IsCaseSensitive").lower() == "true"
        )

        raw_scope = getattr(siemplify, "execution_scope", ExecutionScope.Alert.value)
        execution_scope = get_execution_scope(raw_scope, logger=siemplify.LOGGER)
        target_entities = get_target_entities(
            execution_scope=execution_scope,
            target_entities=siemplify.target_entities,
            case_alerts=getattr(siemplify.case, "alerts", []),
        )

        for entity in target_entities:
            try:
                entity_fields_json = copy.deepcopy(fields_json)
                for item in entity_fields_json:
                    item_results = []
                    if item.get("RegexForFieldName"):
                        for key in entity.additional_properties.keys():
                            if re.search(item.get("RegexForFieldName"), key):
                                item_results.append(
                                    {
                                        "key": key,
                                        "val": entity.additional_properties.get(key),
                                    },
                                )
                    else:
                        item_results.append(
                            {
                                "key": item["FieldName"],
                                "val": entity.additional_properties.get(
                                    item["FieldName"],
                                ),
                            },
                        )

                    item_results = [x for x in item_results if x["val"]]

                    if item.get("RegexForFieldValue"):
                        values_post_regex = []
                        for val in item_results:
                            post_regex_val = re.findall(
                                item.get("RegexForFieldValue"),
                                val["val"],
                            )
                            if isinstance(post_regex_val, list):
                                values_post_regex.append(
                                    [
                                        {"key": item["FieldName"], "val": x}
                                        for x in post_regex_val
                                    ],
                                )
                            else:
                                values_post_regex.append(
                                    [{"key": item["FieldName"], "val": post_regex_val}],
                                )
                        item["ResultsToSearch"] = {"val_to_search": values_post_regex}
                    else:
                        item["ResultsToSearch"] = {"val_to_search": [item_results]}
                    item["ResultsToSearch"]["found_results"] = []
                    item["ResultsToSearch"]["num_of_results"] = 0

                    regex_for_search_field = item.get("RegEx")
                    if not regex_for_search_field:
                        regex_for_search_field = ".*"
                    for search_item in search_data_json:
                        search_string = re.findall(
                            regex_for_search_field, search_item["Data"]
                        )
                        if isinstance(search_string, list):
                            search_item["search_string"] = " ".join(search_string)
                        else:
                            search_item["search_string"] = search_string
                json_result[entity.identifier] = entity_fields_json
            except Exception as e:
                failed_entities.append(entity.identifier)
                siemplify.LOGGER.error(
                    f"Failed to process entity: {entity.identifier}."
                )
                siemplify.LOGGER.exception(e)

        for entity_id, entity_data in json_result.items():
            for item in entity_data:
                for vals in item["ResultsToSearch"]["val_to_search"]:
                    for search_in_item in search_data_json:
                        for val in vals:
                            if (
                                is_case_sensitive
                                and val["val"] in search_in_item.get("search_string")
                            ) or (
                                not is_case_sensitive
                                and val["val"].lower()
                                in search_in_item.get("search_string").lower()
                            ):
                                item["ResultsToSearch"]["found_results"].append(
                                    {
                                        "to_search": val,
                                        "searched_in": search_in_item.get(
                                            "search_string",
                                        ),
                                    },
                                )
                                item["ResultsToSearch"]["num_of_results"] = (
                                    1 + item["ResultsToSearch"]["num_of_results"]
                                )

                                ent = get_entity_object_by_identifier(
                                    target_entities,
                                    entity_id,
                                )
                                if ent:
                                    successfull_entities.append(ent)
                                    if enrich_key:
                                        ent.additional_properties[enrich_key] = True

        if enrich_key:
            siemplify.update_entities(successfull_entities)

        if json_result:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result),
            )

        if successfull_entities:
            unique_entity_identifiers = list(
                set([x.identifier for x in successfull_entities]),
            )
            output_message += "Successfully processed entities:\n   {}".format(
                "\n   ".join(unique_entity_identifiers),
            )
        else:
            output_message += "No entities were processed."

        result_value = len(successfull_entities)

        if failed_entities:
            output_message += (
                "\n" if output_message else ""
            ) + "Failed processing entities:\n   {}".format(
                "\n   ".join(failed_entities),
            )
            status = EXECUTION_STATE_FAILED

    except Exception as e:
        status = EXECUTION_STATE_FAILED
        result_value = "Failed"
        output_message += (
            "\n" if output_message else ""
        ) + f"Error executing action 'CheckEntitiesFieldsInText'. Reason: {e}."
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
