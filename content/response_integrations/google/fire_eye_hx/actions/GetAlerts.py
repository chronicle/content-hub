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
from ..core.datamodels import AlertSourceTypes
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
import arrow


INTEGRATION_NAME = "FireEyeHX"
SCRIPT_NAME = "Get Alerts"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"  # ISO-8601
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

    hours_backwards = extract_action_param(
        siemplify,
        param_name="Alert reported in last x hours",
        is_mandatory=False,
        input_type=int,
        print_value=True,
    )
    resolution_status = extract_action_param(
        siemplify,
        param_name="Alert Resolution Status",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    alert_source = extract_action_param(
        siemplify,
        param_name="Alert Source",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    has_share_mode = extract_action_param(
        siemplify,
        param_name="Has Share Mode",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    alert_id = extract_action_param(
        siemplify,
        param_name="Alert ID",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    limit = extract_action_param(
        siemplify,
        param_name="Limit",
        is_mandatory=False,
        input_type=int,
        print_value=True,
    )

    reported_at = None

    if resolution_status == "any":
        resolution_status = None

    if has_share_mode == "any":
        has_share_mode = None

    if alert_source:
        alert_source = AlertSourceTypes.get(alert_source)

    if hours_backwards:
        reported_at = arrow.utcnow().shift(hours=-hours_backwards).strftime(TIME_FORMAT)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    successful_entities = []
    no_results_entities = []
    missing_entities = []
    failed_entities = []
    multimatch_entities = []
    json_results = {}
    output_message = ""
    result_value = "false"

    try:
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

                if len(matching_hosts) > 1:
                    siemplify.LOGGER.info(
                        f"Multiple hosts matching entity {entity.identifier} were found. First will be used."
                    )
                    multimatch_entities.append(entity)

                if not matching_hosts:
                    siemplify.LOGGER.info(f"Matching host was not found for entity.")
                    missing_entities.append(entity)
                    continue

                # Take endpoint with the most recent last_poll_timestamp
                host = sorted(
                    matching_hosts,
                    key=lambda matching_host: matching_host.last_poll_timestamp,
                )[-1]
                siemplify.LOGGER.info(
                    f"Matching host was found for {entity.identifier}"
                )

                alerts = hx_manager.get_alerts(
                    limit=limit,
                    has_share_mode=has_share_mode,
                    resolution=resolution_status,
                    agent_id=host._id,
                    reported_at=reported_at,
                    alert_id=alert_id,
                    source=alert_source,
                )

                json_results[entity.identifier] = [alert.raw_data for alert in alerts]

                if alerts:
                    siemplify.LOGGER.info(
                        f"Found {len(alerts)} alerts for {entity.identifier}"
                    )
                    siemplify.result.add_data_table(
                        f"Alerts - {entity.identifier}",
                        construct_csv([alert.as_csv() for alert in alerts]),
                    )
                    successful_entities.append(entity)
                else:
                    siemplify.LOGGER.info(
                        f"No alerts were found for {entity.identifier}"
                    )
                    no_results_entities.append(entity)

                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities or no_results_entities:
            if successful_entities:
                output_message += (
                    "Found alerts for the following entities:\n   {}".format(
                        "\n   ".join(
                            [entity.identifier for entity in successful_entities]
                        )
                    )
                )

            if no_results_entities:
                output_message += "{}Action did not find any FireEye HX alerts for the following entities:\n   {}".format(
                    "\n\n" if successful_entities else "",
                    "\n   ".join([entity.identifier for entity in no_results_entities]),
                )

            result_value = "true"

        else:
            output_message += "No alerts were found."
            result_value = "false"

        if multimatch_entities:
            output_message += (
                "Multiple matches were found in FireEye HX, "
                "taking the agent info with the most recent last poll time value "
                "for the following entities:/n {0}".format(
                    "\n   ".join([entity.identifier for entity in multimatch_entities])
                )
            )

        if missing_entities:
            output_message += "\n\nAction was not able to find matching FireEye HX agent for the following entities:\n   {}".format(
                "\n   ".join([entity.identifier for entity in missing_entities])
            )

        if failed_entities:
            output_message += (
                "\n\nFailed processing the following entities:\n   {}".format(
                    "\n   ".join([entity.identifier for entity in failed_entities])
                )
            )

    except Exception as e:
        siemplify.LOGGER.error(f"Failed to execute action! Error is {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Failed to execute action! Error is {e}"

    finally:
        try:
            hx_manager.logout()
        except Exception as e:
            siemplify.LOGGER.error(f"Logging out failed. Error: {e}")
            siemplify.LOGGER.exception(e)

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
