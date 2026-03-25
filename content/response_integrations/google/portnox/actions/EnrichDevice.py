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
from soar_sdk.SiemplifyUtils import dict_to_flat, add_prefix_to_dict_keys
from ..core.PortnoxManager import PortnoxManager


SCRIPT_NAME = "Portnox - EnrichDevice"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("Portnox")
    api_root = conf["Api Root"]
    username = conf["Username"]
    password = conf["Password"]
    use_ssl = str(conf.get("Verify SSL", "False")).lower() == "true"
    portnox_manager = PortnoxManager(api_root, username, password, use_ssl)

    enriched_entities = []

    for entity in siemplify.target_entities:
        try:
            device = None

            if entity.entity_type == EntityTypes.ADDRESS:
                device = portnox_manager.search_device("ip", entity.identifier)

            elif entity.entity_type == EntityTypes.MACADDRESS:
                device = portnox_manager.search_device("macAddress", entity.identifier)

            if device:
                flat_device = dict_to_flat(device)
                flat_device = add_prefix_to_dict_keys(flat_device, "Portnox")
                entity.additional_properties.update(flat_device)
                entity.is_enriched = True
                enriched_entities.append(entity)

        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]

        output_message = "The following entities were enriched:\n" + "\n".join(
            entities_names
        )

        siemplify.update_entities(enriched_entities)

    else:
        output_message = "No entities were enriched."

    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
