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
from ..core.CuckooManager import CuckooManager
from TIPCommon import extract_configuration_param

INTEGRATION_NAME = "Cuckoo"


@output_handler
def main():
    siemplify = SiemplifyAction()

    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
    )
    web_interface_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Web Interface Address",
        is_mandatory=True,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File",
        is_mandatory=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=False,
    )

    cuckoo_manager = CuckooManager(
        server_address, web_interface_address, ca_certificate, verify_ssl, api_token
    )

    try:
        cuckoo_manager.test_connectivity()
        output_message = "Successfully connected to the Cuckoo server."
        siemplify.end(output_message, True)
    except Exception as e:
        output_message = f"Failed to connect to the Cuckoo server. Error: {e}"
        siemplify.end(output_message, False)


if __name__ == "__main__":
    main()


