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
from soar_sdk.Siemplify import InsightSeverity, InsightType
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon import (
    extract_action_param,
    extract_configuration_param,
    flat_dict_to_csv,
)

from ..core.constants import (
    ENRICH_ENTITIES_ACTION,
    HTTP_SCHEMA,
    HTTPS_SCHEMA,
    INTEGRATION_NAME,
)
from ..core.SplashExceptions import EntityNotFoundException
from ..core.SplashManager import SplashManager

SUPPORTED_ENTITY_TYPES = [EntityTypes.URL, EntityTypes.ADDRESS]
ENRICHMENT_PREFIX = "Splash"
INSIGHT_TITLE = "General Info"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENTITIES_ACTION

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    create_insight = extract_action_param(
        siemplify, param_name="Create Insight", print_value=True, input_type=bool
    )
    include_png = extract_action_param(
        siemplify,
        param_name="Include PNG Screenshot",
        print_value=True,
        input_type=bool,
    )
    include_history = extract_action_param(
        siemplify, param_name="Include History", print_value=True, input_type=bool
    )
    include_har = extract_action_param(
        siemplify, param_name="Include HAR", print_value=True, input_type=bool
    )

    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    json_results = {}
    successful_entities, failed_entities = [], []
    successful_endpoints = []

    try:
        manager = SplashManager(
            api_root=api_root, verify_ssl=verify_ssl, siemplify_logger=siemplify.LOGGER
        )

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            identifier = (
                entity.identifier.lower()
                if HTTP_SCHEMA in entity.identifier.lower()
                or HTTPS_SCHEMA in entity.identifier.lower()
                else f"{HTTPS_SCHEMA}{entity.identifier.lower()}"
            )

            try:
                entity_details = manager.get_entity_data(
                    identifier=identifier,
                    include_history=include_history,
                    include_har=include_har,
                )

                if entity_details:
                    json_results[entity.identifier] = entity_details.to_json()
                    entity.additional_properties.update(
                        entity_details.get_enrichment_data(
                            include_history=include_history,
                            include_har=include_har,
                            prefix=ENRICHMENT_PREFIX,
                        )
                    )
                    successful_entities.append(entity)
                    successful_endpoints.append(
                        entity_details.to_insight(include_screenshot=include_png)
                    )
                    entity.is_enriched = True
                    siemplify.result.add_entity_table(
                        f"{entity.identifier}",
                        flat_dict_to_csv(
                            entity_details.as_csv(
                                include_history=include_history, include_har=include_har
                            )
                        ),
                    )
                    siemplify.result.add_entity_attachment(
                        entity_identifier=entity.identifier,
                        filename=f"{entity.identifier}.png",
                        file_contents=entity_details.png,
                    )
                else:
                    failed_entities.append(entity)
            except EntityNotFoundException as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        if successful_entities:
            output_message = (
                f"Successfully enriched the following entities using information from "
                f"{INTEGRATION_NAME}: {', '.join([entity.identifier for entity in successful_entities])}\n"
            )
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            siemplify.update_entities(successful_entities)

            if successful_endpoints and create_insight:
                siemplify.create_case_insight(
                    triggered_by=INTEGRATION_NAME,
                    title=INSIGHT_TITLE,
                    content="".join(successful_endpoints),
                    entity_identifier="",
                    severity=InsightSeverity.INFO,
                    insight_type=InsightType.General,
                )

            if failed_entities:
                output_message += (
                    f"Action wasn't able to enrich the following entities using information from "
                    f"{INTEGRATION_NAME}: {', '.join([entity.identifier for entity in failed_entities])}"
                )
        else:
            output_message = "None of the provided entities were enriched."
            result_value = False

    except Exception as e:
        output_message = f'Error executing action "Enrich Entities". Reason: {e}.'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
