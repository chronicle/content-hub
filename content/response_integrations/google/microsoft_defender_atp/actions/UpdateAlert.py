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

from ..core.constants import LOGIN_API_ROOT_DEFAULT, PROVIDER_NAME, UPDATE_ALERT_SCRIPT_NAME
from ..core.MicrosoftDefenderATPManager import (
    MicrosoftDefenderATPManager,
    MicrosoftDefenderATPError,
    MicrosoftDefenderATPValidationError,
)
from ..core.UtilsManager import DefenderATPManagerConfig, init_defender_atp_manager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_ALERT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    login_api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Login API Root",
        default_value=LOGIN_API_ROOT_DEFAULT,
        is_mandatory=True,
    )

    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Api Root",
        input_type=str,
        is_mandatory=True,
    )

    graph_api_root = extract_configuration_param(
        siemplify=siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Graph API Root",
        print_value=True,
    )

    client_id = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Client ID",
        input_type=str,
        is_mandatory=True,
    )

    client_secret = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Client Secret",
        input_type=str,
        is_mandatory=True,
    )

    tenant_id = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Azure Active Directory ID",
        input_type=str,
        is_mandatory=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        default_value=False,
    )

    alert_id = extract_action_param(
        siemplify, param_name="Alert ID", input_type=str, is_mandatory=True
    )

    status = extract_action_param(
        siemplify, param_name="Status", input_type=str, is_mandatory=False
    )

    assigned_to = extract_action_param(
        siemplify, param_name="Assigned To", input_type=str, is_mandatory=False
    )

    classification = extract_action_param(
        siemplify, param_name="Classification", input_type=str, is_mandatory=False
    )

    determination = extract_action_param(
        siemplify, param_name="Determination", input_type=str, is_mandatory=False
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    # Validation block
    validation_errors = []

    if status:
        try:
            MicrosoftDefenderATPManager.validate_statuses(status)
        except MicrosoftDefenderATPValidationError as e:
            validation_errors.append(e)

    if classification:
        try:
            MicrosoftDefenderATPManager.validate_classifications(classification)
        except MicrosoftDefenderATPValidationError as e:
            validation_errors.append(e)

    if determination:
        try:
            MicrosoftDefenderATPManager.validate_determinations(determination)
        except MicrosoftDefenderATPValidationError as e:
            validation_errors.append(e)

    if validation_errors:
        siemplify.end(
            MicrosoftDefenderATPManager.join_validation_errors(validation_errors),
            "false",
            EXECUTION_STATE_FAILED,
        )

    config = DefenderATPManagerConfig(
        client_id=client_id,
        client_secret=client_secret,
        tenant_id=tenant_id,
        resource=api_root,
        login_api_root=login_api_root,
        verify_ssl=verify_ssl,
        chronicle_soar=siemplify,
        microsoft_graph_url=graph_api_root,
    )

    try:
        microsoft_defender_atp = init_defender_atp_manager(
            config=config,
        )

        alert = microsoft_defender_atp.update_alert(
            alert_id=alert_id,
            status=status,
            assigned_to=assigned_to,
            classification=classification,
            determination=determination,
        )

        output_message = (
            "Successfully updated Microsoft Defender ATP alert with alert id "
            f"{alert_id}"
        )
        result = "true"
        status = EXECUTION_STATE_COMPLETED
        siemplify.result.add_result_json(alert.to_json())

    except MicrosoftDefenderATPError as e:
        output_message = f"Action didn't completed due to error: {e}"
        result = "false"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
