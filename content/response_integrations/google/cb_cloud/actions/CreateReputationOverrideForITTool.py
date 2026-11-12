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
from TIPCommon.extraction import extract_configuration_param, extract_action_param

from ..core.CBCloudManager import CBCloudManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    unix_now,
    convert_unixtime_to_datetime,
    output_handler,
    convert_dict_to_json_result_dict,
)
from ..core.constants import (
    INTEGRATION_NAME,
    CREATE_REPUTATION_OVERRIDE_FOR_IT_TOOL_SCRIPT_NAME,
    NOT_SPECIFIED,
    NEW_LINE,
)
from ..core.utils import get_entity_original_identifier


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_REPUTATION_OVERRIDE_FOR_IT_TOOL_SCRIPT_NAME

    siemplify.LOGGER.info("================= Main - Param Init =================")

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

    file_name = extract_action_param(
        siemplify, param_name="File Name", is_mandatory=False, print_value=True
    )
    file_path = extract_action_param(
        siemplify, param_name="File Path", is_mandatory=True, print_value=True
    )
    description = extract_action_param(
        siemplify, param_name="Description", is_mandatory=False, print_value=True
    )
    reputation_override_list = extract_action_param(
        siemplify,
        param_name="Reputation Override List",
        is_mandatory=True,
        default_value=NOT_SPECIFIED,
        print_value=True,
    )
    include_child_processes = extract_action_param(
        siemplify,
        param_name="Include Child Processes",
        is_mandatory=False,
        print_value=True,
        input_type=bool,
        default_value=False,
    )
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED
    successful_entities, failed_entities, json_results = [], [], {}

    filenames = (
        [file_name]
        if file_name
        else [
            get_entity_original_identifier(entity)
            for entity in siemplify.target_entities
            if entity.entity_type == EntityTypes.FILENAME
        ]
    )

    try:
        if reputation_override_list == NOT_SPECIFIED:
            raise Exception("Reputation Override List is not specified.")
        if not filenames:
            raise Exception(
                "Action failed to start since Filename was not provided either as Siemplify Entity or "
                "action input parameter."
            )
        manager = CBCloudManager(
            api_root=api_root,
            org_key=org_key,
            api_id=api_id,
            api_secret_key=api_secret_key,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        for file in filenames:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline "
                    f"({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) "
                    f"has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                siemplify.LOGGER.info(
                    f"Creating reputation override for path: {file_path}{file}"
                )
                reputation = manager.create_it_tool_reputation_override(
                    override_list=reputation_override_list,
                    path=f"{file_path}{file}",
                    description=description,
                    include_child_processes=include_child_processes,
                )
                json_results[file] = reputation.to_json()
                successful_entities.append(file)
                siemplify.LOGGER.info(f"Finished processing entity: {file}")
            except Exception as e:
                failed_entities.append(file)
                siemplify.LOGGER.error(f"An error occurred on entity: {file}")
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message = "Successfully created reputation override for the following entities:\n   {}".format(
                f"{NEW_LINE}   ".join(successful_entities)
            )
            result_value = True
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            if failed_entities:
                output_message += "Action failed to to create reputation override for the following entities:\n   {}".format(
                    f"{NEW_LINE}   ".join(failed_entities)
                )
        else:
            output_message = "No reputation overrides were created."

    except Exception as e:
        output_message = f"Error executing action {CREATE_REPUTATION_OVERRIDE_FOR_IT_TOOL_SCRIPT_NAME}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
