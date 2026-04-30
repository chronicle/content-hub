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

import socket
import struct

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


def ip2long(ip):
    """Convert an IP string to long"""
    packed_ip = socket.inet_aton(ip)
    return struct.unpack("!L", packed_ip)[0]


@output_handler
def main():
    siemplify = SiemplifyAction()

    status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
    output_message = "output message :"  # human readable message, showed in UI as the action result
    result_value = None  # Set a simple result value, used for playbook if\else and placeholders.

    ip_addresses = list(
        filter(
            None,
            [x.strip() for x in siemplify.parameters.get("IP Addresses").split(",")],
        ),
    )
    json_result = {}
    res = []
    for ip_addr in ip_addresses:
        iplong = ip2long(ip_addr)
        json_result[ip_addr] = iplong
        res.append(iplong)

    siemplify.result.add_result_json(json_result)

    result_value = ",".join(map(str, res))
    output_message = f"Converted from: {ip_addresses} to {result_value}"

    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
