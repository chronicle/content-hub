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
from ..core.ShodanManager import ShodanManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes


@output_handler
def main():
    siemplify = SiemplifyAction()

    conf = siemplify.get_configuration("Shodan")
    verify_ssl = conf.get("Verify SSL", "False").lower() == "true"
    api_key = conf.get("API key", "")
    shodan = ShodanManager(api_key, verify_ssl=verify_ssl)

    ips_list = []
    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.ADDRESS:
            ips_list.append(entity.identifier)
    # Convert ips list to strings
    ips = ",".join(ips_list)

    scan_info = shodan.scan(ips)
    if scan_info:
        scan_id = scan_info.get("id")
        output_message = (
            f"Successfully scan a network using Shodan. Scan ID is {scan_id}"
        )
        result_value = scan_id
    else:
        output_message = "Failed to scan a network using Shodan"
        result_value = "{}"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
