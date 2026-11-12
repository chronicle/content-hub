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

from ..core.WildfireManager import WildfireManager

INTEGRATION_NAME = "Wildfire"
ACTION_NAME = "Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {ACTION_NAME}"

    try:
        wildfire_manager = WildfireManager.from_siemplify(siemplify)
        connectivity = wildfire_manager.test_connectivity()
        siemplify.end("Successfully connected to the Wildfire service.", connectivity, EXECUTION_STATE_COMPLETED)

    except Exception as e:
        siemplify.LOGGER.exception("Failed to connect to Wildfire")
        siemplify.end(f"Failed to connect to the Wildfire service. Reason: {e}", False, EXECUTION_STATE_FAILED)


if __name__ == "__main__":
    main()
