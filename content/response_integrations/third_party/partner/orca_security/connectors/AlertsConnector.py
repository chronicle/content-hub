from __future__ import annotations

import sys

from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import (
    UNIX_FORMAT,
    extract_connector_param,
    filter_old_alerts,
    get_last_success_time,
    is_approaching_timeout,
    is_overflowed,
    read_ids,
    save_timestamp,
    write_ids,
)

from ..core.constants import (
    BLACKLIST_FILTER,
    CONNECTOR_NAME,
    DEFAULT_LIMIT,
    DEFAULT_TIME_FRAME,
    POSSIBLE_SEVERITIES,
    WHITELIST_FILTER,
)
from ..core.OrcaSecurityExceptions import OrcaSecurityInvalidParameterException
from ..core.OrcaSecurityManager import OrcaSecurityManager
from ..core.UtilsManager import convert_comma_separated_to_list, convert_list_to_comma_string

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
        siemplify,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_connector_param(
        siemplify,
        param_name="API Key",
        is_mandatory=False,
    )
    api_token = extract_connector_param(
        siemplify,
        param_name="API Token",
        is_mandatory=False,
    )
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    environment_field_name = extract_connector_param(
        siemplify,
        param_name="Environment Field Name",
        print_value=True,
    )
    environment_regex_pattern = extract_connector_param(
        siemplify,
        param_name="Environment Regex Pattern",
        print_value=True,
    )

    script_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )
    category_filter_string = extract_connector_param(
        siemplify,
        param_name="Category Filter",
        print_value=True,
    )
    alert_type_filter_string = extract_connector_param(
        siemplify,
        param_name="Alert Type Filter",
        print_value=True,
    )
    lowest_severity = extract_connector_param(
        siemplify,
        param_name="Lowest Severity To Fetch",
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
        param_name="Max Alerts To Fetch",
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
        siemplify,
        "DeviceProductField",
        is_mandatory=True,
    )

    lowest_score = extract_connector_param(
        siemplify,
        "Lowest Orca Score To Fetch",
        print_value=True,
    )

    category_filter = convert_comma_separated_to_list(category_filter_string)
    alert_type_filter = convert_comma_separated_to_list(alert_type_filter_string)
    lowest_severity = lowest_severity and lowest_severity.lower()

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
                f"Max Alerts To Fetch must be greater than zero. The default value {DEFAULT_LIMIT} "
                f"will be used"
            )
            fetch_limit = DEFAULT_LIMIT

        if lowest_severity and lowest_severity not in POSSIBLE_SEVERITIES:
            raise Exception(
                f'Invalid value provided for "Lowest Severity To Fetch" parameter. Possible values are: '
                f"{convert_list_to_comma_string([severity.title() for severity in POSSIBLE_SEVERITIES])}."
            )
        try:
            lowest_score = float(lowest_score) if lowest_score else None
        except ValueError as err:
            raise OrcaSecurityInvalidParameterException(
                f"Invalid parameter 'Lowest Orca Score To Fetch'. "
                f"The value must be a number. {err}. "
                f"Wrong value provided: {lowest_score}"
            ) from err

        if lowest_score is not None and (lowest_score < 1.0 or lowest_score > 10.0):
            raise OrcaSecurityInvalidParameterException(
                "Invalid value provided for 'Lowest Orca Score To Fetch' parameter."
                "Accepted values range from 1 to 10. Please adjust the input "
                "accordingly."
            )
        # Read already existing alerts ids
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(
            f"Successfully loaded {len(existing_ids)} existing alerts from ids file"
        )

        manager = OrcaSecurityManager(
            api_root=api_root,
            api_key=api_key,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        fetched_alerts = []
        alerts = manager.get_alerts(
            start_timestamp=get_last_success_time(
                siemplify=siemplify,
                offset_with_metric={"hours": hours_backwards},
                time_format=UNIX_FORMAT,
            ),
            limit=fetch_limit,
            lowest_severity=lowest_severity,
            categories=category_filter,
            title_filter=siemplify.whitelist,
            title_filter_type=(BLACKLIST_FILTER if whitelist_as_a_blacklist else WHITELIST_FILTER),
            alert_types=alert_type_filter,
            lowest_score=lowest_score,
        )

        filtered_alerts = filter_old_alerts(siemplify, alerts, existing_ids, "alert_id")
        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} alerts")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                if is_approaching_timeout(connector_starting_time, script_timeout):
                    siemplify.LOGGER.info("Timeout is approaching. Connector will gracefully exit")
                    break

                if len(processed_alerts) >= fetch_limit:
                    # Provide slicing for the alerts amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle. No more alerts will be processed in this cycle."
                    )
                    break

                siemplify.LOGGER.info(f"Started processing alert {alert.alert_id}")
                alert.set_events()

                # Update existing alerts
                existing_ids.append(alert.alert_id)
                fetched_alerts.append(alert)

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
                siemplify.LOGGER.info(f"Alert {alert.alert_id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process alert {alert.alert_id}")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(f"Finished processing alert {alert.alert_id}")

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(siemplify, existing_ids)
            save_timestamp(
                siemplify=siemplify,
                alerts=fetched_alerts,
                timestamp_key="created_at_ms",
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


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
