from __future__ import annotations
import sys
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
from EnvironmentCommon import GetEnvironmentCommonFactory
from ..core.DevoManager import DevoManager
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from ..core.consts import (
    ALERTS_CONNECTOR_NAME,
    INTEGRATION_IDENTIFIER,
    DEFAULT_OFFSET_TIME_IN_HOURS,
    DEFAULT_MAX_ALERTS_PER_CYCLE,
    BLACKLIST_FILTER,
    WHITELIST_FILTER,
    ALERT_PRIORITIES,
    CONNECTOR_TABLE_NAME,
    QUERY,
    FROM,
    TO,
    NOW,
    MODE,
    MODE_TYPE,
    JSON_MODE,
    REVERSED_MAPPED_ALERT_PRIORITIES,
    STORED_IDS_LIMIT,
)
from ..core.exceptions import DevoManagerErrorValidationException
from ..core.utils import build_devo_query


CONNECTOR_STARTING_TIME = unix_now()


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = ALERTS_CONNECTOR_NAME
    processed_alerts = []
    fetched_alerts = []
    overflowed = 0

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("=================== Main - Param Init ===================")

    # Connector configuration
    api_url = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True, print_value=True
    )
    api_token = extract_connector_param(
        siemplify,
        param_name="API Token",
        is_mandatory=False,
        print_value=False,
        remove_whitespaces=False,
    )
    api_key = extract_connector_param(
        siemplify,
        param_name="API Key",
        is_mandatory=False,
        print_value=False,
        remove_whitespaces=False,
    )
    api_secret = extract_connector_param(
        siemplify,
        param_name="API Secret",
        is_mandatory=False,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        default_value=True,
        print_value=True,
    )
    environment_field_name = extract_connector_param(
        siemplify,
        param_name="Environment Field Name",
        default_value="",
        print_value=True,
    )
    environment_regex_pattern = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern", print_value=True
    )
    script_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        is_mandatory=True,
        input_type=int,
        default_value=300,
        print_value=True,
    )
    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Offset time in hours",
        input_type=int,
        default_value=DEFAULT_OFFSET_TIME_IN_HOURS,
        print_value=True,
    )
    max_alerts_per_cycle = extract_connector_param(
        siemplify,
        param_name="Max Alerts Per Cycle",
        input_type=int,
        default_value=DEFAULT_MAX_ALERTS_PER_CYCLE,
        print_value=True,
    )
    minimum_priority_to_fetch = extract_connector_param(
        siemplify,
        param_name="Minimum Priority to Fetch",
        is_mandatory=False,
        print_value=True,
    )
    if minimum_priority_to_fetch:
        minimum_priority_to_fetch = minimum_priority_to_fetch.strip()

    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use whitelist as a blacklist",
        is_mandatory=True,
        default_value=False,
        input_type=bool,
        print_value=True,
    )

    whitelist_filter_type = (
        BLACKLIST_FILTER if whitelist_as_a_blacklist else WHITELIST_FILTER
    )
    whitelist = (
        siemplify.whitelist
        if isinstance(siemplify.whitelist, list)
        else [siemplify.whitelist]
    )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        if max_alerts_per_cycle <= 0:
            siemplify.LOGGER.info(
                f'"Max Alerts Per Cycle" must be positive. The default value {DEFAULT_MAX_ALERTS_PER_CYCLE} will be used'
            )
            max_alerts_per_cycle = DEFAULT_MAX_ALERTS_PER_CYCLE

        if hours_backwards < 0:
            siemplify.LOGGER.info(
                f"Max Hours Backwards must be non-negative. The default value {DEFAULT_OFFSET_TIME_IN_HOURS} "
                f"will be used"
            )
            hours_backwards = DEFAULT_OFFSET_TIME_IN_HOURS

        # validate minimum alert priority to fetch
        if (
            minimum_priority_to_fetch
            and minimum_priority_to_fetch not in ALERT_PRIORITIES
        ):
            raise DevoManagerErrorValidationException(
                f'Invalid value provided for "Minimum Priority to Fetch" parameter. Possible values are: '
                f" {', '.join(ALERT_PRIORITIES)}."
            )

        # Read already existing alerts ids
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(f"Successfully loaded {len(existing_ids)} existing ids")

        if whitelist:
            siemplify.LOGGER.info(
                f"Whitelist/Blacklist mode: {'Whitelist' if whitelist_filter_type == WHITELIST_FILTER else 'Blacklist'}"
            )
            siemplify.LOGGER.info(
                f"Provided values for {'Whitelist' if whitelist_filter_type == WHITELIST_FILTER else 'Blacklist'} logic: {', '.join(whitelist)}"
            )

        manager = DevoManager(
            api_url=api_url,
            api_token=api_token,
            api_key=api_key,
            api_secret=api_secret,
            verify_ssl=verify_ssl,
            force_test_connectivity=False,
            siemplify=siemplify,
        )

        siemplify.LOGGER.info("Creating the query to execute")
        where_filter = []
        if minimum_priority_to_fetch:
            where_filter.append(
                f"priority>={REVERSED_MAPPED_ALERT_PRIORITIES.get(minimum_priority_to_fetch)}"
            )

        where_filter_str = ", ".join(where_filter)
        query = build_devo_query(
            table_name=CONNECTOR_TABLE_NAME,
            where_filter=where_filter_str,
            fields_to_return="",
            whitelist_blacklist_mode=whitelist_filter_type,
            whitelist_blacklist_param_name="context",
            whitelist_blacklist=whitelist,
        )
        siemplify.LOGGER.info(f"The following query has been created: {query}")

        last_run_timestamp = get_last_success_time(
            siemplify=siemplify,
            offset_with_metric={"hours": hours_backwards},
            time_format=UNIX_FORMAT,
            microtime=True,
        )
        siemplify.LOGGER.info(f"TIME: {int(last_run_timestamp)}")

        # Query Parameters
        params = {
            QUERY: query,
            FROM: int(last_run_timestamp),
            TO: NOW,
            MODE: {MODE_TYPE: JSON_MODE},
        }

        siemplify.LOGGER.info(f"Fetching alerts from {INTEGRATION_IDENTIFIER} service")
        filtered_alerts = manager.get_alerts(
            params=params, existing_ids=existing_ids, limit=max_alerts_per_cycle
        )
        siemplify.LOGGER.info(
            f"Fetched new {len(filtered_alerts)} alerts from {INTEGRATION_IDENTIFIER} service"
        )

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                if is_approaching_timeout(script_timeout, CONNECTOR_STARTING_TIME):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                if len(processed_alerts) >= max_alerts_per_cycle:
                    # Provide slicing for the alerts amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle. No more alerts will be processed in this cycle."
                    )
                    break

                siemplify.LOGGER.info(f"Started processing alert {alert.alert_id}")

                # Check if already processed
                if alert.alert_id in existing_ids:
                    siemplify.LOGGER.info(
                        f"Alert {alert.alert_id} skipped since it has been fetched before"
                    )
                    fetched_alerts.append(alert)
                    continue

                # Update existing alerts
                siemplify.LOGGER.info(
                    f"Appending alert {alert.alert_id} to existing ids"
                )
                existing_ids.append(alert.alert_id)
                fetched_alerts.append(alert)
                siemplify.LOGGER.info(
                    f"Successfully appended alert {alert.alert_id} to existing ids"
                )

                # Creating alert info
                siemplify.LOGGER.info(
                    f"Creating alert info object to alert {alert.alert_id}"
                )
                alert_info = alert.to_alert_info(
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify, environment_field_name, environment_regex_pattern
                    )
                )
                siemplify.LOGGER.info(
                    f"Successfully created alert info object to alert {alert.alert_id}"
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}"
                        f"-{alert_info.device_product} found as overflow alert. Skipping..."
                    )
                    # If is overflowed we should skip
                    overflowed += 1
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert '{alert.alert_id}' was created.")

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process alert {alert.alert_id}")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(f"Finished processing alert {alert.alert_id}")

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(siemplify, existing_ids, stored_ids_limit=STORED_IDS_LIMIT)
            save_timestamp(
                siemplify=siemplify, alerts=fetched_alerts, timestamp_key="eventdate"
            )

        siemplify.LOGGER.info(
            f"Alerts processed: {len(processed_alerts)} out of {len(fetched_alerts)} (Overflowed: {overflowed})"
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
