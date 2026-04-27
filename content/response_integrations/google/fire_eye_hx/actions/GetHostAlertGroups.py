from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    unix_now,
    convert_unixtime_to_datetime,
    output_handler,
    convert_dict_to_json_result_dict,
)
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from ..core.FireEyeHXManager import FireEyeHXManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv


INTEGRATION_NAME = "FireEyeHX"
SCRIPT_NAME = "Get Host Alert Groups"
SUPPORTED_ENTITIES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]
ONLY_ACKNOWLEDGED = "Only Acknowledged"
ONLY_UNACKNOWLEDGED = "Only Unacknowledged"


@output_handler
def main():
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

    ack_filter = extract_action_param(
        siemplify,
        param_name="Acknowledgment Filter",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Alert Groups To Return",
        is_mandatory=False,
        input_type=int,
        print_value=True,
    )

    acknowledgement = (
        True
        if ack_filter == ONLY_ACKNOWLEDGED
        else False if ack_filter == ONLY_UNACKNOWLEDGED else None
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    successful_entities = []
    failed_entities = []
    json_results = {}
    output_message = ""
    result_value = True

    try:
        if limit < 1:
            raise Exception('"Max Alert Groups To Return" must be greater than 0.')

        hx_manager = FireEyeHXManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        for entity in siemplify.target_entities:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                if entity.entity_type not in SUPPORTED_ENTITIES:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is of unsupported type. Skipping."
                    )
                    continue

                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                matching_hosts = []

                if entity.entity_type == EntityTypes.HOSTNAME:
                    siemplify.LOGGER.info(
                        f"Fetching host for hostname {entity.identifier}"
                    )
                    matching_hosts = hx_manager.get_hosts(host_name=entity.identifier)

                elif entity.entity_type == EntityTypes.ADDRESS:
                    siemplify.LOGGER.info(
                        f"Fetching host for address {entity.identifier}"
                    )
                    matching_hosts = hx_manager.get_hosts_by_ip(
                        ip_address=entity.identifier
                    )

                if not matching_hosts:
                    siemplify.LOGGER.info(f"Matching host was not found for entity.")
                    failed_entities.append(entity)
                    continue

                # Take endpoint with the most recent last_poll_timestamp
                host = sorted(
                    matching_hosts,
                    key=lambda matching_host: matching_host.last_poll_timestamp,
                )[-1]
                siemplify.LOGGER.info(
                    f"Matching host was found for {entity.identifier}"
                )

                alert_groups = hx_manager.get_alert_groups(
                    host_id=host._id, acknowledgement=acknowledgement, limit=limit
                )

                if alert_groups:
                    json_results[entity.identifier] = [
                        group.to_json() for group in alert_groups
                    ]
                    siemplify.LOGGER.info(
                        f"Found {len(alert_groups)} alert groups for {entity.identifier}"
                    )
                    siemplify.result.add_data_table(
                        f"Alert Groups - {entity.identifier}",
                        construct_csv([group.as_csv() for group in alert_groups]),
                    )
                    successful_entities.append(entity)
                else:
                    siemplify.LOGGER.info(
                        f"No alert groups were found for {entity.identifier}"
                    )
                    failed_entities.append(entity)

                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_message += "Successfully retrieved alert groups for the following entities in {}:\n  {}".format(
                INTEGRATION_NAME,
                "\n   ".join([entity.identifier for entity in successful_entities]),
            )

            if failed_entities:
                output_message += (
                    "\n\nAction wasn't able to retrieve alert groups for the following entities in {}:"
                    "\n  {}".format(
                        INTEGRATION_NAME,
                        "\n   ".join([entity.identifier for entity in failed_entities]),
                    )
                )
        else:
            result_value = False
            output_message = f"No alert groups were found for the provided entities in {INTEGRATION_NAME}."

    except Exception as e:
        siemplify.LOGGER.error(f"Failed to execute action! Error is {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f'Error executing action "{SCRIPT_NAME}". Reason: {e}'

    finally:
        try:
            hx_manager.logout()
        except Exception as e:
            siemplify.LOGGER.error(f"Logging out failed. Error: {e}")
            siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
