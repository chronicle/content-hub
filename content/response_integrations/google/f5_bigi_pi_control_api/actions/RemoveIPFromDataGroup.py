from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.F5BIGIPiControlAPIManager import F5BIGIPiControlAPIManager
from ..core.F5BIGIPiControlAPIExceptions import InvalidDataGroupException
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    REMOVE_IP_FROM_DATA_GROUP_SCRIPT_NAME,
    IP_GROUP_TYPE,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.UtilsManager import mask_ip_address


SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = REMOVE_IP_FROM_DATA_GROUP_SCRIPT_NAME
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
    data_group_name = extract_action_param(
        siemplify, param_name="Data Group Name", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities = []
    failed_entities = []
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

            data_group = manager.get_data_group(group_name=data_group_name)

            if data_group.type != IP_GROUP_TYPE:
                raise InvalidDataGroupException(
                    f"data group {data_group_name} was not found or doesn't have the"
                    f" IP type in {INTEGRATION_DISPLAY_NAME}. Please check the spelling."
                )

            for entity in suitable_entities:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                ip_address = mask_ip_address(entity.identifier)
                record_names = [record.get("name") for record in data_group.records]

                if ip_address in record_names:
                    data_group.records.pop(record_names.index(ip_address))
                    successful_entities.append(entity)
                else:
                    failed_entities.append(entity)

                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

            if data_group.records:
                updated_data_group = manager.update_data_group(
                    group_name=data_group_name, records=data_group.records
                )
            else:
                raise Exception("you can't remove all of the IPs from the data group")

            if successful_entities:
                siemplify.result.add_result_json(updated_data_group.to_json())
                output_message += "Successfully removed the following IPs from the {} data group in {}: \n{}".format(
                    data_group_name,
                    INTEGRATION_DISPLAY_NAME,
                    "\n".join([entity.identifier for entity in successful_entities]),
                )
            if failed_entities:
                output_message += "\nThe following IPs didn't exist in {} data group in {}: \n{}".format(
                    data_group_name,
                    INTEGRATION_DISPLAY_NAME,
                    "\n".join([entity.identifier for entity in failed_entities]),
                )
        else:
            result = False
            output_message = "No suitable entities were found in the scope."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {REMOVE_IP_FROM_DATA_GROUP_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f'Error executing action "{REMOVE_IP_FROM_DATA_GROUP_SCRIPT_NAME}". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
