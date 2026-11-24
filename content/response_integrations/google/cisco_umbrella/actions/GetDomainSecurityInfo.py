from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon import extract_configuration_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from cisco_umbrella.core.CiscoUmbrellaManager import CiscoUmbrellaIvestigate
import base64
import json

# Consts
HOSTNAME = EntityTypes.HOSTNAME
OUTPUT_MESSAGE_TEMPLATE = "Security info found for: {0}"
SCRIPT_NAME = "CiscoUmbrella - Get Domain Security Info"
INTEGRATION_NAME = "CiscoUmbrella"


# Action Context
@output_handler
def main():
    # Define Variables.
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    result_value = False
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities = []
    json_results = {}
    failed_entities = []
    try:
        # Configuration.
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
            if entity.entity_type == HOSTNAME and not entity.is_internal
        ]

        # Execute Action On Scope Entities.
        for entity in scope_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            try:
                response = cisco_umbrella_manager.get_domain_security_info(
                    entity.identifier
                )
                json_results[entity.identifier] = response
                successful_entities.append(entity)
                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")
                base64_content = base64.b64encode(
                    json.dumps(response).encode("utf-8")
                ).decode("utf-8")
                siemplify.result.add_entity_attachment(
                    entity.identifier, "SecurityInfo.json", base64_content
                )
                result_value = True
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
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

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
