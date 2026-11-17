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
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.CBCloudManager import CBCloudManager
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    EXECUTE_ENTITY_PROCESSES_SEARCH_SCRIPT_NAME,
    PROCESS_SEARCH_RESULTS_TABLE_NAME,
)
from ..core.utils import get_entity_original_identifier

SUPPORTED_ENTITIES = [
    EntityTypes.ADDRESS,
    EntityTypes.HOSTNAME,
    EntityTypes.FILEHASH,
    EntityTypes.PROCESS,
    EntityTypes.USER,
]
THREAT_CATEGORY = "THREAT"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_ENTITY_PROCESSES_SEARCH_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    org_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Organization Key",
        is_mandatory=True,
    )
    api_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API ID",
        is_mandatory=True,
    )
    api_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Secret Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    start = extract_action_param(
        siemplify, param_name="Start from Row", input_type=int, print_value=True
    )
    max_rows_to_return = extract_action_param(
        siemplify,
        param_name="Max Rows to Return",
        default_value=50,
        input_type=int,
        print_value=True,
    )
    create_insight = extract_action_param(
        siemplify,
        param_name="Create Insight",
        default_value=False,
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    successful_entities, failed_entities, enriched_entities, json_results = (
        [],
        [],
        [],
        {},
    )
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITIES
    ]

    try:
        manager = CBCloudManager(
            api_root=api_root,
            org_key=org_key,
            api_id=api_id,
            api_secret_key=api_secret_key,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )

        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)

            try:
                siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")

                events = manager.get_events_by_process_name(
                    process_name=entity_identifier,
                    entity_type=entity.entity_type,
                    start=start,
                    rows=max_rows_to_return,
                )
                if not events.results:
                    failed_entities.append(entity_identifier)
                    continue

                detailed_events = manager.get_detailed_events_information(
                    events.process_guids
                )
                if not detailed_events.results:
                    failed_entities.append(entity_identifier)
                    continue

                json_results[entity_identifier] = detailed_events.to_json()
                successful_entities.append(entity_identifier)

                for event in detailed_events.results:
                    if THREAT_CATEGORY in event.alert_category and event.alert_id:
                        entity.is_suspicious = True
                        enriched_entities.append(entity)
                        entity.is_enriched = True
                        break

                if create_insight:
                    siemplify.add_entity_insight(
                        entity,
                        detailed_events.to_insight(entity_identifier=entity_identifier),
                    )
                siemplify.result.add_data_table(
                    f"{entity_identifier} {PROCESS_SEARCH_RESULTS_TABLE_NAME}",
                    construct_csv(
                        [event.to_csv() for event in detailed_events.results]
                    ),
                )

            except Exception as e:
                failed_entities.append(entity_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message = (
                f"Process information was found for the following entities:\n "
                f"{', '.join(successful_entities)}\n"
            )
            siemplify.update_entities(enriched_entities)

            if failed_entities:
                output_message += (
                    f"Action was not able to find process information for the following provided "
                    f"entities:\n {', '.join(failed_entities)} \n"
                )
        else:
            output_message = (
                "Process information was not found for all of the provided entities. \n"
            )
            result_value = False

        if json_results:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
    except Exception as e:
        output_message = f"Error executing action {EXECUTE_ENTITY_PROCESSES_SEARCH_SCRIPT_NAME}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
