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
from ..core.LogRhythmManager import LogRhythmRESTManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import INTEGRATION_NAME, ADD_ALARM_TO_CASE_SCRIPT_NAME
from ..core.utils import string_to_multi_value


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_ALARM_TO_CASE_SCRIPT_NAME
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
    alarm_ids = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Alarm IDs", is_mandatory=True, print_value=True
        )
    )
    alarm_ids = [int(alarm_id) for alarm_id in alarm_ids]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = (f"Successfully added alarm evidence related to the case with ID "
                      f"{case_id} in {INTEGRATION_NAME}.")
    json_results = []

    try:
        manager = LogRhythmRESTManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        case_alarms, alarms_already_part_of_case = manager.add_alarms_to_case(
            case_id, alarm_ids
        )
        json_results.extend([case_alarm.as_json() for case_alarm in case_alarms])
        if alarms_already_part_of_case:
            output_message = (
                f"All of the provided alarm evidence was already a part of the case "
                f"with ID {case_id} in {INTEGRATION_NAME}."
            )
        if json_results:
            siemplify.result.add_result_json(json_results)

    except Exception as e:
        output_message = (
            f"Error executing action '{ADD_ALARM_TO_CASE_SCRIPT_NAME}'. Reason: {e}"
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
