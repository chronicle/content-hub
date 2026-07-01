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

from ..core.constants import INTEGRATION_DISPLAY_NAME, PING_SCRIPT_NAME
from ..core.MimecastManager import MimecastManager
from ..core import UtilsManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    integration_parameters = UtilsManager.get_integration_parameters(siemplify)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = MimecastManager(
            api_root=integration_parameters.api_root,
            app_id=integration_parameters.app_id,
            app_key=integration_parameters.app_key,
            access_key=integration_parameters.access_key,
            secret_key=integration_parameters.secret_key,
            client_id=integration_parameters.client_id,
            client_secret=integration_parameters.client_secret,
            verify_ssl=integration_parameters.verify_ssl,
            siemplify=siemplify,
        )

        manager.test_connectivity()
        result = True
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} server with the provided "
            f"connection parameters!"
        )

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {PING_SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} server! Error is {e}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Status: {status}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
