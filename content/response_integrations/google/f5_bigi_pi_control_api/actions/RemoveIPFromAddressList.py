from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.F5BIGIPiControlAPIManager import F5BIGIPiControlAPIManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    REMOVE_IP_FROM_ADDRESS_LIST_SCRIPT_NAME,
)
from soar_sdk.SiemplifyDataModel import EntityTypes


SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = REMOVE_IP_FROM_ADDRESS_LIST_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
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
        is_mandatory=True,
        print_value=True,
    )

    # Action parameters
    address_list_name = extract_action_param(
        siemplify, param_name="Address List Name", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities = []
    non_existing_entities = []
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        if suitable_entities:
            manager = F5BIGIPiControlAPIManager(
                api_root=api_root,
                username=username,
                password=password,
                verify_ssl=verify_ssl,
                siemplify_logger=siemplify.LOGGER,
            )

            address_list = manager.get_address_list(address_list_name=address_list_name)
            updated_addresses_data = [
                address
                for address in address_list.addresses
                if address.get("name", "")
                not in [entity.identifier.lower() for entity in suitable_entities]
            ]

            if not updated_addresses_data:
                raise Exception(
                    f"you can't remove all of the IPs from the address list."
                )

            updated_address_list = manager.update_address_list(
                list_name=address_list_name, addresses=updated_addresses_data
            )

            for entity in suitable_entities:
                if entity.identifier.lower() not in [
                    item.get("name") for item in updated_address_list.addresses
                ]:
                    if entity.identifier.lower() in [
                        item.get("name") for item in address_list.addresses
                    ]:
                        successful_entities.append(entity)
                    else:
                        non_existing_entities.append(entity)

            if successful_entities:
                siemplify.result.add_result_json(updated_address_list.to_json())
                output_message += "Successfully removed the following IPs from the {} address list in {}: \n{}".format(
                    address_list_name,
                    INTEGRATION_DISPLAY_NAME,
                    "\n".join([entity.identifier for entity in successful_entities]),
                )

            if non_existing_entities:
                output_message += "\n\nThe following IPs didn't exist in {} address list in {}: \n{}".format(
                    address_list_name,
                    INTEGRATION_DISPLAY_NAME,
                    "\n".join([entity.identifier for entity in non_existing_entities]),
                )
        else:
            result = False
            output_message = "No suitable entities were found in the scope."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {REMOVE_IP_FROM_ADDRESS_LIST_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f'Error executing action "{REMOVE_IP_FROM_ADDRESS_LIST_SCRIPT_NAME}". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
