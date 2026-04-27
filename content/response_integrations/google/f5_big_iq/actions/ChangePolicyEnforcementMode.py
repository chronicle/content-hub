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
from TIPCommon import extract_configuration_param

from ..core.F5BigIQManager import F5BigIQManager

# consts
f5_big_iq_provider = "F5BigIQ"
SCRIPT_NAME = "Change Policy Enforcement Mode"


@output_handler
def main():

    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    # configuration.
    config = siemplify.get_configuration(f5_big_iq_provider)
    host_address = config["Server Address"]
    username = config["Username"]
    password = config["Password"]
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=f5_big_iq_provider,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )
    f5_bigiq_manager = F5BigIQManager(host_address, username, password, verify_ssl)

    # parameters.
    policy_id = siemplify.parameters["Policy ID"]
    enforcement_mode = siemplify.parameters["Enforcement Mode"]

    # get event logs result.
    result_value = f5_bigiq_manager.change_policy_enforcement_mode(
        policy_id, enforcement_mode
    )
    output_message = (
        f"Policy with ID:{policy_id} enforcement mode changed to: {enforcement_mode}"
    )

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
