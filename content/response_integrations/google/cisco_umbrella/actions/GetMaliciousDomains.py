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

# Imports
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CiscoUmbrellaManager import CiscoUmbrellaIvestigate
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param

# Consts
ADDRESS = EntityTypes.ADDRESS
SCRIPT_NAME = "CiscoUmbrella - Get Malicious Domains"
INTEGRATION_NAME = "CiscoUmbrella"


# Action Context
@output_handler
def main():
    # Define Variables.
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    successful_entities = []
    json_results = {}
    failed_entities = []
    output_message = ""
    # Configuration.
    try:
        token = extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name="InvestigateApiToken",
            is_mandatory=True,
        )
        cisco_umbrella_manager = CiscoUmbrellaIvestigate(token)
        # Get Scope Entities.
        scope_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type == ADDRESS and not entity.is_internal
        ]
        # Execute Action On Scope Entities.
        for entity in scope_entities:
            try:
                response = cisco_umbrella_manager.get_malicious_domain_csv(
                    str(entity.identifier).lower()
                )
                response_list = cisco_umbrella_manager.get_malicious_domains(
                    str(entity.identifier).lower()
                )
                json_results[entity.identifier] = response_list
                successful_entities.append(entity)
                siemplify.result.add_entity_table(entity.identifier, response)
            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        # Organize Output Message.
        if successful_entities:
            entities_names = [entity.identifier for entity in successful_entities]
            output_message += "Successfully processed entities: \n{}\n".format(
                "\n".join(entities_names)
            )

            siemplify.update_entities(successful_entities)
            # add json
            siemplify.result.add_result_json(json_results)
        else:
            result_value = False
        if failed_entities:
            output_message += "\nThe following entities were not found in Cisco Umbrella:\n{}\n".format(
                "\n".join([entity.identifier for entity in failed_entities])
            )

        if not failed_entities and not successful_entities:
            output_message = "No entities were enriched."

    except Exception as e:
        output_message = f"Error executing action '{SCRIPT_NAME}'. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    # Finish Action.
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
