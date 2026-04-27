from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SonicWallManager import SonicWallManager
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.UtilsManager import valid_ip_address
from ..core.constants import (
    INTEGRATION_NAME,
    ADD_IP_SCRIPT_NAME,
    IPV4_TYPE_STRING,
    IPV6_TYPE_STRING,
)

from ..core.SonicWallExceptions import UnableToAddException, UnauthorizedException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_IP_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration.
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        input_type=str,
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        input_type=str,
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    # Parameters
    group_name = extract_action_param(
        siemplify, param_name="Group Name", is_mandatory=True
    )
    ip_zone = extract_action_param(siemplify, param_name="IP Zone", is_mandatory=True)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = "true"
    output_message = ""
    successful_entities = []
    failed_entities = []
    ipv4_entities = []
    ipv6_entities = []
    ipv4_group = None
    ipv6_group = None

    try:
        sonic_wall_manager = SonicWallManager(
            api_root,
            username,
            password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        address_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type == EntityTypes.ADDRESS
        ]
        for entity in address_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            ip_type = valid_ip_address(entity.identifier)
            if ip_type == IPV4_TYPE_STRING:
                ipv4_group = sonic_wall_manager.check_group(group_name, ip_type)
                ipv4_entities.append(entity)
            elif ip_type == IPV6_TYPE_STRING:
                ipv6_group = sonic_wall_manager.check_group(group_name, ip_type)
                ipv6_entities.append(entity)
            else:
                siemplify.LOGGER.info(
                    f"Finished processing entity: {entity.identifier}"
                )
                continue
            siemplify.LOGGER.info(f"Finished processing entity: {entity.identifier}")

        if ipv4_group:
            for entity in ipv4_entities:
                try:
                    object_name = sonic_wall_manager.create_address_object(
                        IPV4_TYPE_STRING, ip_zone, entity.identifier
                    )
                    sonic_wall_manager.add_ip_to_address_group(
                        IPV4_TYPE_STRING, group_name, object_name
                    )
                    sonic_wall_manager.confirm_changes()
                    successful_entities.append(entity)
                except UnableToAddException as e:
                    reason_message = str(e.args[0].message)
                    command_message = str(e.args[0].command)
                    failed_entities.append(
                        {
                            "entity": entity,
                            "reason": reason_message,
                            "command": command_message,
                        }
                    )

        if ipv6_group:
            for entity in ipv6_entities:
                try:
                    object_name = sonic_wall_manager.create_address_object(
                        IPV6_TYPE_STRING, ip_zone, entity.identifier
                    )
                    sonic_wall_manager.add_ip_to_address_group(
                        IPV6_TYPE_STRING, group_name, object_name
                    )
                    sonic_wall_manager.confirm_changes()
                    successful_entities.append(entity)
                except UnableToAddException as e:
                    reason_message = str(e.args[0].message)
                    command_message = str(e.args[0].command)
                    failed_entities.append(
                        {
                            "entity": entity,
                            "reason": reason_message,
                            "command": command_message,
                        }
                    )

        if successful_entities:
            output_message = 'Successfully added the following IPs to the SonicWall Address Group "{}": {}'.format(
                group_name,
                "\n".join([entity.identifier for entity in successful_entities]),
            )

        if failed_entities:
            for item in failed_entities:
                output_message += (
                    '\n\nAction was not able to add the following IP to the SonicWall Address Group "{}"'
                    ": {}. \nReason: {}. Command: {}.".format(
                        group_name,
                        item.get("entity"),
                        item.get("reason"),
                        item.get("command"),
                    )
                )

        if not successful_entities:
            output_message = ""
            for item in failed_entities:
                output_message += (
                    '\nIP address was not added to the SonicWall Address Group "{}"'
                    ": {}. \nReason: {}. Command: {}.".format(
                        group_name,
                        item.get("entity"),
                        item.get("reason"),
                        item.get("command"),
                    )
                )
            result_value = "false"

        if not ipv4_group and not ipv6_group:
            output_message = f'Address Group "{group_name}" wasn\'t found in SonicWall'
            result_value = "false"
        elif (not ipv4_group and ipv4_entities) or (not ipv6_group and ipv6_entities):
            ip_type = IPV4_TYPE_STRING if not ipv4_group else IPV6_TYPE_STRING
            output_message += (
                f'\n\n{ip_type} Address Group "{group_name}" wasn\'t found in SonicWall'
            )

        if not address_entities:
            output_message = "No suitable entities found"
            result_value = "false"

    except UnauthorizedException as e:
        output_message = str(e)
        result_value = "false"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    except Exception as e:
        output_message = (
            f'Error executing action "Add IP to Address Group". Reason: {e}'
        )
        result_value = "false"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
