from __future__ import annotations
import sys
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from ..core.FireEyeHXManager import FireEyeHXManager
from TIPCommon import (
    extract_connector_param,
    get_last_success_time,
    is_overflowed,
    save_timestamp,
    is_approaching_timeout,
)
from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

# =====================================
#             CONSTANTS               #
# =====================================
CONNECTOR_NAME = "FireEye HX Alerts Connector"
WHITELIST_FILTER = "whitelist"
BLACKLIST_FILTER = "blacklist"
connector_starting_time = unix_now()
TIMEOUT_THRESHOLD = 0.9


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
        siemplify, param_name="API Root", is_mandatory=True
    )
    username = extract_connector_param(
        siemplify, param_name="Username", is_mandatory=True
    )
    password = extract_connector_param(
        siemplify, param_name="Password", is_mandatory=True
    )
    verify_ssl = extract_connector_param(
        siemplify, param_name="Verify SSL", default_value=True, input_type=bool
    )

    environment_field_name = extract_connector_param(
        siemplify, param_name="Environment Field Name", default_value=""
    )
    environment_regex_pattern = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern", default_value=""
    )

    fetch_limit = extract_connector_param(
        siemplify, param_name="Max Alerts Per Cycle", input_type=int
    )
    hours_backwards = extract_connector_param(
        siemplify, param_name="Offset time in hours", input_type=int
    )
    alert_type = extract_connector_param(siemplify, param_name="Alert Type")

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
    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        siemplify.LOGGER.info("Fetching alerts...")
        manager = FireEyeHXManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        fetched_alerts = []
        filtered_alerts = manager.get_alerts_for_connector(
            start_time=get_last_success_time(
                siemplify=siemplify, offset_with_metric={"hours": hours_backwards}
            ).strftime("%Y-%m-%dT%H:%M:%S.%f"),
            limit=fetch_limit,
            alert_type=alert_type,
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
                        "Reached max number of alerts cycle. No more alerts will be processed in this cycle."
                    )
                    break

                siemplify.LOGGER.info(
                    f"Started processing Alert {alert._id}", alert_id=alert._id
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
                        f"Alert {alert._id} did not pass filters skipping...."
                    )
                    continue

                # attach additional host info
                alert.attach_host_info(
                    manager.get_host_information(siemplify, alert.host_id)
                )

                alert_info = alert.get_alert_info(
                    AlertInfo(),
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify, environment_field_name, environment_regex_pattern
                    ),
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{str(alert_info.rule_generator)}-{str(alert_info.ticket_id)}-{str(alert_info.environment)}-{str(alert_info.device_product)} found as overflow alert. Skipping."
                    )
                    # If is overflowed we should skip
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alert._id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed to process alert {alert._id}", alert_id=alert._id
                )
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(
                f"Finished processing Alert {alert._id}", alert_id=alert._id
            )

        if not is_test_run:
            save_timestamp(siemplify=siemplify, alerts=fetched_alerts)

        manager.close_connection()
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
        if whitelist_filter_type == BLACKLIST_FILTER and alert.type in whitelist:
            siemplify.LOGGER.info(
                f"Alert with type: {alert.type} did not pass blacklist filter."
            )
            return False

        if whitelist_filter_type == WHITELIST_FILTER and alert.type not in whitelist:
            siemplify.LOGGER.info(
                f"Alert with type: {alert.type} did not pass whitelist filter."
            )
            return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
