from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from TIPCommon import (
    extract_connector_param,
    read_ids,
    write_ids,
    get_last_success_time,
    is_approaching_timeout,
    is_overflowed,
    save_timestamp,
    pass_whitelist_filter,
    UNIX_FORMAT,
)
from EnvironmentCommon import GetEnvironmentCommonFactory
from ..core.constants import CONNECTOR_NAME, DEFAULT_TIME_FRAME, SEVERITY_MAP
from ..core.RecordedFutureManager import RecordedFutureManager
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
import sys


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

    api_url = extract_connector_param(
        siemplify, param_name="API URL", is_mandatory=True
    )
    api_key = extract_connector_param(
        siemplify, param_name="API Key", is_mandatory=True
    )
    verify_ssl = extract_connector_param(
        siemplify, param_name="Verify SSL", is_mandatory=True, input_type=bool
    )

    environment_field_name = extract_connector_param(
        siemplify, param_name="Environment Field Name"
    )
    environment_regex_pattern = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern"
    )

    script_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )
    fetch_limit = extract_connector_param(
        siemplify, param_name="Max Alerts To Fetch", input_type=int
    )
    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Fetch Max Hours Backwards",
        input_type=int,
        default_value=DEFAULT_TIME_FRAME,
    )

    severity = extract_connector_param(
        siemplify, param_name="Severity", is_mandatory=True
    )
    get_alerts_details = extract_connector_param(
        siemplify, param_name="Get Alert's Details", is_mandatory=True, input_type=bool
    )

    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use whitelist as a blacklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    whitelist = siemplify.whitelist

    if not SEVERITY_MAP.get(severity):
        siemplify.LOGGER.info(
            'Provided severity is invalid. Default value "Medium" will be used'
        )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        # Read already existing alerts ids
        siemplify.LOGGER.info("Reading already existing alerts ids...")
        existing_ids = read_ids(siemplify)

        siemplify.LOGGER.info("Fetching alerts...")
        manager = RecordedFutureManager(
            api_url, api_key, verify_ssl=verify_ssl, siemplify=siemplify
        )
        fetched_alerts = []

        filtered_alerts = manager.get_alerts(
            existing_ids=existing_ids,
            limit=fetch_limit,
            start_timestamp=get_last_success_time(
                siemplify=siemplify,
                offset_with_metric={"hours": hours_backwards},
                time_format=UNIX_FORMAT,
            ),
            severity=severity,
            get_alerts_details=get_alerts_details,
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
                    f"Started processing alert {alert.id} - {alert.rule_name}",
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
                    siemplify=siemplify,
                    whitelist_as_a_blacklist=whitelist_as_a_blacklist,
                    model=alert,
                    model_key="rule_name",
                    whitelist=whitelist,
                ):
                    siemplify.LOGGER.info(
                        f"Alert {alert.id} did not pass filters skipping..."
                    )
                    continue

                common_env = GetEnvironmentCommonFactory.create_environment_manager(
                    siemplify=siemplify,
                    environment_field_name=environment_field_name,
                    environment_regex_pattern=environment_regex_pattern,
                )
                alert_info = alert.get_alert_info(
                    AlertInfo(), environment_common=common_env
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
            save_timestamp(
                siemplify=siemplify, alerts=fetched_alerts, timestamp_key="triggered"
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


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
