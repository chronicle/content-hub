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
ACTION_SCRIPT_NAME = "Unblock IP"
NSM_PROVIDER = "McAfeeNSM"
ADDRESS = EntityTypes.ADDRESS


@output_handler
def main():
    # Define variables.
    unblocked_entities = []
    result_value = False
    # Configuration.
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_SCRIPT_NAME
    conf = siemplify.get_configuration(NSM_PROVIDER)
    nsm_manager = NsmManager(
        conf["API Root"],
        conf["Username"],
        conf["Password"],
        conf["Domain ID"],
        conf["Siemplify Policy Name"],
        conf["Sensors Names List Comma Separated"],
    )
    # Fetch Scope entities.
    scope_entities = [
        entity for entity in siemplify.target_entities if entity.entity_type == ADDRESS
    ]

    # Scan entities.
    for entity in scope_entities:
        try:
            release_status = nsm_manager.release_ip(entity.identifier)
            if release_status:
                unblocked_entities.append(entity)
                result_value = True
        except Exception as err:
            siemplify.LOGGER.error(
                f"Error unblocking IP {entity.identifier}, ERROR: {err}"
            )
            siemplify.LOGGER._log.exception(err)

    # Deploy changes.
    nsm_manager.deploy_changes()

    # Logout from NSM.
    nsm_manager.logout()

    # Form output message
    if unblocked_entities:
        output_message = (
            "Successfully unblocked"
            f" {','.join([entity.identifier for entity in unblocked_entities])}"
        )
    else:
        output_message = "No entities were Unblocked."

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
