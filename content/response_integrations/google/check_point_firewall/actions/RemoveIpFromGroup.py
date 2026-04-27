from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CheckpointManager import CheckpointManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import (
    INTEGRATION_NAME,
    REMOVE_IP_FROM_GROUP_SCRIPT_NAME,
    PARAMETERS_NEW_LINE_DELIMITER,
)
from ..core.exceptions import InvalidGroupException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = REMOVE_IP_FROM_GROUP_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Server Address",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    domain_name = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Domain",
        is_mandatory=False,
        default_value="",
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )
    policy_name = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Policy Name",
        is_mandatory=True,
    )
    group_name = extract_action_param(
        siemplify,
        param_name="Blacklist Group Name",
        print_value=True,
        is_mandatory=True,
    )

    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = True
    successful_entities, failed_entities = [], []
    relevant_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.ADDRESS
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = CheckpointManager(
            server_address=server_address,
            username=username,
            password=password,
            domain=domain_name,
            verify_ssl=verify_ssl,
        )

        for entity in relevant_entities:
            try:
                siemplify.LOGGER.info(
                    f"\n\nStart process for the following entity: {entity}"
                )
                manager.unblock_ip_in_policy_group(entity.identifier, group_name)
                successful_entities.append(entity.identifier)
                siemplify.LOGGER.info(
                    f"Successfully processed the following entity: {entity}"
                )
            except InvalidGroupException:
                raise
            except Exception as err:
                failed_entities.append(entity.identifier)
                siemplify.LOGGER.error(
                    f"Action was not able to process the following entity: {entity}"
                )
                siemplify.LOGGER.exception(err)

            siemplify.LOGGER.info(f"End process for the following entity: {entity}")

        if successful_entities:
            output_message += f"Successfully removed the following IPs from the {group_name} Checkpoint FireWall Group: {PARAMETERS_NEW_LINE_DELIMITER.join(successful_entities)}\n"

        if failed_entities:
            output_message += (
                "Action wasn’t able to remove the following IPs from the {} Checkpoint FireWall Group: "
                "{}\n".format(
                    group_name, PARAMETERS_NEW_LINE_DELIMITER.join(failed_entities)
                )
            )

        if not successful_entities:
            output_message = (
                f"No IPs were removed from the {group_name} Checkpoint FireWall Group."
            )
            result_value = False

        # All the changes done will be effective only after install is called.
        manager.install_policy(policy_name)
        manager.log_out()
    except Exception as err:
        output_message = f"No IPs were removed from the {group_name} Checkpoint FireWall Group. Reason: {err} "
        result_value = False
        # For invalid groups playbook should not stop
        if not isinstance(err, InvalidGroupException):
            status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
