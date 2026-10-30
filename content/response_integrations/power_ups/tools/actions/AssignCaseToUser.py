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

from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.rest.soar_api import assign_case_to_user

ACTION_NAME = "AssignCaseToUser"


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME

    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        case_id = siemplify.extract_action_param(
            param_name="Case Id",
            is_mandatory=True,
            print_value=True,
        )
        assign_to = siemplify.extract_action_param(
            param_name="Assign To",
            default_value="@Admin",
            is_mandatory=True,
            print_value=True,
        )
        alert_id = siemplify.extract_action_param(
            param_name="Alert Id",
            default_value="id",
            print_value=True,
        )

        response = assign_case_to_user(
            chronicle_soar=siemplify,
            case_id=case_id,
            assign_to=assign_to,
            alert_identifier=alert_id,
        )
        siemplify.LOGGER.info(f"Assign case response: {response}")

        json_result: dict[str, Any] = {
            "caseId": case_id,
            "assignedTo": assign_to,
        }
        if response:
            json_result["response"] = response

        siemplify.result.add_result_json(json_result)
        output_message = f"Successfully assigned case {case_id} to {assign_to}."

    except Exception as e:
        output_message = f"Error executing action '{ACTION_NAME}'. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
