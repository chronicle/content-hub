from __future__ import annotations
import requests
import sys
from datetime import timedelta
from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import (
    output_handler,
    unix_now,
    utc_now,
    convert_datetime_to_unix_time,
)
from TIPCommon import (
    extract_connector_param,
    read_ids,
    write_ids,
    get_last_success_time,
    is_approaching_timeout,
    is_overflowed,
    pass_whitelist_filter,
    convert_comma_separated_to_list,
    convert_list_to_comma_string,
)
from ..core.constants import (
    CONNECTOR_NAME,
    CONNECTOR_DEFAULT_LIMIT,
    DEFAULT_TIME_FRAME,
    DEFAULT_PADDING_TIME,
    TIME_FORMAT,
    FETCH_INTERVAL,
    STORED_IDS_LIMIT,
    MIN_TIME_ZONE,
    MAX_TIME_ZONE,
    WHITELISTED_ALARM_NAMES,
)
from ..core.McAfeeESMManager import McAfeeESMManager

connector_starting_time = unix_now()


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME
    processed_alerts = []

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    api_root = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True, print_value=True
    )
    username = extract_connector_param(
        siemplify, param_name="Username", is_mandatory=True, print_value=True
    )
    password = extract_connector_param(
        siemplify, param_name="Password", is_mandatory=True, remove_whitespaces=False
    )
    product_version = extract_connector_param(
        siemplify, param_name="Product Version", is_mandatory=True, print_value=True
    )
    use_aes_encryption = extract_connector_param(
        siemplify,
        param_name="Use AES Encryption",
        input_type=bool,
        print_value=True,
    )
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    environment_field_name = extract_connector_param(
        siemplify, param_name="Environment Field Name", print_value=True
    )
    environment_regex_pattern = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern", print_value=True
    )
    script_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )
    lowest_severity = extract_connector_param(
        siemplify,
        param_name="Lowest Severity To Fetch",
        input_type=int,
        print_value=True,
    )
    ingest_0_event_alarms = extract_connector_param(
        siemplify,
        param_name="Ingest 0 Source Event Alarms",
        input_type=bool,
        print_value=True,
    )
    padding_time = extract_connector_param(
        siemplify,
        param_name="Padding Time",
        input_type=int,
        default_value=DEFAULT_PADDING_TIME,
        print_value=True,
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
        param_name="Max Alarms To Fetch",
        input_type=int,
        default_value=CONNECTOR_DEFAULT_LIMIT,
        print_value=True,
    )
    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use dynamic list as a blacklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    rule_generator_field_name = extract_connector_param(
        siemplify, param_name="Rule Generator Field Name", print_value=True
    )
    device_product_field = extract_connector_param(
        siemplify, param_name="DeviceProductField", is_mandatory=True
    )
    secondary_device_product_field = extract_connector_param(
        siemplify, param_name="Secondary Device Product Field", print_value=True
    )
    disable_overflow = extract_connector_param(
        siemplify, param_name="Disable Overflow", input_type=bool, print_value=True
    )
    disable_overflow_alarm_names = extract_connector_param(
        siemplify, param_name="Disable Overflow For Alarm Names", print_value=True
    )

    disable_overflow_alarm_names = convert_comma_separated_to_list(
        disable_overflow_alarm_names
    )

    time_format = extract_connector_param(
        siemplify, param_name="Time Format", print_value=True
    )

    time_zone = extract_connector_param(
        siemplify, param_name="Time Zone", print_value=True, input_type=int
    )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        if hours_backwards < 1:
            siemplify.LOGGER.info(
                f"Max Hours Backwards must be greater than zero. "
                f"The default value {DEFAULT_TIME_FRAME} will be used."
            )
            hours_backwards = DEFAULT_TIME_FRAME

        if fetch_limit < 1:
            siemplify.LOGGER.info(
                f"Max Alarms To Fetch must be greater than zero. "
                f"The default value {CONNECTOR_DEFAULT_LIMIT} will be used."
            )
            fetch_limit = CONNECTOR_DEFAULT_LIMIT

        if padding_time < 1 or padding_time > 6:
            siemplify.LOGGER.info(
                f"Padding Time must be in range from 1 to 6. "
                f"The default value {DEFAULT_PADDING_TIME} will be used."
            )
            padding_time = DEFAULT_PADDING_TIME

        if lowest_severity and lowest_severity < 0 or lowest_severity > 100:
            raise Exception(
                f'Invalid value provided for "Lowest Severity To Fetch" parameter. '
                f"Possible values are in range from 0 to 100."
            )

        if time_zone and (time_zone < MIN_TIME_ZONE or time_zone > MAX_TIME_ZONE):
            siemplify.LOGGER.info(
                f"Time Zone must be in range from -11 to +14. "
                f"Connector will ignore the provided value."
            )
            time_zone = None

        # Read already existing alerts ids
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(
            f"Successfully loaded {len(existing_ids)} existing alerts from ids file"
        )

        manager = McAfeeESMManager(
            api_root=api_root,
            username=username,
            password=password,
            product_version=product_version,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
            siemplify_scope=siemplify,
            is_connector=True,
            use_aes_encryption=use_aes_encryption,
        )

        last_success_time = get_last_success_time(
            siemplify=siemplify, offset_with_metric={"hours": hours_backwards}
        )
        start_time = last_success_time
        if not ingest_0_event_alarms:
            if padding_time and last_success_time > utc_now() - timedelta(
                hours=padding_time
            ):
                start_time = utc_now() - timedelta(hours=padding_time)
                siemplify.LOGGER.info(
                    f"Last success time is greater than alarms padding period. "
                    f"Datetime: {start_time} will be used as start time."
                )

        fetched_alerts = []
        new_existing_ids = []
        alerts = manager.get_alarms(
            existing_ids=existing_ids,
            start_timestamp=start_time.strftime(TIME_FORMAT),
            end_timestamp=(
                last_success_time + timedelta(hours=FETCH_INTERVAL)
            ).strftime(TIME_FORMAT),
            limit=fetch_limit,
        )

        siemplify.LOGGER.info(f"Fetched {len(alerts)} alerts")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            alerts = alerts[:1]

        for alert in alerts:
            try:
                if is_approaching_timeout(connector_starting_time, script_timeout):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. " "Connector will gracefully exit"
                    )
                    break

                if (
                    len(processed_alerts) >= fetch_limit
                    or len(new_existing_ids) >= fetch_limit
                ):
                    # Provide slicing for the alerts amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle. "
                        "No more alerts will be processed in this cycle."
                    )
                    break

                siemplify.LOGGER.info(f"Started processing alert {alert.alarm_id}")

                if not pass_filters(
                    siemplify, whitelist_as_a_blacklist, alert, "name", lowest_severity
                ):
                    existing_ids.append(alert.alarm_id)
                    new_existing_ids.append(alert.alarm_id)
                    continue

                # Fetch details for alert's source events
                siemplify.LOGGER.info(
                    f"Fetching source events info for alert {alert.alarm_id}"
                )
                source_events = manager.get_alarm_details(alert.alarm_id)
                siemplify.LOGGER.info(
                    f"Found {len(source_events)} source events for alert {alert.alarm_id}"
                )
                source_event_ids = [event.get("eventId") for event in source_events]
                if source_events:
                    siemplify.LOGGER.info(
                        f"IDs of events found: {convert_list_to_comma_string(source_event_ids)}"
                    )

                event_ids_with_corr = []
                if source_event_ids:
                    # Check for correlated events
                    siemplify.LOGGER.info(f"Checking correlation info")
                    event_ids_with_corr = manager.check_correlated_events(
                        source_event_ids=source_event_ids
                    )
                    if event_ids_with_corr:
                        siemplify.LOGGER.info(
                            f"Found correlations for events: {convert_list_to_comma_string(event_ids_with_corr)}"
                        )
                    else:
                        siemplify.LOGGER.info(f"No correlations found")

                    for event_id in event_ids_with_corr:
                        siemplify.LOGGER.info(
                            f"Fetching correlated events for event with id: {event_id}"
                        )
                        additional_ids = manager.get_correlated_events(
                            source_event_id=event_id
                        )
                        source_event_ids.extend(additional_ids)
                        siemplify.LOGGER.info(
                            f"Fetched {len(additional_ids)} correlated events for event with id: {event_id}"
                        )

                # Filter event ids that have correlated events
                source_event_ids = [
                    eid for eid in source_event_ids if eid not in event_ids_with_corr
                ]

                # Update fetched alerts
                # This is needed to update the timestamp, irrelevant if alarm has events or not.
                fetched_alerts.append(alert)
                if (
                    not ingest_0_event_alarms
                    and not source_events
                    and alert.name not in WHITELISTED_ALARM_NAMES
                ):
                    siemplify.LOGGER.info(
                        f"Alert {alert.alarm_id} has 0 Source Events. " f"Skipping..."
                    )
                    continue

                for source_event_id in source_event_ids:
                    siemplify.LOGGER.info(
                        f"Fetching details for event with id: {source_event_id}"
                    )
                    try:
                        alert.source_events.append(
                            manager.get_event_details(
                                event_id=source_event_id,
                                time_format=time_format,
                                time_zone=time_zone,
                            )
                        )
                    except requests.Timeout:
                        siemplify.LOGGER.info(
                            f"Event with id {source_event_id} is corrupted."
                            " It will be skipped for this alert."
                        )
                        continue

                for corr_event_id in event_ids_with_corr:
                    siemplify.LOGGER.info(
                        f"Fetching details for event with id: {corr_event_id}"
                    )
                    alert.correlation_events.append(
                        manager.get_event_details(
                            event_id=corr_event_id,
                            time_format=time_format,
                            time_zone=time_zone,
                        )
                    )

                # Update existing alerts
                existing_ids.append(alert.alarm_id)
                new_existing_ids.append(alert.alarm_id)

                alert_info = alert.get_alert_info(
                    alert_info=AlertInfo(),
                    environment_common=GetEnvironmentCommonFactory().create_environment_manager(
                        siemplify, environment_field_name, environment_regex_pattern
                    ),
                    device_product_field=device_product_field,
                    secondary_device_product_field=secondary_device_product_field,
                    rule_generator_field_name=rule_generator_field_name,
                    time_format=time_format,
                    time_zone=time_zone,
                    logger=siemplify.LOGGER,
                )

                if should_check_overflow(
                    disable_overflow, alert.name, disable_overflow_alarm_names
                ):
                    if is_overflowed(siemplify, alert_info, is_test_run):
                        siemplify.LOGGER.info(
                            f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}"
                            f"-{alert_info.device_product} found as overflow alert. Skipping..."
                        )
                        # If is overflowed we should skip
                        continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alert.alarm_id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process alert {alert.alarm_id}")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(f"Finished processing alert {alert.alarm_id}")

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(siemplify, existing_ids, stored_ids_limit=STORED_IDS_LIMIT)

            if not fetched_alerts:
                siemplify.LOGGER.info(
                    "Timestamp is not updated since no alerts fetched"
                )
            else:
                fetched_alerts = sorted(
                    fetched_alerts, key=lambda alarm: alarm.alarm_date_ms
                )
                last_timestamp = fetched_alerts[-1].alarm_date_ms
                if last_timestamp < convert_datetime_to_unix_time(last_success_time):
                    siemplify.LOGGER.info(
                        "Timestamp is not updated since no new alerts were "
                        "processed after last success time"
                    )
                else:
                    siemplify.save_timestamp(new_timestamp=last_timestamp)
                    siemplify.LOGGER.info(f"Last timestamp is: {last_timestamp}")

        siemplify.LOGGER.info(
            f"Alerts processed: {len(processed_alerts)} out of "
            f"{len(fetched_alerts)}"
        )

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {e}")
        siemplify.LOGGER.exception(e)

        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def pass_filters(
    siemplify, whitelist_as_a_blacklist, alert, model_key, lowest_severity_to_fetch
):
    # All alert filters should be checked here
    if not pass_whitelist_filter(siemplify, whitelist_as_a_blacklist, alert, model_key):
        return False

    if not pass_severity_filter(siemplify, alert, lowest_severity_to_fetch):
        return False

    return True


def pass_severity_filter(siemplify, alarm, lowest_severity):
    # severity filter
    if lowest_severity and alarm.severity < lowest_severity:
        siemplify.LOGGER.info(
            f"Alert with severity: {alarm.severity} did not pass filter. "
            f"Lowest risk score to fetch is {lowest_severity}"
        )
        return False
    return True


def should_check_overflow(
    disable_overflow, alarm_name, disable_overflow_alarm_names
) -> bool:
    if disable_overflow:
        if disable_overflow_alarm_names:
            if alarm_name in disable_overflow_alarm_names:
                return False
            return True
        else:
            return False
    else:
        return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
