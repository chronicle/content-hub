from __future__ import annotations
import sys

from EnvironmentCommon import GetEnvironmentCommonFactory
from ..core.Office365ManagementAPIManager import Office365ManagementAPIManager
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import (
    extract_connector_param,
    read_ids,
    write_ids,
    get_last_success_time,
    is_approaching_timeout,
    is_overflowed,
    save_timestamp,
    pass_whitelist_filter,
)
from ..core.UtilsManager import get_milliseconds_from_minutes
from ..core.constants import (
    CONNECTOR_NAME,
    DEFAULT_TIME_FRAME,
    UNIX_FORMAT,
    PARAMETERS_DEFAULT_DELIMITER,
    ALERT_TYPES,
)

connector_starting_time = unix_now()


@output_handler
def main(is_test_run):
    processed_alerts = []
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    api_root = extract_connector_param(
        siemplify, param_name="Api Root", is_mandatory=True, print_value=True
    )
    azure_active_directory_id = extract_connector_param(
        siemplify,
        param_name="Azure Active Directory ID",
        is_mandatory=True,
        print_value=True,
    )
    client_id = extract_connector_param(
        siemplify, param_name="Client ID", is_mandatory=True, print_value=True
    )
    client_secret = extract_connector_param(siemplify, param_name="Client Secret")
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    certificate_path = extract_connector_param(
        siemplify, param_name="Certificate Path", print_value=True
    )
    certificate_password = extract_connector_param(
        siemplify, param_name="Certificate Password"
    )
    oauth2_login_endpoint_url = extract_connector_param(
        siemplify,
        param_name="OAUTH2 Login Endpoint Url",
        is_mandatory=True,
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

    fetch_limit = extract_connector_param(
        siemplify, param_name="Max events to fetch", input_type=int, print_value=True
    )
    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Fetch Max Hours Backwards",
        input_type=int,
        default_value=DEFAULT_TIME_FRAME,
        print_value=True,
    )
    time_interval = extract_connector_param(
        siemplify,
        param_name="Fetch Backwards Time Interval (minutes)",
        input_type=int,
        default_value=DEFAULT_TIME_FRAME,
        print_value=True,
    )
    events_padding_period = extract_connector_param(
        siemplify,
        param_name="Events Padding Period (minutes)",
        input_type=int,
        default_value=DEFAULT_TIME_FRAME,
        print_value=True,
    )

    operation_filter = extract_connector_param(
        siemplify, param_name="Type of Operation Filter", print_value=True
    )
    status_filter = extract_connector_param(
        siemplify, param_name="Status Filter", print_value=True
    )
    use_filters_as_whitelist = extract_connector_param(
        siemplify,
        param_name="Use operation and status filters as whitelist",
        input_type=bool,
        print_value=True,
    )
    entity_events_keys = extract_connector_param(
        siemplify,
        param_name="Entity Keys to Create Additional Events",
        print_value=True,
    )

    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use whitelist as a blacklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    event_field_name = extract_connector_param(
        siemplify, "EventClassId", is_mandatory=True
    )

    operation_filter_list = (
        [item.strip() for item in operation_filter.split(PARAMETERS_DEFAULT_DELIMITER)]
        if operation_filter
        else []
    )

    status_filter_list = (
        [item.strip() for item in status_filter.split(PARAMETERS_DEFAULT_DELIMITER)]
        if status_filter
        else []
    )

    entity_events_keys_list = (
        [
            item.strip()
            for item in entity_events_keys.split(PARAMETERS_DEFAULT_DELIMITER)
        ]
        if entity_events_keys
        else []
    )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        # Read already existing alerts ids
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(f"Successfully loaded {len(existing_ids)} existing ids")

        manager = Office365ManagementAPIManager(
            api_root,
            azure_active_directory_id,
            client_id=client_id,
            client_secret=client_secret,
            oauth2_login_endpoint_url=oauth2_login_endpoint_url,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
            certificate_path=certificate_path,
            certificate_password=certificate_password,
        )

        fetched_alerts = []
        last_success_time = get_last_success_time(
            siemplify=siemplify,
            offset_with_metric={"hours": hours_backwards},
            time_format=UNIX_FORMAT,
        )

        filtered_alerts = manager.get_alerts(
            existing_ids=existing_ids,
            limit=fetch_limit,
            start_timestamp=last_success_time,
            time_interval=time_interval,
            events_padding_period=events_padding_period,
            alert_type=ALERT_TYPES["audit_general"],
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} alerts")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                if is_approaching_timeout(connector_starting_time, script_timeout):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                if len(processed_alerts) >= fetch_limit:
                    # Provide slicing for the alerts amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle. No more alerts will be processed in this cycle."
                    )
                    break

                if not pass_filters(
                    siemplify,
                    whitelist_as_a_blacklist,
                    use_filters_as_whitelist,
                    alert,
                    "workload",
                    "operation",
                    "status",
                    operation_filter_list,
                    status_filter_list,
                ):
                    # Update existing alerts
                    existing_ids.append(alert.id)
                    fetched_alerts.append(alert)
                    continue

                alert.set_events(entity_events_keys_list, event_field_name)

                # Update existing alerts
                existing_ids.append(alert.id)
                fetched_alerts.append(alert)

                alert_info = alert.get_alert_info(
                    AlertInfo(),
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify, environment_field_name, environment_regex_pattern
                    ),
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}"
                        f"-{alert_info.device_product} found as overflow alert. Skipping..."
                    )
                    # If is overflowed we should skip
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alert.id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process alert {alert.id}")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(f"Finished processing alert {alert.id}")

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(siemplify, existing_ids)

            if not fetched_alerts:
                last_timestamp = min(
                    unix_now(),
                    last_success_time + get_milliseconds_from_minutes(time_interval),
                )
                siemplify.LOGGER.info(f"Last timestamp is: {last_timestamp}")
                siemplify.save_timestamp(new_timestamp=last_timestamp)
            else:
                save_timestamp(
                    siemplify=siemplify,
                    alerts=fetched_alerts,
                    timestamp_key="creation_time",
                )

        siemplify.LOGGER.info(
            f"Alerts processed: {len(processed_alerts)} out of {len(fetched_alerts)}"
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
    siemplify,
    whitelist_as_a_blacklist,
    filters_as_whitelist,
    alert,
    model_key,
    operation_key,
    status_key,
    operation_filter_list,
    status_filter_list,
):
    # All alert filters should be checked here
    if not pass_whitelist_filter(siemplify, whitelist_as_a_blacklist, alert, model_key):
        return False

    if not pass_whitelist_filter(
        siemplify, not filters_as_whitelist, alert, operation_key, operation_filter_list
    ):
        return False

    if not pass_whitelist_filter(
        siemplify, not filters_as_whitelist, alert, status_key, status_filter_list
    ):
        return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
