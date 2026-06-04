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
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CarbonBlackProtectionManager import CBProtectionManager
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict


@output_handler
def main():
    siemplify = SiemplifyAction()
    configurations = siemplify.get_configuration("CBProtection")
    server_addr = configurations["Api Root"]
    api_key = configurations["Api Key"]

    cb_protection = CBProtectionManager(server_addr, api_key)

    enriched_entities = []
    computer_infos = []
    json_result = {}
    errors = ""

    for entity in siemplify.target_entities:
        try:
            if entity.entity_type == EntityTypes.FILEHASH:
                # CR: Move to manager
                if len(entity.identifier) == 32:
                    computers = cb_protection.get_computers_running_hash(
                        entity.identifier
                    )

                    if computers:
                        # CR: Move to manager
                        for computer in computers:
                            computer_info = {
                                "Id": computer.get("id"),
                                "Hostname": computer.get("name"),
                                "Mac Address": computer.get("macAddress"),
                                "Ip Address": computer.get("ipAddress"),
                                "Policy Name": computer.get("policyName"),
                                "Connected": computer.get("connected"),
                                "Operating System": computer.get("osName"),
                                "Last Updated": computer.get("last_update"),
                                "Agent Version": computer.get("agentVersion	"),
                            }
                            computer_infos.append(computer_info)

                        json_result[entity.identifier] = [
                            computer.original_document for computer in computers
                        ]

                        # Attach as csv
                        csv_output = cb_protection.construct_csv(computer_infos)
                        siemplify.result.add_entity_table(entity.identifier, csv_output)
                        enriched_entities.append(entity)

        except Exception as e:
            errors += f"Unable to get computer that are running file {entity.identifier}: \n{e}\n"
            continue

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]
        output_message = (
            "Carbon Black Protection - Found computers for the following files:\n"
            + "\n".join(entities_names)
        )
        output_message += errors

    else:
        output_message = "Carbon Black Protection - No computers were found.\n"
        output_message += errors

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
