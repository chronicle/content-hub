from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon import extract_configuration_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from cisco_umbrella.core.CiscoUmbrellaManager import CiscoUmbrellaEnforcment
import datetime

HOSTNAME = EntityTypes.HOSTNAME
SCRIPT_NAME = "CiscoUmbrella - Delete Domain"
INTEGRATION_NAME = "CiscoUmbrella"


@output_handler
def main():
    # Define Variables.
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")
    result_value = False
    status = EXECUTION_STATE_COMPLETED
    failed_entities = []
    successful_entities = []
    output_message = ""
    try:
        # Configuration.
        token = extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name="EnforcementApiToken",
            is_mandatory=True,
        )
        cisco_umbrella_manager = CiscoUmbrellaEnforcment(token)

        scope_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type == HOSTNAME and not entity.is_internal
        ]
        siemplify.LOGGER.info("----------------- Main - Started -----------------")
        for entity in scope_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            try:
                date = datetime.datetime.now()
                cisco_umbrella_manager.deleteDomain(entity.identifier)
                result_value = True
                successful_entities.append(entity)
                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")
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

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
