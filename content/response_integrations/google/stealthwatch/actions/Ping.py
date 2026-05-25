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
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.StealthwatchManager import StealthwatchManager
from TIPCommon import extract_configuration_param

INTEGRATION_NAME = "Stealthwatch"


@output_handler
def main():
    siemplify = SiemplifyAction()
    configurations = siemplify.get_configuration("Stealthwatch")
    server_address = configurations["Api Root"]
    username = configurations["Username"]
    password = configurations["Password"]
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
    )

    stealthwatch_manager = StealthwatchManager(
        server_address, username, password, verify_ssl
    )

    connectivity = stealthwatch_manager.test_connectivity()
    if connectivity:
        output_message = "Successfully connected to the Stealthwatch."
    else:
        output_message = "Failed to connect to the Stealthwatch."
    siemplify.end(output_message, connectivity)


if __name__ == "__main__":
    main()


