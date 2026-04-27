from __future__ import annotations
import sys
import copy

from TIPCommon import extract_connector_param, dict_to_flat
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler, unix_now

from ..core.utils import (
    read_ids,
    validate_timestamp,
    is_approaching_timeout,
    get_environment_common,
    is_overflowed,
    write_ids,
    format_time_to_request,
    get_device_activities,
)
from ..core.ArmisManager import ArmisManager
from ..core.consts import (
    CONNECTOR_DISPLAY_NAME,
    DEFAULT_TIMEOUT_IN_SECONDS,
    DEFAULT_LOWEST_SEVERITY_TO_FETCH,
    DEFAULT_HOURS_BACKWARDS,
    DEFAULT_MAX_ALERTS_TO_FETCH,
    SEVERITIES_FILTER_MAPPING,
    INTEGRATION_NAME,
    WHITELIST_FILTER,
    BLACKLIST_FILTER,
    DEFAULT_LENGTH_TO_FETCH,
    MAX_SIEMPLIFY_EVENTS,
    TIMEOUT_THRESHOLD,
    DEFAULT_HOURS_BACKWARDS_FROM_EXISTING_IDS,
)


@output_handler
def main(is_test_run):
    connector_starting_time = unix_now()

    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = CONNECTOR_DISPLAY_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    api_root = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True
    )

    api_secret = extract_connector_param(
        siemplify,
        param_name="API Secret",
        print_value=False,
        is_mandatory=True,
        remove_whitespaces=False,
    )

    environment_field_name = extract_connector_param(
        siemplify,
        param_name="Environment Field Name",
        is_mandatory=False,
        default_value="",
        print_value=True,
    )

    environment_regex_pattern = extract_connector_param(
        siemplify,
        param_name="Environment Regex Pattern",
        default_value=".*",
        is_mandatory=False,
        print_value=True,
    )

    lowest_severity_to_fetch = extract_connector_param(
        siemplify,
        param_name="Lowest Severity To Fetch",
        default_value=DEFAULT_LOWEST_SEVERITY_TO_FETCH,
        is_mandatory=False,
        print_value=True,
    )

    use_whitelist_as_blacklist = extract_connector_param(
        siemplify,
        param_name="Use whitelist as a blacklist",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    whitelist = siemplify.whitelist

    whitelist_filter_type = (
        BLACKLIST_FILTER if use_whitelist_as_blacklist else WHITELIST_FILTER
    )

    if lowest_severity_to_fetch.upper() not in SEVERITIES_FILTER_MAPPING:
        raise Exception(
            f"Alert severity {lowest_severity_to_fetch} is invalid. "
            "Valid values are: Low, Medium, High"
        )
    processed_alerts = []
    try:
        max_hours_backwards = extract_connector_param(
            siemplify,
            param_name="Max Hours Backwards",
            default_value=DEFAULT_HOURS_BACKWARDS,
            input_type=int,
            is_mandatory=False,
            print_value=True,
        )

        script_timeout = extract_connector_param(
            siemplify,
            param_name="PythonProcessTimeout",
            input_type=int,
            is_mandatory=True,
            default_value=DEFAULT_TIMEOUT_IN_SECONDS,
            print_value=True,
        )

        max_alerts_to_fetch = extract_connector_param(
            siemplify,
            param_name="Max Alerts To Fetch",
            input_type=int,
            default_value=DEFAULT_MAX_ALERTS_TO_FETCH,
            is_mandatory=False,
            print_value=True,
        )

        siemplify.LOGGER.info("------------------- Main - Started -------------------")
        siemplify.LOGGER.info(f"Connecting to {INTEGRATION_NAME} Service")
        manager = ArmisManager(
            api_root=api_root, api_secret=api_secret, verify_ssl=verify_ssl
        )
        siemplify.LOGGER.info(f"Successfully connected to {INTEGRATION_NAME} Service")

        # Read already existing alert ids from ids.json file
        siemplify.LOGGER.info("Loading existing ids from IDS file.")
        existing_ids = read_ids(
            siemplify, max_hours_backwards=DEFAULT_HOURS_BACKWARDS_FROM_EXISTING_IDS
        )
        siemplify.LOGGER.info(f"Found {len(existing_ids)} existing ids in ids.json")

        last_success_time_datetime = validate_timestamp(
            siemplify.fetch_timestamp(datetime_format=True), max_hours_backwards
        )

        fetched_alerts = []
        siemplify.LOGGER.info(f"Fetching alerts from {INTEGRATION_NAME} service")

        filtered_alerts = manager.get_alerts(
            existing_ids=existing_ids,
            after_date=format_time_to_request(last_success_time_datetime),
            severity=SEVERITIES_FILTER_MAPPING.get(
                lowest_severity_to_fetch.upper(), ""
            ),
            max_alerts_to_fetch=max(DEFAULT_LENGTH_TO_FETCH, max_alerts_to_fetch),
        )
        siemplify.LOGGER.info(
            f"Successfully fetched {len(filtered_alerts)} alerts "
            f"from {INTEGRATION_NAME} service"
        )

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                if len(processed_alerts) >= max_alerts_to_fetch:
                    # Provide slicing for the alarms amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle of value "
                        f"{max_alerts_to_fetch}. "
                        "No more alerts will be processed in this cycle."
                    )
                    break

                if is_approaching_timeout(
                    script_timeout, connector_starting_time, TIMEOUT_THRESHOLD
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                # Update existing alerts
                existing_ids.update({alert.alert_id: unix_now()})
                fetched_alerts.append(alert)

                if not pass_whitelist_filter(
                    siemplify, alert, whitelist, whitelist_filter_type
                ):
                    siemplify.LOGGER.info(
                        f"Alert {alert.alert_id} did not pass filters skipping...."
                    )
                    continue

                environment = get_environment_common(
                    siemplify, environment_field_name, environment_regex_pattern
                )
                alert_info = alert.to_alert_info(environment, alert_events=[])

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}"
                        f"-{alert_info.environment}-{alert_info.device_product} "
                        "found as overflow alert. Skipping."
                    )
                    # If is overflowed we should skip
                    continue

                # check here overflow

                siemplify.LOGGER.info(
                    f"Fetching alert devices from {INTEGRATION_NAME} service"
                )
                alert_devices_list = manager.get_alert_devices(alert_id=alert.alert_id)
                alert_devices_ids = alert.device_ids

                if len(alert_devices_ids) > MAX_SIEMPLIFY_EVENTS:
                    siemplify.LOGGER.info(
                        f"Siemplify can fetch Max of {MAX_SIEMPLIFY_EVENTS} "
                        f"for each alert, The first {MAX_SIEMPLIFY_EVENTS} will be handled"
                    )

                alert_devices_ids = set(alert.device_ids[:MAX_SIEMPLIFY_EVENTS])
                alert_devices_dict = {
                    device.id: device for device in alert_devices_list
                }
                siemplify.LOGGER.info(
                    f"Successfully fetched alerts devices from {INTEGRATION_NAME} "
                    "service"
                )

                siemplify.LOGGER.info(
                    f"Fetching alerts activities from {INTEGRATION_NAME} service"
                )
                alert_activities_list = manager.get_alert_activities(
                    alert_id=alert.alert_id
                )
                device_activities_dict = get_device_activities(
                    alert_activities_list=alert_activities_list,
                    alert_devices_ids=alert_devices_ids,
                )
                siemplify.LOGGER.info(
                    f"Successfully fetched alerts activities from {INTEGRATION_NAME}"
                    " service"
                )

                siemplify.LOGGER.info(
                    f"Starting to process alert with id: {alert.alert_id}"
                )
                events = []
                index = 0
                while len(events) < MAX_SIEMPLIFY_EVENTS:
                    new_events = [
                        device_activities_dict.get(device_id)[index].as_event(
                            alert_type=alert.type,
                            device=alert_devices_dict.get(device_id),
                        )
                        for device_id in alert_devices_ids
                        if len(device_activities_dict.get(device_id)) >= index + 1
                    ]

                    if not new_events:
                        break

                    events.extend(new_events)
                    index += 1

                if not events:
                    for device in alert_devices_list:
                        event_data = copy.deepcopy(alert.raw_data)
                        event_data["alert_type"] = "Alert"
                        event_data["deviceIds"] = device.as_event()
                        events.append(dict_to_flat(event_data))

                alert_info.events = events[:MAX_SIEMPLIFY_EVENTS]
                if events:
                    environment.get_environment(
                        dict_to_flat({**alert.raw_data, **events[0]})
                    )
                else:
                    alert_info.environment = environment.get_environment(
                        dict_to_flat(alert.raw_data)
                    )

                processed_alerts.append(alert_info)

            except Exception as error:
                siemplify.LOGGER.error(
                    f"Failed to process alert {alert.alert_id}", alert_id=alert.alert_id
                )
                siemplify.LOGGER.exception(error)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(
                f"Finished processing Alert {alert.alert_id}", alert_id=alert.alert_id
            )

        if not is_test_run:
            if fetched_alerts:
                new_timestamp = fetched_alerts[-1].time
                siemplify.save_timestamp(new_timestamp=new_timestamp)
                siemplify.LOGGER.info(f"New timestamp {new_timestamp} has been saved")

            write_ids(siemplify, existing_ids)

    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {err}")
        siemplify.LOGGER.exception(err)
        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def pass_whitelist_filter(siemplify, alert, whitelist, whitelist_filter_type):
    # whitelist filter
    if whitelist:
        if whitelist_filter_type == BLACKLIST_FILTER and alert.title in whitelist:
            siemplify.LOGGER.info(
                f"Threat with name: {alert.title} did not pass blacklist filter."
            )
            return False

        if whitelist_filter_type == WHITELIST_FILTER and alert.title not in whitelist:
            siemplify.LOGGER.info(
                f"Threat with name: {alert.title} did not pass whitelist filter."
            )
            return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
