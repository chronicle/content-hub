from __future__ import annotations
import sys
from datetime import timedelta
from ..core.CybereasonManager import CybereasonManager, MALOP_TYPE
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import (
    output_handler,
    utc_now,
    unix_now,
    convert_unixtime_to_datetime,
)
from TIPCommon import extract_connector_param
from ..core.constants import (
    ALERTS_CONNECTOR_SCRIPT_NAME,
    BLACKLIST_FILTER,
    WHITELIST_FILTER,
    NULL_SEVERITY,
)
from ..core.utils import (
    get_environment_common,
    read_ids,
    write_ids,
    is_overflowed,
    is_approaching_timeout,
    validate_timestamp,
    validate_end_time,
    convert_comma_separated_to_list,
)

DEFAULT_TIME_FRAME = 1
DEFAULT_FETCH_LIMIT = 10
DEFAULT_FETCH_INTERVAL = 12
MAX_PROCESSED_EVENTS_PER_ALERT = 499


def get_events_from_malop_data(malop_data_for_events, data_type, alert):
    return (
        alert.get_events_with_multiple_keys(malop_data_for_events)
        if data_type == MALOP_TYPE
        else alert.get_events(malop_data_for_events)
    )


@output_handler
def main(is_test_run):
    processed_alerts = []
    connector_starting_time = unix_now()
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
            siemplify, param_name="API Root", is_mandatory=True, print_value=True
        )
        username = extract_connector_param(
            siemplify, param_name="Username", is_mandatory=True, print_value=True
        )
        password = extract_connector_param(
            siemplify, param_name="Password", is_mandatory=True, print_value=False
        )
        ca_certificate = extract_connector_param(
            siemplify,
            param_name="CA Certificate Base64",
        )
        verify_ssl = extract_connector_param(
            siemplify,
            param_name="Verify SSL",
            default_value=True,
            input_type=bool,
            print_value=True,
        )
        environment_field_name = extract_connector_param(
            siemplify,
            param_name="Environment Field Name",
            default_value="",
            print_value=True,
        )
        environment_regex_pattern = extract_connector_param(
            siemplify, param_name="Environment Regex Pattern", print_value=True
        )
        python_process_timeout = extract_connector_param(
            siemplify,
            param_name="PythonProcessTimeout",
            input_type=int,
            is_mandatory=True,
            print_value=True,
        )
        severity_filter = extract_connector_param(
            siemplify, param_name="Severity Filter", print_value=True
        )
        status_filter = extract_connector_param(
            siemplify, param_name="Status Filter", print_value=True
        )
        hours_backwards = extract_connector_param(
            siemplify,
            param_name="Max Hours Backwards",
            input_type=int,
            default_value=DEFAULT_TIME_FRAME,
            print_value=True,
        )
        fetch_limit = extract_connector_param(
            siemplify,
            param_name="Max Alerts To Fetch",
            input_type=int,
            default_value=DEFAULT_FETCH_LIMIT,
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
        manager = CybereasonManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            ca_certificate_b64=ca_certificate,
            logger=siemplify.LOGGER,
            force_check_connectivity=True,
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

        end_time = validate_end_time(
            last_success_time_datetime + timedelta(hours=DEFAULT_FETCH_INTERVAL)
        )

        fetched_alerts = []
        alerts_with_new_events = []
        alerts = manager.get_malops_inbox_alerts(
            start_time=last_success_time_datetime, end_time=end_time
        )
        filtered_alerts = sorted(alerts, key=lambda item: item.updating_time)

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} alerts")

        for alert in filtered_alerts:
            try:
                if is_test_run and alerts_with_new_events:
                    siemplify.LOGGER.info(
                        "This is a TEST run. Only 1 alert will be processed."
                    )
                    break

                if len(alerts_with_new_events) >= fetch_limit:
                    siemplify.LOGGER.info(
                        f"Already processed {len(alerts_with_new_events)} alerts. Stopping."
                    )
                    break

                siemplify.LOGGER.info(
                    f"Started processing Alert {alert.guid} - {alert.display_name}",
                    alert_id=alert.guid,
                )

                if is_approaching_timeout(
                    connector_starting_time, python_process_timeout
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                fetched_alerts.append(alert)

                if not pass_whitelist_filter(
                    siemplify, alert, whitelist, whitelist_filter_type
                ):
                    siemplify.LOGGER.info(
                        f"Alert {alert.guid} did not pass filters. Skipping...."
                    )
                    continue

                if not pass_severity_filter(siemplify, alert, severity_filter):
                    siemplify.LOGGER.info(
                        f"Alert {alert.guid} did not pass severity filter. Skipping...."
                    )
                    continue

                if not pass_status_filter(siemplify, alert, status_filter):
                    siemplify.LOGGER.info(
                        f"Alert {alert.guid} did not pass status filter. Skipping...."
                    )
                    continue

                events = []
                try:
                    siemplify.LOGGER.info("Loading events...")
                    malop_details_for_events, data_type = (
                        manager.get_malop_details_for_events(alert.guid)
                    )
                    events = get_events_from_malop_data(
                        malop_details_for_events, data_type, alert
                    )
                    siemplify.LOGGER.info(f"Loaded {len(events)} events.")
                except Exception as e:
                    siemplify.LOGGER.error(f'Failed to load events. Error is "{e}"')

                if existing_ids.get(alert.guid, 0) == len(events):
                    siemplify.LOGGER.info(
                        f"Alert {alert.guid} did not have new events. Skipping...."
                    )
                    continue

                alerts_with_new_events.append(alert)

                alert_infos = []
                for event_chunk in [
                    events[x : x + MAX_PROCESSED_EVENTS_PER_ALERT]
                    for x in range(0, len(events), MAX_PROCESSED_EVENTS_PER_ALERT)
                ]:
                    alert_infos.append(
                        alert.to_alert_info(
                            get_environment_common(
                                siemplify,
                                environment_field_name,
                                environment_regex_pattern,
                            ),
                            event_chunk,
                        )
                    )

                # Update existing alerts
                existing_ids[alert.guid] = len(events)
                if len(alert_infos) > 0:
                    alert_info = alert_infos[0]
                    if is_overflowed(siemplify, alert_info, is_test_run):
                        siemplify.LOGGER.info(
                            f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}-"
                            f"{alert_info.device_product} found as overflow alert. Skipping."
                        )
                        # If is overflowed we should skip
                        continue

                processed_alerts.extend(alert_infos)
                siemplify.LOGGER.info(
                    f"Alert {alert.guid} was created with {len(alert_infos)} cases"
                )

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process alert {alert.guid}")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(f"Finished processing Alert {alert.guid}")

        if not is_test_run:
            if fetched_alerts:
                new_timestamp = fetched_alerts[-1].updating_time
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


def pass_severity_filter(siemplify, alert, severity_filter):
    # severity filter
    if not severity_filter:
        return True

    severity_filter_values = severity_filter.lower()

    if alert.severity.lower() not in convert_comma_separated_to_list(
        severity_filter_values
    ):
        siemplify.LOGGER.info(
            f"Alert with severity: {alert.severity if alert.severity else NULL_SEVERITY} "
            f"did not pass filter. Acceptable severities are: {severity_filter}."
        )

        return False

    return True


def pass_status_filter(siemplify, alert, status_filter):
    # status filter
    if status_filter and alert.status not in convert_comma_separated_to_list(
        status_filter
    ):
        siemplify.LOGGER.info(
            f"Alert with status: {alert.status} did not pass filter. Acceptable statuses are: "
            f"{status_filter}."
        )
        return False
    return True


def pass_whitelist_filter(siemplify, alert, whitelist, whitelist_filter_type):
    # whitelist filter
    if whitelist:
        if (
            whitelist_filter_type == BLACKLIST_FILTER
            and alert.malop_detection_type in whitelist
        ):
            siemplify.LOGGER.info(
                f"Alert with malop detection type: {alert.malop_detection_type} did not pass blacklist filter."
            )
            return False

        if (
            whitelist_filter_type == WHITELIST_FILTER
            and alert.malop_detection_type not in whitelist
        ):
            siemplify.LOGGER.info(
                f"Alert with malop detection type: {alert.malop_detection_type} did not pass whitelist filter."
            )
            return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
