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

import validators
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from ..core.consts import (
    ANALYSIS_RESULTS,
    DEFAULT_X_LAST_SCANS_GET_RESULTS,
    FILE,
    GET_ANALYSIS_RESULTS,
    INTEGRATION_NAME,
    THRESHOLD,
    URL,
)
from ..core.exceptions import LastlineAuthenticationException, LastlineInvalidParamException
from ..core.LastlineManager import LastlineManager
from ..core.utils import get_file_hash


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {GET_ANALYSIS_RESULTS}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=True,
        is_mandatory=False,
        print_value=True,
    )

    create_insight = extract_action_param(
        siemplify,
        param_name="Create Insight?",
        is_mandatory=False,
        print_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    output_message = ""
    try:
        threshold = extract_action_param(
            siemplify,
            param_name="Threshold",
            is_mandatory=True,
            print_value=True,
            input_type=int,
            default_value=THRESHOLD,
        )

        search_in_last_x_scans = extract_action_param(
            siemplify,
            param_name="Search in last x scans",
            is_mandatory=True,
            print_value=True,
            input_type=int,
            default_value=DEFAULT_X_LAST_SCANS_GET_RESULTS,
        )

        manager = LastlineManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        enriched_entities = []
        json_results = {}
        for entity in siemplify.target_entities:
            # Check if the entity is URL or file hash

            siemplify.LOGGER.info(f"Started processing entity {entity.identifier}")
            try:
                submission_type = URL if entity.entity_type == EntityTypes.URL else FILE

                url = None
                if entity.entity_type == EntityTypes.URL:
                    url = entity.identifier
                    if not validators.url(url):
                        msg = "Invalid URL!"
                        raise LastlineInvalidParamException(msg)

                file_sha1 = None
                file_md5 = None
                if entity.entity_type == EntityTypes.FILEHASH:
                    file_sha1, file_md5 = get_file_hash(entity.identifier)

                if entity.entity_type not in {EntityTypes.URL, EntityTypes.FILEHASH}:
                    output_message += (
                        f"Entity type {entity.entity_type} is not supported by the action, only URL "
                        f"or Filehash are supported, skipping this entity type\n"
                    )
                    continue

                siemplify.LOGGER.info(f"Fetching analysis of url: {entity.identifier}")
                analysis = manager.search_analysis_history(
                    submission_type=submission_type,
                    search_in_last_x_scans=search_in_last_x_scans,
                    url=url,
                    file_md5=file_md5,
                    file_sha1=file_sha1,
                )

                if not analysis.data:
                    siemplify.LOGGER.info(
                        f"There is no successful analysis that have been made for: {entity.identifier}"
                    )
                    continue

                siemplify.LOGGER.info(
                    f"Successfully fetched analysis of url: {entity.identifier}"
                )

                task_uuid = analysis.data[0].task_uuid

                siemplify.LOGGER.info(f"Fetching report of url: {entity.identifier}")
                submission_task_report = manager.get_result(
                    uuid=task_uuid, is_get_process=False
                )
                siemplify.LOGGER.info(
                    f"Successfully fetched report of url: {entity.identifier}"
                )

                # Insight
                if create_insight:
                    siemplify.LOGGER.info(
                        f"Creating insight for entity: {entity.identifier}"
                    )
                    entity_type = URL if submission_type == URL else "File"

                    siemplify.add_entity_insight(
                        entity,
                        submission_task_report.as_insight(
                            entity.identifier, entity_type
                        ),
                        triggered_by=INTEGRATION_NAME,
                    )
                siemplify.LOGGER.info(
                    f"Created insight for entity: {entity.identifier}"
                )

                siemplify.LOGGER.info(
                    f"Creating JSON results for entity: {entity.identifier}"
                )
                json_results[entity.identifier] = submission_task_report.as_json()
                siemplify.LOGGER.info(
                    f"Created JSON results for entity: {entity.identifier}"
                )

                siemplify.LOGGER.info(
                    f"Creating CSV results for entity: {entity.identifier}"
                )
                siemplify.result.add_data_table(
                    ANALYSIS_RESULTS.format(entity.identifier),
                    construct_csv([submission_task_report.as_table(submission_type)]),
                )
                siemplify.LOGGER.info(
                    f"Created CSV results for entity: {entity.identifier}"
                )

                siemplify.LOGGER.info(f"Enriching entity: {entity.identifier}")
                # Enrich entity
                if submission_task_report.data.score > threshold:
                    siemplify.LOGGER.info("The entity will be mark as suspicious")
                    entity.is_suspicious = True

                enrichment_data = submission_task_report.as_table(
                    submission_type, is_enrichment=True
                )
                entity.additional_properties.update(enrichment_data)
                entity.is_enriched = True
                enriched_entities.append(entity)

                siemplify.LOGGER.info(f"Enriched entity: {entity.identifier}")

                output_message += (
                    f"Successfully fetched the analysis results for the {submission_type} "
                    f"{entity.identifier}\n"
                )

            except LastlineInvalidParamException as error:
                siemplify.LOGGER.error(error)
                output_message += (
                    f"Failed to fetch the analysis results for the {submission_type} "
                    f"{entity.identifier}\n"
                )

        if enriched_entities:
            result_value = True
            siemplify.update_entities(enriched_entities)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

        else:
            output_message += "No previously completed analysis tasks were found based on the provided entities\n"

        status = EXECUTION_STATE_COMPLETED

    except LastlineAuthenticationException as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to connect to the {INTEGRATION_NAME} service with the provided account. Please "
            f"check your configuration. Error is: {error}\n"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action: {GET_ANALYSIS_RESULTS}. Reason: {error}."
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
