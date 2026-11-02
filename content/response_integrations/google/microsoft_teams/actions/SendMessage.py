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
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.MicrosoftConstants import (
    INTEGRATION_NAME,
    SEND_MESSAGE_ACTION,
    DEFAULT_API_ROOT,
    DEFAULT_LOGIN_API_ROOT,
)
from ..core.MicrosoftManager import MicrosoftTeamsManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SEND_MESSAGE_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=True,
    )
    secret_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret ID",
        is_mandatory=True,
        print_value=False,
    )
    tenant = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Tenant",
        is_mandatory=True,
        print_value=True,
    )
    redirect_url = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Redirect URL",
        is_mandatory=False,
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Refresh Token",
        is_mandatory=True,
        print_value=False,
    )
    login_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Login API Root",
        default_value=DEFAULT_LOGIN_API_ROOT,
        print_value=True,
    )
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        default_value=DEFAULT_API_ROOT,
        print_value=True,
    )

    team_name = extract_action_param(
        siemplify, param_name="Team Name", print_value=True, is_mandatory=True
    )
    channel_name = extract_action_param(
        siemplify, param_name="Channel Name", print_value=True, is_mandatory=True
    )
    message = extract_action_param(
        siemplify, param_name="Message", print_value=True, is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""

    try:
        mtm = MicrosoftTeamsManager(
            client_id=client_id,
            client_secret=secret_id,
            tenant=tenant,
            refresh_token=token,
            redirect_url=redirect_url,
            api_root=api_root,
            login_api_root=login_api_root,
            verify_ssl=verify_ssl,
        )
        message_res = mtm.send_message(channel_name, team_name, message) or []

        if message_res:
            output_message = f"Successfully send message to channel {channel_name} in team {team_name}."
            siemplify.result.add_result_json(message_res)
        else:
            output_message = (
                "{message} message NOT delivered to channel {channel_name}."
            )
            result_value = False

    except Exception as e:
        output_message = f"Error executing action {SEND_MESSAGE_ACTION}. Reason: {e}"
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
