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
import base64
from enum import Enum

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.AlienVaultManager import AlienVaultManager


PROVIDER = "AlienVaultAppliance"
TABLE_NAME = "PCAP Records"
PCAP_FILE_NAME = "{0}_{1}.pcap"
ACTION_NAME = "AlienVault_Get PCAP For Events"


class ExecutionScope(Enum):
    ExecutionScopeUnspecified = 0
    Alert = 1
    Case = 2


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    configurations = siemplify.get_configuration(PROVIDER)
    server_address = configurations["Api Root"]
    username = configurations["Username"]
    password = configurations["Password"]

    alienvault_manager = AlienVaultManager(server_address, username, password)

    result_value = False
    errors = []
    json_result = {}

    target_alerts: list = []
    execution_scope = getattr(siemplify, "execution_scope", ExecutionScope.Alert)

    if execution_scope.value == ExecutionScope.Alert.value:
        target_alerts = [siemplify.current_alert]
    else:
        target_alerts = getattr(siemplify.case, "alerts", [])

    for alert in target_alerts:
        for event in alert.security_events:
            try:
                event_id = event.additional_properties.get("Id")
                if event_id:
                    pcap_content = alienvault_manager.get_event_pcap(event_id)
                    if pcap_content:
                        json_result[event_id] = base64.b64encode(pcap_content.encode())
                        siemplify.result.add_attachment(
                            event.name,
                            PCAP_FILE_NAME.format(event.name, event_id),
                            base64.b64encode(pcap_content.encode()),
                        )
                        result_value = True
                else:
                    siemplify.LOGGER.info(f'Event "{event.name}" has no ID field')

            except Exception as err:
                error_message = (
                    f"Error fetching PCAP file for event {event.name}_{event_id}, "
                    f"ERROR: {str(err)}"
                )
                siemplify.LOGGER.error(error_message)
                siemplify.LOGGER.exception(err)
                errors.append(error_message)

    if result_value:
        output_message = "Found PCAP files for events."
    else:
        output_message = "Not found PCAP files for events."

    if errors:
        output_message = "{0} \n \n Errors: \n \n  {1}".format(
            output_message, " \n ".join(errors)
        )

    siemplify.result.add_result_json(json_result)
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
