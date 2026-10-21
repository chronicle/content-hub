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

from TIPCommon.extraction import extract_action_param, extract_configuration_param

from microsoft_graph_security.core.constants import (
    DEFAULT_API_ROOT,
    DEFAULT_LOGIN_API_ROOT,
    INTEGRATION_NAME,
    KILL_USER_SESSION,
)
from microsoft_graph_security.core.MicrosoftGraphSecurityManager import MicrosoftGraphSecurityManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = KILL_USER_SESSION
    siemplify.LOGGER.info("================= Main - Param Init =================")

    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        input_type=str,
    )
    secret_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret ID",
        is_mandatory=False,
        input_type=str,
    )
    certificate_path = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Certificate Path",
        is_mandatory=False,
        input_type=str,
    )
    certificate_password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Certificate Password",
        is_mandatory=False,
        input_type=str,
    )
    tenant = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Tenant",
        is_mandatory=True,
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    api_root = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        default_value=DEFAULT_API_ROOT,
        print_value=True,
    )
    login_api_root = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Login API Root",
        default_value=DEFAULT_LOGIN_API_ROOT,
        print_value=True,
    )

    user_id = extract_action_param(
        siemplify,
        param_name="userPrincipalName or ID",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        siemplify.LOGGER.info("Connecting to Microsoft Graph Security.")
        microsoft_graph_manager = MicrosoftGraphSecurityManager(
            client_id=client_id,
            client_secret=secret_id,
            certificate_path=certificate_path,
            certificate_password=certificate_password,
            tenant=tenant,
            verify_ssl=verify_ssl,
            api_root=api_root,
            login_api_root=login_api_root,
            siemplify=siemplify,
        )
        siemplify.LOGGER.info("Connected successfully.")

        siemplify.LOGGER.info(f"Killing user {user_id} session")
        microsoft_graph_manager.kill_user_session(user_id)

        siemplify.LOGGER.info(
            "User tokens invalidated. Kill User session was successful."
        )
        output_message = "User tokens invalidated. Kill User session was successful."
        status = EXECUTION_STATE_COMPLETED
        result_value = "true"

    except Exception as e:
        siemplify.LOGGER.error(f"Some errors occurred. Error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Some errors occurred. Error: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
