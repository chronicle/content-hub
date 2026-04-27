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
)
from ..core.UtilsManager import get_milliseconds_from_minutes
from ..core.constants import (
    CONNECTOR_NAME,
    WHITELIST_FILTER,
    BLACKLIST_FILTER,
    DEFAULT_TIME_FRAME,
    UNIX_FORMAT,
    PARAMETERS_DEFAULT_DELIMITER,
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
    client_secret = extract_connector_param(
        siemplify, param_name="Client Secret", is_mandatory=False
    )
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    certificate_path = extract_connector_param(
        siemplify, param_name="Certificate Path", is_mandatory=False, input_type=str
    )
    certificate_password = extract_connector_param(
        siemplify, param_name="Certificate Password", is_mandatory=False, input_type=str
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
    policy_filter = extract_connector_param(
        siemplify, param_name="Type of Policy Filter", print_value=True
    )
    mask_findings = extract_connector_param(
        siemplify, param_name="Mask findings?", input_type=bool, print_value=True
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

    operation_filter_list = (
        [item.strip() for item in operation_filter.split(PARAMETERS_DEFAULT_DELIMITER)]
        if operation_filter
        else []
    )

    policy_filter_list = (
        [item.strip() for item in policy_filter.split(PARAMETERS_DEFAULT_DELIMITER)]
        if policy_filter
        else []
    )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        # Read already existing alerts ids
        siemplify.LOGGER.info("Reading already existing alerts ids...")
        existing_ids = read_ids(siemplify)

        siemplify.LOGGER.info("Fetching alerts...")
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
            mask_findings=mask_findings,
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} alerts")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                if len(processed_alerts) >= fetch_limit:
                    # Provide slicing for the alerts amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle. No more alerts will be processed in this cycle."
                    )
                    break

                siemplify.LOGGER.info(
                    f"Started processing alert {alert.id} - {alert.workload}",
                    alert_id=alert.id,
                )

                if is_approaching_timeout(connector_starting_time, script_timeout):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                # Update existing alerts
                existing_ids.append(alert.id)
                fetched_alerts.append(alert)

                if not pass_whitelist_filter(
                    siemplify, alert, whitelist, whitelist_filter_type
                ):
                    siemplify.LOGGER.info(
                        f"Alert {alert.id} did not pass filters skipping..."
                    )
                    continue

                if not pass_operation_filter(alert, operation_filter_list):
                    siemplify.LOGGER.info(
                        f"Alert {alert.id} did not pass operation filter skipping..."
                    )
                    continue

                if not pass_policy_filter(alert, policy_filter_list):
                    siemplify.LOGGER.info(
                        f"Alert {alert.id} did not pass policy filter skipping..."
                    )
                    continue

                alert_info = alert.get_alert_info(
                    AlertInfo(),
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify, environment_field_name, environment_regex_pattern
                    ),
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
                f"Finished processing alert {alert.id}", alert_id=alert.id
            )

        if not is_test_run:
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

            write_ids(siemplify, existing_ids)

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {e}")
        siemplify.LOGGER.exception(e)

        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def pass_whitelist_filter(siemplify, alert, whitelist, whitelist_filter_type):
    # whitelist filter
    if whitelist:
        if whitelist_filter_type == BLACKLIST_FILTER and alert.workload in whitelist:
            siemplify.LOGGER.info(
                f"Alert with rule name: {alert.workload} did not pass blacklist filter."
            )
            return False

        if (
            whitelist_filter_type == WHITELIST_FILTER
            and alert.workload not in whitelist
        ):
            siemplify.LOGGER.info(
                f"Alert with rule name: {alert.workload} did not pass whitelist filter."
            )
            return False

    return True


def pass_operation_filter(alert, operations_list):
    if alert.operation in operations_list:
        return False

    return True


def pass_policy_filter(alert, policies_list):
    filtered_policy_names = [
        policy_name
        for policy_name in alert.policy_names
        if policy_name in policies_list
    ]

    if filtered_policy_names:
        return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
