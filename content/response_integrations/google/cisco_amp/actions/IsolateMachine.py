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
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from ..core.CiscoAMPManager import CiscoAMPManager

SCRIPT_NAME = "CiscoAMP - IsolateMachine"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    configurations = siemplify.get_configuration("CiscoAMP")
    server_address = configurations["Api Root"]
    client_id = configurations["Client ID"]
    api_key = configurations["Api Key"]
    use_ssl = configurations["Use SSL"].lower() == "true"

    manager = CiscoAMPManager(server_address, client_id, api_key, use_ssl)

    enriched_entities = []
    json_results = {}
    errors = ""

    for entity in siemplify.target_entities:
        try:
            computer = None
            if entity.entity_type == EntityTypes.ADDRESS:
                computer = manager.get_computer_info_by_ip(
                    entity.identifier, internal=entity.is_internal
                )

            elif entity.entity_type == EntityTypes.HOSTNAME:
                computer = manager.get_computer_info_by_hostname(entity.identifier)

            if computer:
                info = manager.isolate_machine(computer["connector_guid"])
                json_results[entity.identifier] = info
                enriched_entities.append(entity)
            else:
                siemplify.LOGGER.info(
                    f"Computer was not found for entity {entity.identifier}"
                )

        except Exception as e:
            errors += (
                f"Unable to isolate computer by ip {entity.identifier}: \n{str(e)}\n"
            )
            continue

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]
        output_message = "The following computers isolated successfully:\n{}\n".format(
            "\n".join(entities_names)
        )
        output_message += errors

        siemplify.update_entities(enriched_entities)

    else:
        output_message = "Cisco AMP - No computers were found to isolate.\n"
        output_message += errors

    # add json
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
