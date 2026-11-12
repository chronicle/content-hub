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

"""AtlassianConfluenceServer - Ping."""
from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.ConfluenceManager import ConfluenceManager
from ..core.constants import PING_SCRIPT_NAME
from ..core.exceptions import ConfluenceValidationError
from ..core.utils import get_configuration_params


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("--------------- Main - Param Init ---------------")

    # Integration Configuration
    (api_root, username, password, api_token, verify_ssl) = get_configuration_params(
        siemplify_action_instance=siemplify
    )

    siemplify.LOGGER.info("--------------- Main - Started ---------------")

    output_message = (
        "Successfully connected to the Atlassian Confluence"
        f" Server instance {api_root} with the provided connection parameters!."
    )
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    try:
        confluence_manager = ConfluenceManager(
            api_root,
            username,
            password,
            api_token,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
            ping=True,
        )
        confluence_manager.test_connectivity()

    except ConfluenceValidationError as error:
        output_message = str(error)
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)

    except Exception as error:
        output_message = (
            "Failed to connect to the Atlassian Confluence Server instance! "
            f"Error is {error}"
        )
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
