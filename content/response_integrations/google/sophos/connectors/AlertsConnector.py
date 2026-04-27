from __future__ import annotations
import sys

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler, unix_now

from EnvironmentCommon import GetEnvironmentCommonFactory

from TIPCommon import (
    extract_connector_param,
    read_ids,
    write_ids,
    get_last_success_time,
    is_approaching_timeout,
    is_overflowed,
    save_timestamp,
    UNIX_FORMAT,
)

from ..core.constants import (
    CONNECTOR_NAME,
    DEFAULT_TIME_FRAME,
    MAX_LIMIT,
    DEFAULT_LIMIT,
    MAX_FETCH_HOURS,
)
from ..core.SophosExceptions import NoAuthParamsProvided
from ..core.SophosManager import SophosManagerForConnector as SophosManager
from ..core.utils import pass_severity_filter, pass_whitelist_filter


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
    )
    auth_token = extract_connector_param(
        siemplify,
        param_name="Base 64 Auth Payload",
    )
    client_id = extract_connector_param(
        siemplify,
        param_name="Client ID",
    )
    client_secret = extract_connector_param(
        siemplify,
        param_name="Client Secret",
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
        param_name="Max Alerts To Fetch",
        input_type=int,
        default_value=DEFAULT_LIMIT,
        print_value=True,
    )
    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use whitelist as a blacklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    device_product_field = extract_connector_param(
        siemplify, "DeviceProductField", is_mandatory=True
    )
    if not any([api_key and auth_token, client_id and client_secret]):
        raise NoAuthParamsProvided(
            "No authentication credentials provided. Please provide either:\n"
            "- API Key and Base 64 Auth Payload, or\n"
            "- Client ID and Client Secret"
        )
    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        if fetch_limit > MAX_LIMIT:
            siemplify.LOGGER.info(
                f"Max Alerts To Fetch exceeded the maximum limit of {MAX_LIMIT}. "
                f"The default value {DEFAULT_LIMIT} will be used"
            )
            fetch_limit = DEFAULT_LIMIT
        elif fetch_limit < 0:
            siemplify.LOGGER.info(
                "Max Alerts To Fetch must be non-negative. "
                f"The default value {DEFAULT_LIMIT} will be used"
            )
            fetch_limit = DEFAULT_LIMIT

        if hours_backwards > 24:
            siemplify.LOGGER.info(
                f"Max Hours Backwards exceeded the maximum limit of {MAX_FETCH_HOURS}. "
                f"The default value {DEFAULT_TIME_FRAME} will be used"
            )
            hours_backwards = DEFAULT_TIME_FRAME
        elif hours_backwards < 0:
            siemplify.LOGGER.info(
                "Max Hours Backwards must be non-negative. "
                f"The default value {DEFAULT_TIME_FRAME} will be used"
            )
            hours_backwards = DEFAULT_TIME_FRAME

        # Read already existing alerts ids
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(f"Successfully loaded {len(existing_ids)} existing ids")

        manager = SophosManager(
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
            api_root=api_root,
            api_key=api_key,
            api_token=auth_token,
            siemplify=siemplify,
        )

        last_success_time = get_last_success_time(
            siemplify=siemplify,
            offset_with_metric={"hours": hours_backwards},
            time_format=UNIX_FORMAT,
        )

        fetched_alerts = []
        filtered_alerts = manager.get_alerts(
            existing_ids=existing_ids, limit=fetch_limit, start_time=last_success_time
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} alerts")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                if is_approaching_timeout(script_timeout, connector_starting_time):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                if len(processed_alerts) >= fetch_limit:
                    # Provide slicing for the alerts amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle. "
                        "No more alerts will be processed in this cycle."
                    )
                    break

                siemplify.LOGGER.info(
                    f"Started processing alert {alert.id} - {alert.threat}"
                )

                # Update existing alerts
                existing_ids.append(alert.id)
                fetched_alerts.append(alert)

                if not pass_filters(
                    siemplify,
                    whitelist_as_a_blacklist,
                    alert,
                    "alert_type",
                    lowest_severity_to_fetch,
                ):
                    continue

                alert_info = alert.get_alert_info(
                    AlertInfo(),
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify, environment_field_name, environment_regex_pattern
                    ),
                    device_product_field,
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}"
                        f"-{alert_info.environment}-{alert_info.device_product} "
                        "found as overflow alert. Skipping..."
                    )
                    # If is overflowed we should skip
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alert.id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process incident {alert.id}")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(f"Finished processing incident {alert.id}")

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(siemplify, existing_ids)
            save_timestamp(
                siemplify=siemplify,
                alerts=fetched_alerts,
                timestamp_key="when",
                convert_a_string_timestamp_to_unix=True,
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


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the
    # ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
