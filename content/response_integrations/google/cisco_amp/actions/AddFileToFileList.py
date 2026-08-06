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

    description = siemplify.parameters["Description"]
    file_list_name = siemplify.parameters["File List Name"]
    file_list = cisco_amp_manager.get_file_list_by_name(file_list_name)

    enriched_entities = []
    errors = ""

    for entity in siemplify.target_entities:
        try:
            if entity.entity_type == EntityTypes.FILEHASH:
                # Only SHA256
                if len(entity.identifier) == 64:
                    cisco_amp_manager.add_file_to_list(
                        file_list["guid"], entity.identifier, description
                    )
                    enriched_entities.append(entity)
        except Exception as e:
            errors += f"Unable to add hash {entity.identifier} to file list {file_list_name}: \n{e}\n"
            continue

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]
        output_message = (
            f"Cisco AMP - Added the following hashes to {file_list_name}:\n"
            + "\n".join(entities_names)
        )
        output_message += errors

        siemplify.update_entities(enriched_entities)

    else:
        output_message = f"Cisco AMP - No files were added to {file_list_name}.\n"
        output_message += errors

    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
