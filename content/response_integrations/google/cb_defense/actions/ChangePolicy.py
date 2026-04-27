from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_unixtime_to_datetime
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.CarbonBlackDefenseManager import CBDefenseManager, CBDefenseManagerException


INTEGRATION_NAME = "CBDefense"
SCRIPT_NAME = "Change Policy"
SUPPORTED_ENTITIES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Key",
        is_mandatory=True,
    )

    policy_name = extract_action_param(
        siemplify, param_name="Policy Name", print_value=True, is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    successful_entities = []
    missing_entities = []
    failed_entities = []
    output_message = ""
    result_value = "true"

    try:
        siemplify.LOGGER.info("Connecting to Carbon Black Defense.")
        cb_defense = CBDefenseManager(api_root, api_key)
        cb_defense.test_connectivity()

        for entity in siemplify.target_entities:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                execution_deadline = convert_unixtime_to_datetime(
                    siemplify.execution_deadline_unix_time_ms
                )
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline "
                    f"({execution_deadline}) "
                    f"has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                if entity.entity_type not in SUPPORTED_ENTITIES:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is of unsupported type. Skipping."
                    )
                    continue

                siemplify.LOGGER.info(
                    f"Started processing entity: {entity.identifier}"
                )

                siemplify.LOGGER.info(f"Fetching device data for {entity.identifier}.")
                device_data = None

                if entity.entity_type == EntityTypes.ADDRESS:
                    device_data = cb_defense.get_device_data_by_ip(entity.identifier)

                elif entity.entity_type == EntityTypes.HOSTNAME:
                    device_data = cb_defense.get_device_data_by_hostname(
                        entity.identifier
                    )

                if device_data:
                    siemplify.LOGGER.info(
                        f"Device data was found for {entity.identifier}."
                    )
                    device_id = device_data.device_id

                    siemplify.LOGGER.info(
                        f"Updating device {device_id} for policy {policy_name}."
                    )
                    cb_defense.change_policy(device_id, policy_name)

                    successful_entities.append(entity)

                else:
                    siemplify.LOGGER.info(
                        f"No device data was found for {entity.identifier}"
                    )
                    missing_entities.append(entity)

            except CBDefenseManagerException:
                # Device was not found for this entity in CB(get_device_data_by_ip)
                # and get_device_data_by_hostname raise CBDefenseManagerException
                # if no device is found) - entity is irrelevant, continue.
                siemplify.LOGGER.info(
                    f"No device data was found for {entity.identifier}"
                )
                missing_entities.append(entity)
                continue

            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message += (
                "Policy changed for the following entities:\n   {}\n\n".format(
                    "\n   ".join([entity.identifier for entity in successful_entities])
                )
            )

        else:
            output_message += "No suitable entities found.\n\n"

        if missing_entities:
            output_message += ("Action was not able to find device data "
                               "for the following entities:\n   {}\n\n").format(
                "\n   ".join([entity.identifier for entity in missing_entities])
            )

        if failed_entities:
            output_message += (
                "Failed changing the policy the following entities:\n   {}\n\n".format(
                    "\n   ".join([entity.identifier for entity in failed_entities])
                )
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error occurred while running action {SCRIPT_NAME}. Error: {e}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"An error occurred while running action. Error: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
