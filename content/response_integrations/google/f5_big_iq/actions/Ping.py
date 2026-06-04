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
from ..core.F5BigIQManager import F5BigIQManager
from TIPCommon import extract_configuration_param

# consts
F5_BIG_IQ_PROVIDER = "F5BigIQ"
SCRIPT_NAME = "Ping"


@output_handler
def main():

    # define variables.
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    # configuration.
    config = siemplify.get_configuration(F5_BIG_IQ_PROVIDER)
    host_address = config["Server Address"]
    username = config["Username"]
    password = config["Password"]
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=F5_BIG_IQ_PROVIDER,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    f5_bigiq_manager = F5BigIQManager(host_address, username, password, verify_ssl)

    if f5_bigiq_manager:
        output_message = "Connection Established"
        result_value = True
    else:
        output_message = "Connection Failed"
        result_value = False

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
