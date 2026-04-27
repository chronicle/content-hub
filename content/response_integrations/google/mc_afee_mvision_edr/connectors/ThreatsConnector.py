from __future__ import annotations
import sys

from EnvironmentCommon import GetEnvironmentCommonFactory
from ..core.McAfeeMvisionEDRManager import McAfeeMvisionEDRManager
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import (
    output_handler,
    utc_now,
    convert_datetime_to_unix_time,
    unix_now,
)
from TIPCommon import (
    extract_connector_param,
    read_ids,
    write_ids,
    is_overflowed,
    get_last_success_time,
    save_timestamp,
    is_approaching_timeout,
    UNIX_FORMAT,
)
from ..core.constants import (
    CONNECTOR_NAME,
    DEFAULT_TIME_FRAME,
    BLACKLIST_FILTER,
    WHITELIST_FILTER,
    STORED_IDS_LIMIT,
    ACCEPTABLE_TIME_INTERVAL_IN_MINUTES,
    DEFAULT_SEVERITY,
)

connector_starting_time = unix_now()


@output_handler
def main(is_test_run):
    processed_alerts = []
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    api_root = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True, input_type=str
    )
    login_api_root = extract_connector_param(
        siemplify, param_name="Login API Root", is_mandatory=False, input_type=str
    )
    username = extract_connector_param(
        siemplify, param_name="Username", is_mandatory=False, input_type=str
    )
    password = extract_connector_param(
        siemplify, param_name="Password", is_mandatory=False, input_type=str
    )
    client_id = extract_connector_param(
        siemplify, param_name="Client ID", is_mandatory=False, input_type=str
    )
    client_secret = extract_connector_param(
        siemplify, param_name="Client Secret", is_mandatory=False, input_type=str
    )
    verify_ssl = extract_connector_param(
        siemplify, param_name="Verify SSL", default_value=True, input_type=bool
    )

    environment_field_name = extract_connector_param(
        siemplify, param_name="Environment Field Name", default_value="", input_type=str
    )
    environment_regex_pattern = extract_connector_param(
        siemplify,
        param_name="Environment Regex Pattern",
        default_value="",
        input_type=str,
    )

    fetch_limit = extract_connector_param(
        siemplify, param_name="Max Threats To Fetch", input_type=int
    )
    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Fetch Max Hours Backwards",
        input_type=int,
        default_value=DEFAULT_TIME_FRAME,
    )

    lowest_severity = extract_connector_param(
        siemplify,
        param_name="Lowest Severity To Fetch",
        input_type=str,
        default_value=DEFAULT_SEVERITY,
    )

    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use whitelist as a blacklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )

    whitelist_filter_type = (
        BLACKLIST_FILTER if whitelist_as_a_blacklist else WHITELIST_FILTER
    )

    whitelist = siemplify.whitelist

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        # Read already existing alerts ids
        siemplify.LOGGER.info("Reading already existing alerts ids...")
        existing_ids = read_ids(siemplify)

        siemplify.LOGGER.info("Fetching threats...")
        manager = McAfeeMvisionEDRManager(
            api_root,
            username,
            password,
            client_id,
            client_secret,
            verify_ssl,
            siemplify,
            login_api_root=login_api_root,
        )

        fetched_alerts = []
        filtered_alerts = manager.get_threats(
            existing_ids=existing_ids,
            start_time=get_last_success_time(
                siemplify=siemplify,
                offset_with_metric={"hours": hours_backwards},
                time_format=UNIX_FORMAT,
            ),
            limit=fetch_limit,
            severity=lowest_severity,
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} threats")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                if len(processed_alerts) >= fetch_limit:
                    # Provide slicing for the alarms amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle. "
                        "No more alerts will be processed in this cycle."
                    )
                    break

                siemplify.LOGGER.info(
                    f"Started processing Alert {alert.threat_id} - {alert.name} ",
                    alert_id=alert.threat_id,
                )

                if is_approaching_timeout(
                    connector_starting_time=connector_starting_time,
                    python_process_timeout=python_process_timeout,
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                if not pass_time_filter(siemplify, alert):
                    siemplify.LOGGER.info(
                        f"Alerts which are older then {ACCEPTABLE_TIME_INTERVAL_IN_MINUTES} minutes fetched. Stopping connector...."
                    )
                    break

                siemplify.LOGGER.info("Attaching detections to alert")
                # for this we send request to backend, that is why we should attach only after passing all filters.
                # EXCEPT whitelist filter, since we are saving alert id before that filter to avoid infinite loop.
                # and we can not call attach_detections AFTER saving alert id
                # since if attach_detections gives one time error we will loose that alert.
                alert = attach_detections(alert, manager)

                # Update existing alerts
                existing_ids.append(alert.threat_id)
                fetched_alerts.append(alert)

                if not pass_whitelist_filter(
                    siemplify, alert, whitelist, whitelist_filter_type
                ):
                    siemplify.LOGGER.info(
                        f"Alert {alert.threat_id} did not pass filters skipping...."
                    )
                    continue

                # Get environment
                common_environment = (
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify=siemplify,
                        environment_field_name=environment_field_name,
                        environment_regex_pattern=environment_regex_pattern,
                    )
                )
                alert_info = alert.get_alert_info(
                    alert_info=AlertInfo(), environment_common=common_environment
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        "{alert_name}-{alert_identifier}-{environment}-{product} found as overflow alert. "
                        "Skipping.".format(
                            alert_name=str(alert_info.rule_generator),
                            alert_identifier=str(alert_info.ticket_id),
                            environment=str(alert_info.environment),
                            product=str(alert_info.device_product),
                        )
                    )
                    # If is overflowed we should skip
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alert.threat_id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed to process alert {alert.threat_id}",
                    alert_id=alert.threat_id,
                )
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(
                f"Finished processing Alert {alert.threat_id}", alert_id=alert.threat_id
            )

        if not is_test_run:
            save_timestamp(siemplify=siemplify, alerts=fetched_alerts)
            write_ids(siemplify, existing_ids, stored_ids_limit=STORED_IDS_LIMIT)

    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {err}")
        siemplify.LOGGER.exception(err)
        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def pass_time_filter(siemplify, alert):
    # time filter
    time_passed_from_first_detected_in_minutes = (
        convert_datetime_to_unix_time(utc_now()) - alert.first_detected
    ) / 60000
    if (
        time_passed_from_first_detected_in_minutes
        <= ACCEPTABLE_TIME_INTERVAL_IN_MINUTES
    ):
        siemplify.LOGGER.info(
            f"Alert did not pass time filter. Detected approximately {str(time_passed_from_first_detected_in_minutes)} minutes ago."
        )
        return False
    return True


def pass_whitelist_filter(siemplify, alert, whitelist, whitelist_filter_type):
    # whitelist filter
    if whitelist:
        if whitelist_filter_type == BLACKLIST_FILTER and alert.name in whitelist:
            siemplify.LOGGER.info(
                f"Threat with name: {alert.name} did not pass blacklist filter."
            )
            return False

        if whitelist_filter_type == WHITELIST_FILTER and alert.name not in whitelist:
            siemplify.LOGGER.info(
                f"Threat with name: {alert.name} did not pass whitelist filter."
            )
            return False

    return True


def attach_detections(alert, manager):
    """
    Attach detections to alert.
    :param alert: {Threat} The alert to attach detections
    :param manager: {McAfeeMvisionEDRManager} The manager to fetch detections
    :return: {Threat} The same alert with detections
    """
    alert.detections = manager.get_detections(alert.threat_id)

    return alert


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
