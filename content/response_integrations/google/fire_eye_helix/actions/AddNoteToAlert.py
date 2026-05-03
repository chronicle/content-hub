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
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.FireEyeHelixConstants import PROVIDER_NAME, ADD_NOTE_TO_ALERT_SCRIPT_NAME
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.FireEyeHelixManager import FireEyeHelixManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.FireEyeHelixExceptions import FireEyeHelixNotFoundAlertException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_NOTE_TO_ALERT_SCRIPT_NAME
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Init Integration Configurations
    api_root = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="API Root", is_mandatory=True
    )

    api_token = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Token",
        is_mandatory=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
    )

    # Init Action Parameters
    alert_id = extract_action_param(siemplify, param_name="Alert ID", is_mandatory=True)
    note = extract_action_param(siemplify, param_name="Note", is_mandatory=True)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = FireEyeHelixManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )
        manager.add_note_to_alert(alert_id, note)
        output_message = f"Successfully added a note to the alert with ID {alert_id} in FireEye Helix."

    except FireEyeHelixNotFoundAlertException:
        output_message = (
            "Action wasn't able to add a note to the alert with ID {id} in FireEye Helix. "
            "Reason: Alert with ID {id} wasn't found.".format(id=alert_id)
        )
        result_value = False
    except Exception as e:
        output_message = f'Error executing action "Add Note To Alert". Reason: {e}'
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
