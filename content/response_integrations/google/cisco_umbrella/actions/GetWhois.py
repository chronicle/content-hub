from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon import extract_configuration_param
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from cisco_umbrella.core.CiscoUmbrellaManager import CiscoUmbrellaIvestigate
from TIPCommon import dict_to_flat, add_prefix_to_dict
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

# Consts
HOSTNAME = EntityTypes.HOSTNAME
OUTPUT_MESSAGE_TEMPLATE = "Associated domains found for: {0}"
CISCO_UMBRELLA_PREFIX = "CU"
INTEGRATION_NAME = "CiscoUmbrella"
SCRIPT_NAME = "CiscoUmbrella - Get Whois"


# Action Context
@output_handler
def main():
    # Define Variables.
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    result_value = False
    status = EXECUTION_STATE_COMPLETED
    entities_to_update = []
    json_results = {}
    failed_entities = []
    output_message = ""
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
            if entity.entity_type == HOSTNAME and not entity.is_internal
        ]

        # Execute Action On Scope Entities.
        for entity in scope_entities:
            try:
                response_csv = cisco_umbrella_manager.get_whois_csv(
                    str(entity.identifier).lower()
                )
                response_dict = cisco_umbrella_manager.get_whois_dict(
                    str(entity.identifier).lower()
                )
                if response_csv and len(response_csv) > 1:
                    siemplify.result.add_entity_table(entity.identifier, response_csv)
                    result_value = True
                if response_dict:
                    json_results[entity.identifier] = response_dict
                    # Enrich Entity.
                    entity.additional_properties.update(
                        add_prefix_to_dict(
                            dict_to_flat(response_dict), CISCO_UMBRELLA_PREFIX
                        )
                    )
                    entities_to_update.append(entity)
                    result_value = True
                    # Attach Country To Entity.
                    if "registrantCountry" in list(response_dict.keys()):
                        entity.additional_properties["Country"] = response_dict[
                            "registrantCountry"
                        ]
                    elif "technicalContactCountry" in list(response_dict.keys()):
                        entity.additional_properties["Country"] = response_dict[
                            "technicalContactCountry"
                        ]
                    elif "administrativeContactCountry" in list(response_dict.keys()):
                        entity.additional_properties["Country"] = response_dict[
                            "administrativeContactCountry"
                        ]
                if not response_dict and not response_csv:
                    failed_entities.append(entity)
            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        # Organize Output Message.
        if failed_entities:
            output_message += "\nThe following entities were not found in Cisco Umbrella:\n{}\n".format(
                "\n".join([entity.identifier for entity in failed_entities])
            )
        if entities_to_update:
            output_message += OUTPUT_MESSAGE_TEMPLATE.format(
                ",".join([entity.identifier for entity in entities_to_update])
            )
        if not entities_to_update and not failed_entities:
            output_message = "No data found for entities."

        # add json
        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
        # Update Entities.
        siemplify.update_entities(entities_to_update)
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
