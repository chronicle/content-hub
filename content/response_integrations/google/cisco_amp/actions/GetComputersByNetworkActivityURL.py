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
from soar_sdk.SiemplifyUtils import construct_csv, convert_dict_to_json_result_dict
from ..core.CiscoAMPManager import CiscoAMPManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    configurations = siemplify.get_configuration("CiscoAMP")
    server_addr = configurations["Api Root"]
    client_id = configurations["Client ID"]
    api_key = configurations["Api Key"]
    use_ssl = configurations["Use SSL"].lower() == "true"

    cisco_amp_manager = CiscoAMPManager(server_addr, client_id, api_key, use_ssl)

    enriched_entities = []
    json_results = {}
    errors = ""

    for entity in siemplify.target_entities:
        try:
            if (
                entity.entity_type == EntityTypes.HOSTNAME
                or entity.entity_type == EntityTypes.URL
            ):
                computers = cisco_amp_manager.get_computer_activity(entity.identifier)

                if computers:
                    flat_computers = []
                    computers_dict = {}

                    for index, computer in enumerate(computers):
                        computers_dict[index] = computer
                        # Remove links (not relevant)
                        del computer["links"]

                        computer_info = cisco_amp_manager.create_computer_info(computer)

                        flat_computers.append(computer_info)

                    # Attach file lists in csv
                    csv_output = construct_csv(flat_computers)
                    siemplify.result.add_data_table("Computers", csv_output)

                    json_results[entity.identifier] = computers_dict
                    enriched_entities.append(entity)

        except Exception as e:
            errors += f"Unable to get computer for {entity.identifier}: \n{e}\n"
            continue

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]
        output_message = (
            "Cisco AMP - Got computers by the following entities\n"
            + "\n".join(entities_names)
        )
        output_message += errors

        siemplify.update_entities(enriched_entities)

    else:
        output_message = "Cisco AMP - No computers were found.\n"
        output_message += errors

    # add json
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
