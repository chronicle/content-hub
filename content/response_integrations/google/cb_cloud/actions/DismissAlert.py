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
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from ..core.CBCloudManager import CBCloudManager
from ..core.constants import (
    ALERT_CLOSE_REASON,
    ALERT_DETERMINATION,
    DISMISS_ALERT_SCRIPT_NAME,
    INTEGRATION_NAME,
    PROVIDER_NAME,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DISMISS_ALERT_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

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

    alert_id = extract_action_param(
        siemplify, param_name="Alert ID", is_mandatory=True, print_value=True
    )
    remediation_state = extract_action_param(
        siemplify, param_name="Reason for dismissal", print_value=True
    )
    comment = extract_action_param(
        siemplify, param_name="Message for alert dismissal", print_value=True
    )
    determination = extract_action_param(
        siemplify, param_name="Determination", print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = (
        f"Successfully dismissed {PROVIDER_NAME} alert with alert id {alert_id}"
    )

    try:
        remediation_state = ALERT_CLOSE_REASON.get(remediation_state)
        determination = ALERT_DETERMINATION.get(determination)
        manager = CBCloudManager(
            api_root=api_root,
            org_key=org_key,
            api_id=api_id,
            api_secret_key=api_secret_key,
            verify_ssl=verify_ssl,
        )
        manager.validate_alert(alert_id=alert_id)
        manager.dismiss_alert(
            alert_id=alert_id,
            remediation_state=remediation_state,
            determination=determination,
            comment=comment,
        )

    except Exception as e:
        output_message = (
            f"Error executing action {DISMISS_ALERT_SCRIPT_NAME}. Reason: {e}"
        )
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
