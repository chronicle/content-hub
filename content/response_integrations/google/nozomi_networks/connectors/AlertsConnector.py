from __future__ import annotations
import sys
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import (
    output_handler,
    utc_now,
    unix_now,
    convert_unixtime_to_datetime,
)
from ..core.NozomiNetworksManager import NozomiNetworksManager
from ..core.UtilsManager import (
    get_environment_common,
    read_ids,
    write_ids,
    is_overflowed,
    is_approaching_timeout,
    validate_timestamp,
)
from TIPCommon import extract_connector_param
from datetime import timedelta

from ..core.NozomiNetworksConstants import (
    ALERTS_CONNECTOR_SCRIPT_NAME,
    DEFAULT_TIME_FRAME,
    DEFAULT_FETCH_INTERVAL,
    ACCEPTABLE_TIME_INTERVAL_IN_MINUTES,
    WHITELIST_FILTER,
    BLACKLIST_FILTER,
)

connector_starting_time = unix_now()


@output_handler
def main(is_test_run):
    processed_alerts = []
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = ALERTS_CONNECTOR_SCRIPT_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    try:
        siemplify.LOGGER.info(
            "------------------- Main - Param Init -------------------"
        )

        api_root = extract_connector_param(
            siemplify, param_name="API URL", is_mandatory=True, print_value=True
        )
        username = extract_connector_param(
            siemplify, param_name="Username", is_mandatory=True, print_value=True
        )
        password = extract_connector_param(
            siemplify, param_name="Password", is_mandatory=True, print_value=False
        )
        verify_ssl = extract_connector_param(
            siemplify,
            param_name="Verify SSL",
            default_value=False,
            input_type=bool,
            print_value=True,
        )
        ca_certificate = extract_connector_param(
            siemplify,
            param_name="CA Certificate File",
            is_mandatory=False,
            print_value=False,
        )
        environment_field_name = extract_connector_param(
            siemplify,
            param_name="Environment Field Name",
            default_value="",
            print_value=True,
        )
        environment_regex_pattern = extract_connector_param(
            siemplify,
            param_name="Environment Regex Pattern",
            default_value=".*",
            print_value=True,
        )
        python_process_timeout = extract_connector_param(
            siemplify,
            param_name="PythonProcessTimeout",
            input_type=int,
            is_mandatory=True,
            print_value=True,
        )
        lowest_severity_to_fetch = extract_connector_param(
            siemplify, param_name="Minimum severity to fetch", input_type=int
        )
        is_security = extract_connector_param(
            siemplify,
            param_name="Ingest only alerts that have “is_security” "
            "attribute set to True?",
            default_value=False,
            input_type=bool,
            print_value=True,
        )
        is_incident = extract_connector_param(
            siemplify,
            param_name="Ingest only alerts that have “is_incident” "
            "attribute set to True?",
            default_value=False,
            input_type=bool,
            print_value=True,
        )
        hours_backwards = extract_connector_param(
            siemplify,
            param_name="Fetch Max Hours Backwards",
            input_type=int,
            default_value=DEFAULT_TIME_FRAME,
            is_mandatory=True,
            print_value=True,
        )
        fetch_interval = extract_connector_param(
            siemplify,
            param_name="Fetch Backwards Time Interval (minutes)",
            input_type=int,
            is_mandatory=True,
            default_value=DEFAULT_FETCH_INTERVAL,
            print_value=True,
        )
        whitelist_as_a_blacklist = extract_connector_param(
            siemplify,
            "Use whitelist as a blacklist",
            is_mandatory=True,
            input_type=bool,
            print_value=True,
        )

        whitelist_filter_type = (
            BLACKLIST_FILTER if whitelist_as_a_blacklist else WHITELIST_FILTER
        )

        whitelist = siemplify.whitelist

        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        # Read already existing alerts ids
        siemplify.LOGGER.info("Reading already existing alerts ids...")
        existing_ids = read_ids(siemplify)

        siemplify.LOGGER.info("Fetching alerts...")
        manager = NozomiNetworksManager(
            api_root=api_root,
            username=username,
            password=password,
            ca_certificate_file=ca_certificate,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        if is_test_run:
            siemplify.LOGGER.info("This is a test run. Ignoring stored timestamps")
            last_success_time_datetime = validate_timestamp(
                utc_now() - timedelta(hours=hours_backwards), hours_backwards
            )
        else:
            last_success_time_datetime = validate_timestamp(
                siemplify.fetch_timestamp(datetime_format=True), hours_backwards
            )

        fetched_alerts = []
        filtered_alerts = manager.get_alerts(
            existing_ids=existing_ids,
            start_time=last_success_time_datetime,
            time_interval=fetch_interval,
            lowest_severity=lowest_severity_to_fetch,
            is_security=is_security,
            is_incident=is_incident,
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} alerts")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                siemplify.LOGGER.info(
                    f"Started processing Alert {alert.id} - {alert.name}",
                    alert_id=alert.id,
                )

                if is_approaching_timeout(
                    connector_starting_time, python_process_timeout
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

                # Update existing alerts
                existing_ids.append(alert.id)
                fetched_alerts.append(alert)

                if not pass_whitelist_filter(
                    siemplify, alert, whitelist, whitelist_filter_type
                ):
                    siemplify.LOGGER.info(
                        f"Alert {alert.id} did not pass filters skipping...."
                    )
                    continue

                alert_info = alert.to_alert_info(
                    get_environment_common(
                        siemplify, environment_field_name, environment_regex_pattern
                    )
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}-{alert_info.device_product} found as overflow alert. Skipping."
                    )
                    # If is overflowed we should skip
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alert.id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed to process alert {alert.id}", alert_id=alert.id
                )
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(
                f"Finished processing Alert {alert.id}", alert_id=alert.id
            )

        if not is_test_run:
            if fetched_alerts:
                new_timestamp = fetched_alerts[-1].created_time
                siemplify.save_timestamp(new_timestamp=new_timestamp)
                siemplify.LOGGER.info(
                    f"New timestamp {convert_unixtime_to_datetime(new_timestamp).isoformat()} has been saved"
                )

            write_ids(siemplify, existing_ids)

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
        unix_now() - alert.created_time
    ) / 60000
    if (
        time_passed_from_first_detected_in_minutes
        <= ACCEPTABLE_TIME_INTERVAL_IN_MINUTES
    ):
        siemplify.LOGGER.info(
            f"Alert did not pass time filter. Detected approximately {time_passed_from_first_detected_in_minutes} minutes ago."
        )
        return False
    return True


def pass_whitelist_filter(siemplify, alert, whitelist, whitelist_filter_type):
    # whitelist filter
    if whitelist:
        if whitelist_filter_type == BLACKLIST_FILTER and alert.type_name in whitelist:
            siemplify.LOGGER.info(
                f"Alert with type name: {alert.type_name} did not pass blacklist filter."
            )
            return False

        if (
            whitelist_filter_type == WHITELIST_FILTER
            and alert.type_name not in whitelist
        ):
            siemplify.LOGGER.info(
                f"Alert with type name: {alert.type_name} did not pass whitelist filter."
            )
            return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
