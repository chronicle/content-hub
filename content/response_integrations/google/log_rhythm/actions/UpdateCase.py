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
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.LogRhythmManager import LogRhythmRESTManager
from ..core.constants import (
    INTEGRATION_NAME,
    UPDATE_CASE_SCRIPT_NAME,
    CASE_STATUS_MAPPING,
    CASE_PRIORITY_MAPPING,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_CASE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    case_id = extract_action_param(
        siemplify, param_name="Case ID", is_mandatory=True, print_value=True
    )
    name = extract_action_param(siemplify, param_name="Name", print_value=True)
    priority = extract_action_param(
        siemplify, param_name="Priority", default_value="Select One", print_value=True
    )
    due_date = extract_action_param(siemplify, param_name="Due Date", print_value=True)
    description = extract_action_param(
        siemplify, param_name="Description", print_value=True
    )
    resolution = extract_action_param(
        siemplify, param_name="Resolution", print_value=True
    )
    case_status = extract_action_param(
        siemplify, param_name="Status", default_value="Select One", print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = f"Successfully updated case {case_id} in {INTEGRATION_NAME}."
    priority = CASE_PRIORITY_MAPPING.get(priority)
    case_status = CASE_STATUS_MAPPING.get(case_status)
    try:
        manager = LogRhythmRESTManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )

        if not priority and not case_status:
            if not any([name, due_date, description, resolution]):
                raise Exception(
                    "at least one of the action parameters "
                    "should have a provided value."
                )

        if case_status:
            case = manager.update_case_status(case_id=case_id, case_status=case_status)
        if priority or any([name, due_date, description, resolution]):
            case = manager.update_case(
                case_id=case_id,
                name=name,
                priority=priority,
                due_date=due_date,
                description=description,
                resolution=resolution,
            )

        siemplify.result.add_result_json(case.as_json())

    except Exception as e:
        output_message = (
            f"Error executing action {UPDATE_CASE_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"is_success: {result_value}\n  "
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
