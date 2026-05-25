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
from ..core.XForceManager import XForceManager
from soar_sdk.SiemplifyUtils import construct_csv
import json


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("XForce")
    address = conf["Address"]
    api_key = conf["Api Key"]
    api_password = conf["Api Password"]
    verify_ssl = conf["Verify SSL"].lower() == "true"
    xf_manager = XForceManager(api_key, api_password, address, verify_ssl=verify_ssl)

    # Category options:
    # Spam, Anonymisation Services, Scanning IPs, Dynamic IPs, Malware, Bots, Botnet Command and Control Server
    category = siemplify.parameters["Category"]
    json_results = {}

    ips = xf_manager.get_ip_by_category(category)
    if ips:
        json_results = json.dumps(ips)
        ips_csv = construct_csv(ips)
        siemplify.result.add_data_table(f"IPS in {category}", ips_csv)

        output_message = f"{category} retrieved {len(ips)} IPs"
        result_value = "true"
    else:
        output_message = f"Failed to retrieved the IPs that are in {category}."
        result_value = "false"

    siemplify.result.add_result_json(json_results)

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
