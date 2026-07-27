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
from ..core.NSMManager import NsmManager

# Consts
# Provider Sign.
NSM_PROVIDER = "McAfeeNSM"
ADDRESS = EntityTypes.ADDRESS


@output_handler
def main():
    # Define Variables.
    blocked_entitites = []
    unblocked_entities = []
    result_value = False
    # configurations.
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration(NSM_PROVIDER)
    nsm_manager = NsmManager(
        conf["API Root"],
        conf["Username"],
        conf["Password"],
        conf["Domain ID"],
        conf["Siemplify Policy Name"],
        conf["Sensors Names List Comma Separated"],
    )

    # Fetch scope entities.
    scope_entities = [
        entity for entity in siemplify.target_entities if entity.entity_type == ADDRESS
    ]

    # Run on entities.
    for entity in scope_entities:
        # Check if address blocked.
        block_status = nsm_manager.is_ip_blocked(entity.identifier)
        if block_status:
            blocked_entitites.append(entity)
            result_value = True
        else:
            unblocked_entities.append(entity)

    # Logout from NSM.
    nsm_manager.logout()

    # Form output message.
    if scope_entities:
        output_message = (
            f"Blocked Entities: {','.join(map(str, blocked_entitites))} \n Unblocked"
            f" Entities: {','.join(map(str, unblocked_entities))}"
        )
    else:
        output_message = "No entities with type address at the case."

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
