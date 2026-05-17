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
from ..core.CynetManager import CynetManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param

INTEGRATION_NAME = "Cynet"


@output_handler
def main():
    siemplify = SiemplifyAction()
    output_message = ""
    result_value = False

    # Configuration.
    conf = siemplify.get_configuration("Cynet")
    api_root = conf["Api Root"]
    username = conf["Username"]
    password = conf["Password"]
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )
    cynet_manager = CynetManager(api_root, username, password, verify_ssl)

    if cynet_manager:
        output_message = "Successfully connected to the Cynet."
        result_value = True
    else:
        output_message = "Failed to connect to the Cynet."

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
