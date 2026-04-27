from __future__ import annotations
import sys
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import (
    output_handler,
    utc_now,
    unix_now,
    convert_string_to_unix_time,
    convert_string_to_datetime,
)
from ..core.DigitalShadowsManager import DigitalShadowsManager
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

from ..core.DigitalShadowsConstants import (
    INCIDENTS_CONNECTOR_NAME,
    DEFAULT_TIME_FRAME,
    ACCEPTABLE_TIME_INTERVAL_IN_MINUTES,
    WHITELIST_FILTER,
    BLACKLIST_FILTER,
    ALERTS_LIMIT,
    DEFAULT_SEVERITY,
    DATETIME_STR_FORMAT,
    API_MAX_FETCH_LIMIT,
)

connector_starting_time = unix_now()


@output_handler
def main(is_test_run):
    processed_alerts = []
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = INCIDENTS_CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    api_key = extract_connector_param(
        siemplify, param_name="API Key", is_mandatory=True
    )
    api_secret = extract_connector_param(
        siemplify, param_name="API Secret", is_mandatory=True
    )
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )
    environment_field_name = extract_connector_param(
        siemplify, param_name="Environment Field Name", default_value=""
    )
    environment_regex_pattern = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern", default_value=".*"
    )
    lowest_severity_to_fetch = extract_connector_param(
        siemplify,
        param_name="Lowest Severity To Fetch",
        default_value=DEFAULT_SEVERITY,
        is_mandatory=True,
    )
    incident_type_filter = extract_connector_param(
        siemplify, param_name="Incident Type Filter"
    )
    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Fetch Max Hours Backwards",
        input_type=int,
        default_value=DEFAULT_TIME_FRAME,
    )
    limit = extract_connector_param(
        siemplify,
        param_name="Max Incidents To Fetch",
        input_type=int,
        default_value=ALERTS_LIMIT,
    )

    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        param_name="Use whitelist as a blacklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    whitelist_filter_type = (
        BLACKLIST_FILTER if whitelist_as_a_blacklist else WHITELIST_FILTER
    )

    whitelist = siemplify.whitelist

    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )

    if limit > API_MAX_FETCH_LIMIT:
        limit = API_MAX_FETCH_LIMIT
        siemplify.LOGGER.error(
            "Parameter: Max Incidents To Fetch can't be higher than {0}. This is API limitation."
            " Using max value of {0}.".format(API_MAX_FETCH_LIMIT)
        )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        # Read already existing alerts ids
        siemplify.LOGGER.info("Reading already existing alerts ids...")
        existing_ids = read_ids(siemplify)

        siemplify.LOGGER.info("Fetching alerts...")
        manager = DigitalShadowsManager(
            api_key=api_key,
            api_secret=api_secret,
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
        filtered_alerts = manager.get_incidents(
            existing_ids=existing_ids,
            start_time=last_success_time_datetime.strftime(DATETIME_STR_FORMAT),
            end_time=utc_now().strftime(DATETIME_STR_FORMAT),
            types=(
                [t.strip() for t in incident_type_filter.split(",") if t.strip()]
                if incident_type_filter
                else []
            ),
            lowest_severity=lowest_severity_to_fetch,
            fetch_limit=limit,
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} alerts")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                siemplify.LOGGER.info(
                    f"Started processing Alert {alert.id} - {alert.title}",
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
                new_timestamp = convert_string_to_datetime(fetched_alerts[-1].published)
                siemplify.save_timestamp(new_timestamp=new_timestamp)
                siemplify.LOGGER.info(
                    f"New timestamp {new_timestamp.isoformat()} has been saved"
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
        unix_now() - convert_string_to_unix_time(alert.published)
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
        if whitelist_filter_type == BLACKLIST_FILTER and alert.title in whitelist:
            siemplify.LOGGER.info(
                f"Alert with name: {alert.title} did not pass blacklist filter."
            )
            return False

        if whitelist_filter_type == WHITELIST_FILTER and alert.title not in whitelist:
            siemplify.LOGGER.info(
                f"Alert with name: {alert.title} did not pass whitelist filter."
            )
            return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
