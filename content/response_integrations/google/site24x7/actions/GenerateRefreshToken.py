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
from TIPCommon import extract_action_param, extract_configuration_param

from ..core.constants import GENERATE_REFRESH_TOKEN_SCRIPT_NAME, INTEGRATION_NAME
from ..core.Site24x7Manager import Site24x7Manager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GENERATE_REFRESH_TOKEN_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    client_id = extract_configuration_param(
        siemplify=siemplify,
        param_name="Client ID",
        is_mandatory=True,
        provider_name=INTEGRATION_NAME,
        print_value=True,
    )

    client_secret = extract_configuration_param(
        siemplify=siemplify,
        param_name="Client Secret",
        is_mandatory=True,
        provider_name=INTEGRATION_NAME,
        print_value=False,
    )

    auth_code = extract_action_param(
        siemplify=siemplify,
        param_name="Authorization Code",
        is_mandatory=True,
        print_value=False,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED

    try:
        refresh_token = Site24x7Manager.generate_refresh_token(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            code=auth_code,
        )
        output_message = (
            "Successfully generated the refresh token. Copy that refresh token and put it in the "
            "Integration configuration."
        )
        siemplify.result.add_result_json({"refresh_token": f"{refresh_token}"})

    except Exception as e:
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f'Error executing action "Generate Refresh Token". Reason: {e}'
        siemplify.LOGGER.exception(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Status: {status}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
