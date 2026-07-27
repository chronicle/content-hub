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
from soar_sdk.SiemplifyUtils import dict_to_flat, convert_dict_to_json_result_dict
from ..core.CarbonBlackProtectionManager import CBProtectionManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    configurations = siemplify.get_configuration("CBProtection")
    server_addr = configurations["Api Root"]
    api_key = configurations["Api Key"]

    cb_protection = CBProtectionManager(server_addr, api_key)

    enriched_entities = []
    json_results = {}
    errors = ""

    for entity in siemplify.target_entities:
        try:
            if entity.entity_type == EntityTypes.FILEHASH:
                # CR: Move to manager
                if len(entity.identifier) == 32:
                    file_instances = cb_protection.get_file_instances(entity.identifier)

                    if file_instances:
                        flat_instances = []

                        for file_instance in file_instances:
                            file_instance = file_instance.original_document
                            flat_instances.append(dict_to_flat(file_instance))

                        json_results[entity.identifier] = flat_instances

                        # Attach as csv
                        csv_output = cb_protection.construct_csv(flat_instances)
                        siemplify.result.add_entity_table(entity.identifier, csv_output)

                        enriched_entities.append(entity)

        except Exception as e:
            errors += f"Unable to find file {entity.identifier}: \n{e}\n"
            continue

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]
        output_message = (
            "Carbon Black Protection - Found the following files:\n"
            + "\n".join(entities_names)
        )
        output_message += errors

    else:
        output_message = "Carbon Black Protection - No files were found.\n"
        output_message += errors

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
