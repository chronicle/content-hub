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


@output_handler
def main():
    siemplify = SiemplifyAction()
    configurations = siemplify.get_configuration("CBProtection")
    server_addr = configurations["Api Root"]
    api_key = configurations["Api Key"]

    cb_protection = CBProtectionManager(server_addr, api_key)

    policy_name = siemplify.parameters.get("Policy Name")

    enriched_entities = []
    errors = ""

    for entity in siemplify.target_entities:
        try:
            computer = None

            if entity.entity_type == EntityTypes.ADDRESS:
                computer = cb_protection.get_computer_by_ip(entity.identifier)

            elif entity.entity_type == EntityTypes.HOSTNAME:
                computer = cb_protection.get_computer_by_hostname(entity.identifier)

            if computer:
                cb_protection.change_computer_policy(computer.id, policy_name)
                enriched_entities.append(entity)

        except Exception as e:
            errors += f"Unable to change policy of {entity.identifier}: \n{e}\n"
            continue

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]
        output_message = (
            f"Carbon Black Protection - The following computer were moved to policy {policy_name}:\n"
            + "\n".join(entities_names)
        )
        output_message += errors

        siemplify.update_entities(enriched_entities)

    else:
        output_message = f"Carbon Black Protection - No computers were moved to policy {policy_name}.\n"
        output_message += errors

    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
