from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon import extract_action_param, extract_configuration_param

from ..core.BanduraCyberManager import BanduraCyberManager

# CONTS
INTEGRATION_NAME = "BanduraCyber"
SCRIPT_NAME = "Add IP to Allowed Lists"
ADDRESS = EntityTypes.ADDRESS


@output_handler
def main():
    json_results = {}
    entities_with_results = []
    result_value = False

    # Configuration.
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        input_type=str,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        input_type=str,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    list_name = extract_action_param(
        siemplify,
        param_name="List Name",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )
    description = extract_action_param(
        siemplify,
        param_name="Description",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    maskbit = extract_action_param(
        siemplify,
        param_name="Maskbit",
        is_mandatory=False,
        input_type=int,
        print_value=True,
        default_value=32,
    )
    expiration_date = extract_action_param(
        siemplify,
        param_name="Expiration Date",
        is_mandatory=False,
        input_type=str,
        print_value=True,
        default_value="",
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    bandura_cyber_manager = BanduraCyberManager(
        username,
        password,
        verify_ssl=verify_ssl,
    )

    # Get scope entities.
    scope_entities = [
        entity for entity in siemplify.target_entities if entity.entity_type == ADDRESS
    ]

    for entity in scope_entities:
        siemplify.LOGGER.info(f"Processing entity {entity.identifier}")
        siemplify.LOGGER.info(f"Adding {entity.identifier} to {list_name} Allowed List")
        results = bandura_cyber_manager.add_allowed_ip_entity(
            list_name,
            entity.identifier,
            maskbit,
            description,
            expiration_date,
        )

        if results:
            json_results[entity.identifier] = results[0]
            entities_with_results.append(entity.identifier)
            result_value = True

    if result_value:
        output_message = f"Added the following Entities to {list_name}: {', '.join(entities_with_results)}"
    else:
        output_message = "No entities were added"

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
