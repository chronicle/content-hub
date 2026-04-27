from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CiscoISEManager import CiscoISEManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyDataModel import EntityTypes


INTEGRATION_NAME = "CiscoISE"
PRODUCT_NAME = "Cisco ISE"
SCRIPT_NAME = "Cisco ISE - Add Endpoint To Endpoint Identity Group"

# Fix misalignment of MAC entity type
EntityTypes.MACADDRESS = EntityTypes.MACADDRESS.upper()
SUPPORTED_ENTITY_TYPES = [EntityTypes.MACADDRESS, EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        print_value=True,
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=True,
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
        is_mandatory=True,
    )

    # Action parameters
    endpoint_group_name = extract_action_param(
        siemplify,
        param_name="Endpoint Identity Group Name",
        print_value=True,
        is_mandatory=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED
    successful_entities, failed_entities, json_results = [], [], {}
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        manager = CiscoISEManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_requests=verify_ssl,
            logger=siemplify.LOGGER,
        )

        groups = manager.get_endpoint_groups("name", "EQ", endpoint_group_name, 100)

        if groups:
            group_id = groups[0].id
            for entity in suitable_entities:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                try:
                    mac_address = (
                        manager.get_endpoint_mac_by_ip(entity.identifier)
                        if entity.entity_type == EntityTypes.ADDRESS
                        else entity.identifier
                    )
                    endpoint_id = next(
                        (
                            endpoint.get("id")
                            for endpoint in manager.get_endpoints()
                            if endpoint.get("name", "") == mac_address
                        ),
                        None,
                    )
                    if endpoint_id:
                        json_response = manager.add_endpoint_to_group(
                            endpoint_id, group_id
                        )
                        successful_entities.append(entity)
                        json_results[entity.identifier] = json_response
                    else:
                        failed_entities.append(entity)
                except Exception as e:
                    failed_entities.append(entity.identifier)
                    siemplify.LOGGER.error(
                        f"An error occurred on entity {entity.identifier}"
                    )
                    siemplify.LOGGER.exception(e)

                siemplify.LOGGER.info(
                    f"Finished processing entity: {entity.identifier}"
                )
        else:
            raise Exception(
                "Endpoint Identity Group '{}' wasn't found in Cisco ISE. "
                "Please check the spelling.".format(endpoint_group_name)
            )

        if successful_entities:
            output_message = (
                'Successfully added the following endpoints to the "{}" Endpoint '
                "Identity Group in {}: {}\n\n".format(
                    endpoint_group_name,
                    PRODUCT_NAME,
                    ", ".join([entity.identifier for entity in successful_entities]),
                )
            )
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

            if failed_entities:
                output_message += f'Action wasn\'t able to find the following endpoints in {PRODUCT_NAME}: {", ".join(failed_entities)}\n'
        else:
            output_message = "None of the provided endpoints were found."
            result = False

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f'Error executing action "{SCRIPT_NAME}". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
