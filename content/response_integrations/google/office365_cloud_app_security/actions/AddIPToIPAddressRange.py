from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.Office365CloudAppSecurityManager import Office365CloudAppSecurityManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.SiemplifyUtils import output_handler
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    ADD_IP_TO_IP_ADDRESS_RANGE_SCRIPT_NAME,
)
from ..core.utils import (
    get_entity_original_identifier,
    build_temporary_name,
    find_ip_address_range_by_name,
)
from ..core.Office365CloudAppSecurityExceptions import (
    Office365CloudAppSecurityAlreadyExistingError,
)


SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_IP_TO_IP_ADDRESS_RANGE_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="portal URL",
        input_type=str,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API token",
        input_type=str,
    )

    # action parameter
    name = extract_action_param(
        siemplify, param_name="Name", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = True
    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    successful_entities, already_existing_entities, failed_entities = [], [], []
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        cloud_app_manager = Office365CloudAppSecurityManager(
            api_root=api_root, api_token=api_token
        )

        # find ip address range by name
        ip_address_ranges = cloud_app_manager.get_ip_address_ranges()
        ip_address_range = find_ip_address_range_by_name(ip_address_ranges, name)

        if not ip_address_range:
            raise Exception(
                f"IP address range {name} wasn't found in {INTEGRATION_DISPLAY_NAME}. Please check "
                f"the spelling."
            )

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"\nStarted processing entity: {entity.identifier}")
            entity_identifier = get_entity_original_identifier(entity)

            try:
                if entity_identifier in ip_address_range.subnets:
                    raise Office365CloudAppSecurityAlreadyExistingError

                cloud_app_manager.update_ip_address_range(
                    build_temporary_name(ip_address_range.name),
                    ip_address_range,
                    [*ip_address_range.subnets, entity_identifier],
                )
                # same request is sent twice to recover original name of the ip address range
                cloud_app_manager.update_ip_address_range(
                    ip_address_range.name,
                    ip_address_range,
                    [*ip_address_range.subnets, entity_identifier],
                )
                ip_address_range.subnets.append(entity_identifier)
                successful_entities.append(entity)

            except Office365CloudAppSecurityAlreadyExistingError:
                siemplify.LOGGER.error(
                    f"Entity {entity.identifier} already part of the {name} IP Address Range"
                )
                already_existing_entities.append(entity)
            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed processing entity: {entity.identifier}: Error is: {e}"
                )
                failed_entities.append(entity)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}\n")

        updated_ip_address_range = cloud_app_manager.get_ip_address_range(
            ip_address_range.id
        )

        if successful_entities:
            siemplify.result.add_result_json(updated_ip_address_range.to_json())
            output_message = "Successfully added the following IPs to the {} IP Address Range in {}: \n {}".format(
                name,
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in successful_entities]),
            )

        if already_existing_entities:
            output_message += "\nThe following IPs are already a part of {} IP Address Range in {}: \n {}".format(
                name,
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in already_existing_entities]),
            )

        if failed_entities:
            output_message += "\nAction wasn't able to add the following IPs to the {} IP Address Range in {}: \n {}".format(
                name,
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in failed_entities]),
            )

        if not successful_entities:
            result_value = False
            output_message = f"None of the IPs were added to the IP Address Range in {INTEGRATION_DISPLAY_NAME}."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {ADD_IP_TO_IP_ADDRESS_RANGE_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f'Error executing action "{ADD_IP_TO_IP_ADDRESS_RANGE_SCRIPT_NAME}". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
