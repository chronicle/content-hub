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
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.CylanceManager import CylanceManager
from soar_sdk.SiemplifyUtils import dict_to_flat, convert_dict_to_json_result_dict

SCRIPT_NAME = "Cylance - GetThreatDevices"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("Cylance")

    server_address = conf["Server Address"]
    application_secret = conf["Application Secret"]
    application_id = conf["Application ID"]
    tenant_identifier = conf["Tenant Identifier"]

    cm = CylanceManager(
        server_address, application_id, application_secret, tenant_identifier
    )

    affected_entities = []
    json_results = {}

    for entity in siemplify.target_entities:
        try:
            if entity.entity_type == EntityTypes.FILEHASH:
                threats = cm.get_threat_devices(entity.identifier)
                json_results[entity.identifier] = threats

                if threats:
                    threats = list(map(dict_to_flat, threats))
                    csv_output = cm.construct_csv(threats)

                    siemplify.result.add_entity_table(
                        f"Cylance Threats - {entity.identifier}", csv_output
                    )
                    affected_entities.append(entity)

        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER._log.exception(e)

    if affected_entities:
        entities_names = [entity.identifier for entity in affected_entities]

        output_message = "Threats were found for the following entites:\n" + "\n".join(
            entities_names
        )
    else:
        output_message = "No threats were found."

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
