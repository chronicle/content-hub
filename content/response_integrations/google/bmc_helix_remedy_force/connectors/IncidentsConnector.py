from __future__ import annotations
import sys

from ..core.BMCHelixRemedyForceManager import BMCHelixRemedyForceManager
from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from TIPCommon import (
    extract_connector_param,
    read_ids,
    write_ids,
    is_overflowed,
    is_approaching_timeout,
    get_last_success_time,
    save_timestamp,
    pass_whitelist_filter,
    convert_comma_separated_to_list,
    DATETIME_FORMAT,
)
from ..core.constants import (
    CONNECTOR_NAME,
    DEFAULT_TIME_FRAME,
    MAX_LIMIT,
    DEFAULT_LIMIT,
    API_TIME_FORMAT,
    DEFAULT_PRIORITY,
)


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
    login_api_root = extract_connector_param(
        siemplify, param_name="Login API Root", is_mandatory=True, print_value=True
    )
    username = extract_connector_param(
        siemplify, param_name="Username", print_value=True
    )
    password = extract_connector_param(siemplify, param_name="Password")
    client_id = extract_connector_param(siemplify, param_name="Client ID")
    client_secret = extract_connector_param(siemplify, param_name="Client Secret")
    refresh_token = extract_connector_param(siemplify, param_name="Refresh Token")
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
    lowest_priority_to_fetch = extract_connector_param(
        siemplify,
        param_name="Lowest Priority To Fetch",
        input_type=int,
        print_value=True,
    )
    ingest_empty_priority = extract_connector_param(
        siemplify,
        "Ingest Empty Priority Incidents",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    type_filter = extract_connector_param(
        siemplify, param_name="Type Filter", print_value=True
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
        param_name="Max Incidents To Fetch",
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

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        if fetch_limit > MAX_LIMIT:
            siemplify.LOGGER.info(
                f"Max Incidents To Fetch exceeded the maximum limit of {MAX_LIMIT}. "
                f"The default value {DEFAULT_LIMIT} will be used"
            )
            fetch_limit = DEFAULT_LIMIT
        elif fetch_limit < 0:
            siemplify.LOGGER.info(
                f"Max Incidents To Fetch must be non-negative. "
                f"The default value {DEFAULT_LIMIT} will be used"
            )
            fetch_limit = DEFAULT_LIMIT

        if hours_backwards < 0:
            siemplify.LOGGER.info(
                f"Max Hours Backwards must be non-negative. "
                f"The default value {DEFAULT_TIME_FRAME} will be used"
            )
            hours_backwards = DEFAULT_TIME_FRAME

        if lowest_priority_to_fetch:
            if lowest_priority_to_fetch > 5 or lowest_priority_to_fetch < 1:
                siemplify.LOGGER.info(
                    f"Lowest Priority To Fetch must be between 1 and 5. "
                    f"The default value {DEFAULT_PRIORITY} will be used"
                )
                lowest_priority_to_fetch = DEFAULT_PRIORITY

        # Read already existing alerts ids
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(f"Successfully loaded {len(existing_ids)} existing ids")

        manager = BMCHelixRemedyForceManager(
            api_root=api_root,
            password=password,
            username=username,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            login_api_root=login_api_root,
        )

        fetched_alerts = []
        raw_start_time = get_last_success_time(
            siemplify=siemplify,
            offset_with_metric={"hours": hours_backwards},
            time_format=DATETIME_FORMAT,
        )
        filtered_alerts = manager.get_incidents(
            existing_ids=existing_ids,
            limit=fetch_limit,
            start_time=raw_start_time.strftime(API_TIME_FORMAT),
            lowest_priority=lowest_priority_to_fetch,
            ingest_empty_priority=ingest_empty_priority,
            types=convert_comma_separated_to_list(type_filter),
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} incidents")

        if is_test_run:
            siemplify.LOGGER.info(
                "This is a TEST run. Only 1 incident will be processed."
            )
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
                        "Reached max number of incidents cycle. No more incidents will be processed in this cycle."
                    )
                    break

                siemplify.LOGGER.info(
                    f"Started processing incident {alert.id} - {alert.title}"
                )

                # Update existing alerts
                existing_ids.append(alert.id)
                fetched_alerts.append(alert)

                if not pass_filters(
                    siemplify, whitelist_as_a_blacklist, alert, "title"
                ):
                    continue

                environment_common = (
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify,
                        environment_field_name=environment_field_name,
                        environment_regex_pattern=environment_regex_pattern,
                    )
                )
                alert_info = alert.get_alert_info(
                    AlertInfo(), environment_common, device_product_field
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
                timestamp_key="created_date",
                convert_a_string_timestamp_to_unix=True,
            )

        siemplify.LOGGER.info(
            f"Incidents processed: {len(processed_alerts)} out of {len(fetched_alerts)}"
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
