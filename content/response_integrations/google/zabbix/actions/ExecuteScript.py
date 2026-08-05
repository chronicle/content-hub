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
import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import create_entity_json_result_object, output_handler

from ..core.constants import EXECUTION_FAILED, EXECUTION_SUCCEEDED
from ..core.ZabbixManager import ZabbixManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "Zabbix - ExecuteScript"

    configurations = siemplify.get_configuration("Zabbix")
    server_addr = configurations["Api Root"]
    username = configurations["Username"]
    password = configurations["Password"]
    verify_ssl = configurations.get("Verify SSL", "False").lower() == "true"

    zabbix = ZabbixManager(server_addr, username, password, verify_ssl)

    script_name = siemplify.parameters["Script Name"]
    script = zabbix.get_script_by_name(script_name)

    output_message = ""
    success_entities = []
    failed_entities = []
    missing_entities = []
    json_results = []

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.ADDRESS:
            try:
                hosts = zabbix.get_hosts_by_ip(entity.identifier)

                siemplify.LOGGER.info(
                    f"Found {len(hosts)} hosts with IP {entity.identifier}."
                )

                if hosts:
                    for host in hosts:
                        host_id = host.get("hostid")

                        siemplify.LOGGER.info(
                            f"Executing script {script_name} on host {host_id}."
                        )

                        result = zabbix.execute_script(host_id, script.get("scriptid"))

                        json_results.append(
                            create_entity_json_result_object(entity.identifier, result)
                        )

                        if result.get("response") == EXECUTION_FAILED:
                            siemplify.LOGGER.error(
                                f"Failed to run script {script_name} "
                                f"on host {host_id}. "
                                f"Script output: {result.get('value')}"
                            )
                            failed_entities.append(entity.identifier)

                        elif result.get("response") == EXECUTION_SUCCEEDED:
                            siemplify.LOGGER.info(
                                f"Script {script_name} "
                                f"completed on host {host_id}. "
                                f"Script output: {result.get('value')}"
                            )
                            success_entities.append(entity.identifier)

                        else:
                            siemplify.LOGGER.error(
                                f"Script {script_name} execution on "
                                f"host {host_id} ended with unknown status. "
                                f"Script output: {result.get('value')}"
                            )
                            failed_entities.append(entity.identifier)

                else:
                    siemplify.LOGGER.info(
                        f"Couldn't find host with IP {entity.identifier}."
                    )
                    missing_entities.append(entity.identifier)

            except Exception as e:
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}." f"\n{str(e)}."
                )
                siemplify.LOGGER.exception(e)
                failed_entities.append(entity)

    if success_entities:
        entities = "\n".join(success_entities)
        output_message = (
            f"Script {script_name} execution succeeded on the "
            f"following entities:\n{entities}\n"
        )

    if failed_entities:
        entities = "\n".join(failed_entities)
        output_message += (
            f"The script {script_name} failed for the "
            f"following entities:\n{entities}\n"
        )

    if missing_entities:
        entities = "\n".join(missing_entities)
        output_message += f"No hosts were found for the following entitied:\n{entities}"

    if success_entities:
        result_value = "true"
    else:
        result_value = "false"

    # add json
    siemplify.result.add_result_json(json.dumps(json_results))
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
