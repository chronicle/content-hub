from __future__ import annotations
import sys
import arrow
import uuid

from datetime import timedelta

from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_unixtime_to_datetime
from TIPCommon import (
    extract_connector_param,
    dict_to_flat,
    read_ids,
    write_ids,
    is_overflowed,
    is_approaching_timeout,
    filter_old_alerts,
    utc_now,
    validate_timestamp,
)
from ..core.FireEyeETPManager import FireEyeETPManager

from ..core.FireEyeETPConstants import (
    ALERT_ID_FIELD,
    ALERTS_CONNECTOR_NAME,
    DEFAULT_TIME_FRAME,
    ALERT_NAME,
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    PRINT_TIME_FORMAT,
    ACCEPTABLE_TIME_INTERVAL_IN_MINUTES,
    WHITELIST_FILTER,
    BLACKLIST_FILTER,
)


def filter_recent_alerts(
    siemplify, alert_groups, max_minutes_backwards=ACCEPTABLE_TIME_INTERVAL_IN_MINUTES
):
    filtered_groups = []

    for group in alert_groups:
        if (
            group[0].occurred_time_unix
            < arrow.utcnow().shift(minutes=-max_minutes_backwards).timestamp * 1000
        ):
            filtered_groups.append(group)

        else:
            siemplify.LOGGER.info(
                "Alert group with email ID {} did not pass time filter. Earliest Alert in the group occurred in the "
                "last {} minutes.".format(
                    group[0].etp_message_id, max_minutes_backwards
                )
            )

    return filtered_groups


def pass_whitelist_filter(siemplify, alert_group, whitelist, whitelist_filter_type):
    # whitelist filter
    if whitelist:
        if (
            whitelist_filter_type == BLACKLIST_FILTER
            and alert_group[0].name in whitelist
        ):
            siemplify.LOGGER.info(
                f"Alert group with name: {alert_group[0].name} did not pass blacklist filter."
            )
            return False

        if (
            whitelist_filter_type == WHITELIST_FILTER
            and alert_group[0].name not in whitelist
        ):
            siemplify.LOGGER.info(
                f"Alert group with name: {alert_group[0].name} did not pass whitelist filter."
            )
            return False

    return True


def group_alerts(fetched_alerts):
    alert_groups = set(map(lambda alert: alert.etp_message_id, fetched_alerts))
    grouped_alerts = [
        [alert for alert in fetched_alerts if alert.etp_message_id == group]
        for group in alert_groups
    ]
    # Sort groups by the occurred time of the earliest alert in each group
    return sorted(
        grouped_alerts,
        key=lambda alert_group: sorted(
            alert_group, key=lambda alert: alert.occurred_time_unix
        )[0].occurred_time_unix,
    )


def calculate_priority(alerts_group):
    return max([alert.priority for alert in alerts_group])


def create_alert_info(environment, alerts_group):
    sorted_alerts_group = sorted(
        alerts_group, key=lambda alert: alert.occurred_time_unix
    )

    alert_info = AlertInfo()
    alert_info.display_id = str(uuid.uuid4())
    alert_info.ticket_id = sorted_alerts_group[0].id
    alert_info.name = ALERT_NAME
    alert_info.rule_generator = sorted_alerts_group[0].name
    alert_info.priority = calculate_priority(alerts_group)
    alert_info.start_time = sorted_alerts_group[0].occurred_time_unix
    alert_info.end_time = sorted_alerts_group[-1].occurred_time_unix

    alert_info.device_vendor = DEVICE_VENDOR
    alert_info.device_product = DEVICE_PRODUCT

    events = []
    for alert in sorted_alerts_group:
        for event in alert.events:
            events.append(event)

    for rec_event in sorted_alerts_group[0].recipient_events:
        events.append(rec_event)

    alert_info.events = [dict_to_flat(event) for event in events]
    alert_info.environment = environment.get_environment(
        sorted_alerts_group[0].raw_data
    )

    return alert_info


@output_handler
def main(is_test_run):
    connector_starting_time = unix_now()
    alerts = []
    processed_alerts = []
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = ALERTS_CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button" "Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("==================== Main - Param Init ====================")

    api_root = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True, print_value=True
    )
    api_key = extract_connector_param(
        siemplify, param_name="API Key", is_mandatory=True
    )
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
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
    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Fetch Max Hours Backwards",
        input_type=int,
        default_value=DEFAULT_TIME_FRAME,
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

    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )
    server_timezone = extract_connector_param(
        siemplify, param_name="Timezone", default_value="0", print_value=True
    )

    siemplify.LOGGER.info("------------------- Main - Started -------------------")

    try:
        if is_test_run:
            siemplify.LOGGER.info("This is a test run. Ignoring stored timestamps")
            last_success_time_datetime = validate_timestamp(
                utc_now() - timedelta(hours=hours_backwards), hours_backwards
            )
        else:
            last_success_time_datetime = validate_timestamp(
                siemplify.fetch_timestamp(datetime_format=True), hours_backwards
            )

        siemplify.LOGGER.info(
            f"Last success time: {last_success_time_datetime.strftime(PRINT_TIME_FORMAT)}"
        )

        # Read already existing alerts ids
        siemplify.LOGGER.info("Reading already existing alerts ids...")
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(f"Found {len(existing_ids)} existing ids in ids.json")

        etp_manager = FireEyeETPManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        siemplify.LOGGER.info("Fetching alerts...")

        fetched_alerts = etp_manager.get_alerts(
            start_time=last_success_time_datetime, timezone_offset=server_timezone
        )

        siemplify.LOGGER.info(f"Fetched {len(fetched_alerts)} alerts")

        siemplify.LOGGER.info("Filtering already processed alerts")
        filtered_alerts = filter_old_alerts(
            siemplify=siemplify,
            alerts=fetched_alerts,
            existing_ids=existing_ids,
            id_key=ALERT_ID_FIELD,
        )
        siemplify.LOGGER.info(f"Found {len(filtered_alerts)} new alerts")

        siemplify.LOGGER.info("Grouping alerts.")
        grouped_alerts = group_alerts(filtered_alerts)

        siemplify.LOGGER.info(
            f"Grouped into {len(grouped_alerts)} alert group based on email id"
        )

        siemplify.LOGGER.info("Filtering too recent alerts")
        filtered_recent_alerts = filter_recent_alerts(
            siemplify, grouped_alerts, ACCEPTABLE_TIME_INTERVAL_IN_MINUTES
        )
        siemplify.LOGGER.info(f"Filtered to {len(filtered_recent_alerts)} alert groups")

        if is_test_run:
            siemplify.LOGGER.info(
                "This is a TEST run. Only 1 alert group will be processed."
            )
            filtered_recent_alerts = filtered_recent_alerts[:1]

        for alert_group in filtered_recent_alerts:
            try:
                if is_approaching_timeout(
                    connector_starting_time, python_process_timeout
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit."
                    )
                    break

                siemplify.LOGGER.info(
                    f"Processing alert group {alert_group[0].etp_message_id}"
                )
                siemplify.LOGGER.info(
                    f"There are {len(alert_group)} alerts in this group"
                )

                existing_ids.extend([alert.id for alert in alert_group])

                if not pass_whitelist_filter(
                    siemplify, alert_group, whitelist, whitelist_filter_type
                ):
                    siemplify.LOGGER.info(
                        f"Alert group {alert_group[0].name} did not pass filters skipping...."
                    )
                    continue

                processed_alerts.extend(alert_group)
                detailed_alert_group = []
                siemplify.LOGGER.info(
                    f"Fetching alert details for alert group {alert_group[0].etp_message_id}"
                )
                for alert in alert_group:
                    detailed_alert = etp_manager.get_alert_details(
                        alert_id=alert.id, timezone_offset=server_timezone
                    )
                    detailed_alert_group.append(detailed_alert)

                siemplify.LOGGER.info(
                    f"Creating AlertInfo for alert group {alert_group[0].etp_message_id}"
                )
                environment_common = (
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify,
                        environment_field_name=environment_field_name,
                        environment_regex_pattern=environment_regex_pattern,
                    )
                )
                alert_info = create_alert_info(environment_common, detailed_alert_group)

                siemplify.LOGGER.info(
                    f"Finished creating AlertInfo for alert group {alert_group[0].etp_message_id}"
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert.name}-{alert_info.ticket_id}-{alert_info.environment}-{alert_info.device_product} found as overflow alert. Skipping."
                    )
                    # If is overflowed we should skip
                    continue

                alerts.append(alert_info)
                siemplify.LOGGER.info(
                    f"Finished processing. Alert group {alert_group[0]. etp_message_id} was created."
                )

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed to process alert group {alert_group[0].etp_message_id}"
                )
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

        if not is_test_run:
            if filtered_alerts:
                if processed_alerts:
                    new_timestamp = sorted(
                        processed_alerts, key=lambda alert: alert.occurred_time_unix
                    )[0].occurred_time_unix
                    siemplify.save_timestamp(new_timestamp=new_timestamp)
                    siemplify.LOGGER.info(
                        f"New timestamp {convert_unixtime_to_datetime(new_timestamp).strftime(PRINT_TIME_FORMAT)} has been saved"
                    )

            else:
                if fetched_alerts:
                    new_timestamp = sorted(
                        fetched_alerts, key=lambda alert: alert.occurred_time_unix
                    )[-1].occurred_time_unix
                    siemplify.save_timestamp(new_timestamp=new_timestamp)
                    siemplify.LOGGER.info(
                        f"New timestamp {convert_unixtime_to_datetime(new_timestamp) .strftime(PRINT_TIME_FORMAT)} has been saved"
                    )
                else:
                    siemplify.LOGGER.info(
                        "No alerts were fetched. Timestamp won't be updated."
                    )

            write_ids(siemplify, existing_ids)

    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {err}")
        siemplify.LOGGER.exception(err)
        if is_test_run:
            raise err

    siemplify.LOGGER.info(f"Created total of {len(alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(alerts)


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
