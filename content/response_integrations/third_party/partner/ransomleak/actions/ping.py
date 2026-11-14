# Copyright 2026 RansomLeak
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
from ..core.utils import build_manager


@output_handler
def main() -> None:
    """Verify the API Root and API Key with an authenticated request."""
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = build_manager(siemplify)
        manager.test_connectivity()
        output_message = (
            f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} server with the provided connection parameters!"
        )
        result_value = True
        status = EXECUTION_STATE_COMPLETED
    except Exception as error:
        siemplify.LOGGER.error(f"Ping failed: {error}")
        siemplify.LOGGER.exception(error)
        output_message = f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} server! Error is {error}"
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
