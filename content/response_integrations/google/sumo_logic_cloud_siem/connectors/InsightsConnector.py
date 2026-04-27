from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from TIPCommon import (
    extract_connector_param,
    read_ids,
    write_ids,
    filter_old_alerts,
    get_last_success_time,
    DATETIME_FORMAT,
    DATETIME_FORMAT,
    is_approaching_timeout,
    save_timestamp,
    is_overflowed,
)
from ..core.constants import (
    CONNECTOR_NAME,
    DEFAULT_LIMIT,
    DEFAULT_TIME_FRAME,
    POSSIBLE_SEVERITIES,
    TIMESTAMP_KEY,
)
from ..core.UtilsManager import (
    pass_whitelist_filter,
    convert_list_to_comma_string,
    datetime_to_rfc3339,
)
from ..core.SumoLogicCloudSIEMManager import SumoLogicCloudSIEMManager
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
import sys
from EnvironmentCommon import GetEnvironmentCommonFactory


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
    api_key = extract_connector_param(siemplify, param_name="API Key")
    access_id = extract_connector_param(
        siemplify, param_name="Access ID", print_value=True
    )
    access_key = extract_connector_param(siemplify, param_name="Access Key")
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
    lowest_severity_to_fetch = extract_connector_param(
        siemplify, param_name="Lowest Severity To Fetch", print_value=True
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
        param_name="Max Insights To Fetch",
        input_type=int,
        default_value=DEFAULT_LIMIT,
        print_value=True,
    )
    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use dynamic list as a blacklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    device_product_field = extract_connector_param(
        siemplify, "DeviceProductField", is_mandatory=True
    )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        if hours_backwards < 1:
            siemplify.LOGGER.info(
                f"Max Hours Backwards must be greater than zero. The default value {DEFAULT_TIME_FRAME} "
                f"will be used"
            )
            hours_backwards = DEFAULT_TIME_FRAME

        if fetch_limit < 1:
            siemplify.LOGGER.info(
                f"Max Insights To Fetch must be greater than zero. The default value {DEFAULT_LIMIT} "
                f"will be used"
            )
            fetch_limit = DEFAULT_LIMIT

        if (
            lowest_severity_to_fetch
            and lowest_severity_to_fetch.upper() not in POSSIBLE_SEVERITIES
        ):
            raise Exception(
                f'Invalid value provided for "Lowest Severity To Fetch" parameter. Possible values are: '
                f"{convert_list_to_comma_string([severity.title() for severity in POSSIBLE_SEVERITIES])}."
            )

        # Read already existing alerts ids
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(
            f"Successfully loaded {len(existing_ids)} existing alerts from ids file"
        )

        manager = SumoLogicCloudSIEMManager(
            api_root=api_root,
            api_key=api_key,
            access_id=access_id,
            access_key=access_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        last_success_time = get_last_success_time(
            siemplify=siemplify,
            offset_with_metric={"hours": hours_backwards},
            time_format=DATETIME_FORMAT,
        )

        fetched_alerts = []

        insights = manager.get_insights(
            limit=fetch_limit,
            start_timestamp=datetime_to_rfc3339(last_success_time),
            lowest_severity=lowest_severity_to_fetch,
        )

        filtered_alerts = filter_old_alerts(siemplify, insights, existing_ids, "id")
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

                siemplify.LOGGER.info(f"Started processing alert {alert.id}")

                # Update existing alerts
                existing_ids.append(alert.id)
                fetched_alerts.append(alert)

                if not pass_filters(siemplify, whitelist_as_a_blacklist, alert, "name"):
                    continue

                alert_info = alert.get_alert_info(
                    alert_info=AlertInfo(),
                    environment_common=GetEnvironmentCommonFactory().create_environment_manager(
                        siemplify, environment_field_name, environment_regex_pattern
                    ),
                    device_product_field=device_product_field,
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
            save_timestamp(
                siemplify=siemplify, alerts=fetched_alerts, timestamp_key=TIMESTAMP_KEY
            )

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {e}")
        siemplify.LOGGER.exception(e)

        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def pass_filters(siemplify, whitelist_as_a_blacklist, alert, model_key):
    # All alert filters should be checked here
    if not pass_whitelist_filter(siemplify, whitelist_as_a_blacklist, alert, model_key):
        return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
