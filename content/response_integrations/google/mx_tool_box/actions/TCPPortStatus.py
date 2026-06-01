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
from soar_sdk.SiemplifyUtils import get_domain_from_entity, construct_csv
from ..core.MXToolBoxManager import MXToolBoxManager


MXTOOLBOX_PROVIDER = "MXToolBox"
SCRIPT_NAME = "MXToolBox_port_status"
TABLE_HEADER = "TCP Port Status Results"


@output_handler
def main():
    # Configurations.
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration(MXTOOLBOX_PROVIDER)
    verify_ssl = conf["Verify SSL"].lower() == "true"
    mx_tool_box_manager = MXToolBoxManager(
        conf["API Root"], conf["API Key"], verify_ssl
    )
    # Parameters.
    port_number = siemplify.parameters["Port Number"]

    # Variables.
    errors = []
    port_statuses = []
    success_entities = []
    unsuccessful_entities = []
    results_list = []

    target_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.HOSTNAME
        or entity.entity_type == EntityTypes.ADDRESS
        or entity.entity_type == EntityTypes.USER
        or entity.entity_type == EntityTypes.URL
    ]

    for entity in target_entities:
        try:
            if not entity.entity_type == EntityTypes.ADDRESS:
                port_status = mx_tool_box_manager.get_port_status(
                    get_domain_from_entity(entity), port_number
                )
            else:
                port_status = mx_tool_box_manager.get_port_status(
                    entity.identifier, port_number
                )
            results_list.append(
                {
                    "Domain/IP": entity.identifier,
                    "Port": port_number,
                    "Port Status": str(port_status),
                }
            )
            entity.additional_properties.update({f"MX_port_{port_number}": port_status})
            port_statuses.append(port_status)
            if port_status:
                success_entities.append(entity)
            else:
                unsuccessful_entities.append(entity)

        except Exception as e:
            # An error occurred - skip entity and continue
            error_message = (
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(e)
            errors.append(error_message)

    if results_list:
        siemplify.result.add_data_table(TABLE_HEADER, construct_csv(results_list))
    if success_entities:
        output_message = f"Port {port_number} was checked in the following entities: {', '.join([entity.identifier for entity in target_entities])}"
    else:
        output_message = "Not found data for target entities."

    if errors:
        output_message = "{0}  \n \n {1}".format(output_message, " \n ".join(errors))

    siemplify.update_entities(target_entities)
    siemplify.end(output_message, ",".join(map(str, port_statuses)))


if __name__ == "__main__":
    main()
