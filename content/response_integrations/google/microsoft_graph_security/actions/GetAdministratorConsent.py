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

from TIPCommon.extraction import extract_configuration_param

from microsoft_graph_security.core.constants import (
    ADMIN_CONSENT_PATH,
    DEFAULT_LOGIN_API_ROOT,
    GET_ADMINISTRATOR_CONSENT_SCRIPT_NAME,
    INTEGRATION_NAME,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_ADMINISTRATOR_CONSENT_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        input_type=str,
    )
    tenant = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Tenant",
        is_mandatory=True,
        input_type=str,
    )
    redirect_uri = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Redirect URL",
        default_value=False,
        input_type=str,
    )
    login_api_root = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Login API Root",
        default_value=DEFAULT_LOGIN_API_ROOT,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        siemplify.LOGGER.info("Generating authorization link.")
        normalized_login_root = (login_api_root or DEFAULT_LOGIN_API_ROOT).rstrip("/")
        consent_path = ADMIN_CONSENT_PATH.format(
            tenant=tenant,
            client_id=client_id,
            redirect_uri=redirect_uri,
        )
        url = f"{normalized_login_root}/{consent_path}"

        if url:
            siemplify.result.add_link("Browse to this authorization link", url)
            siemplify.LOGGER.info(f"Successfully generated link: {url}")
            status = EXECUTION_STATE_COMPLETED
        else:
            siemplify.LOGGER.error("Failed to create an authorization url")
            status = EXECUTION_STATE_FAILED

        output_message = (
            "Your browser should be redirected with a response in the address bar. If the administrator"
            " approves the permissions for your application, admin_consent set to True."
            if url
            else "Failed to create an authorization url"
        )

        result_value = "true" if url else "false"

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
