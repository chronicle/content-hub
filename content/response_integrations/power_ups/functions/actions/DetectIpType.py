# Copyright 2025 Google LLC
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

import re

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

IPV4 = r"^(\d|[1-9]\d|1\d\d|2([0-4]\d|5[0-5]))\.(\d|[1-9]\d|1\d\d|2([0-4]\d|5[0-5]))\.(\d|[1-9]\d|1\d\d|2([0-4]\d|5[0-5]))\.(\d|[1-9]\d|1\d\d|2([0-4]\d|5[0-5]))$"
IPV6 = r"(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))"


@output_handler
def main():
    siemplify = SiemplifyAction()

    status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
    output_message = "IP types found"  # human readable message, showed in UI as the action result
    result_value = "true"  # Set a simple result value, used for playbook if\else and placeholders.

    res = []
    to_enrich = []

    addresses = siemplify.parameters.get("IP Addresses")
    if addresses:
        addresses = addresses.split(",")
    try:
        for address in addresses:
            match = re.match(IPV4, address)
            if match:
                res.append({"Address": address, "IPType": "IPV4"})
            else:
                match = re.match(IPV6, address)
                if match:
                    res.append({"Address": address, "IPType": "IPV6"})
                else:
                    res.append({"Address": address, "IPType": "UNDETECTED"})

        for entity in siemplify.target_entities:
            if entity.entity_type == "ADDRESS":
                match = re.match(IPV4, entity.identifier)
                if match:
                    d = {"IPType": "IPV4"}
                else:
                    match = re.match(IPV6, entity.identifier)
                    d = {"IPType": "IPV6"} if match else {"IPType": "UNDETECTED"}
                entity.additional_properties.update(d)
                to_enrich.append(entity)
                d["Address"] = entity.identifier
                res.append(d)

        if to_enrich:
            siemplify.update_entities(to_enrich)
        siemplify.result.add_result_json(res)
        siemplify.result.add_json("IP Types", res)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = f"Error: {e}"
        result_value = False

    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
