from __future__ import annotations

import sys

from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import (
    extract_connector_param,
    is_approaching_timeout,
    is_overflowed,
    read_ids,
    write_ids,
)

from ..core.constants import (
    BLACKLIST_FILTER,
    CONNECTOR_NAME,
    CREATED_AT_LOOKBACK_HOURS,
    DEFAULT_LIMIT,
    DEFAULT_TIME_FRAME,
    POSSIBLE_SEVERITIES,
    STORED_IDS_LIMIT,
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

        # The watermark tracks last_sync (DB write time), so alerts that become
        # visible or eligible after creation (e.g. Orca Score populated later) still
        # enter the fetch window. The CreatedAt bound keeps updates of alerts older
        # than the lookback out of the window, preserving "new alerts only" semantics.
        lookback_ms = CREATED_AT_LOOKBACK_HOURS * 60 * 60 * 1000
        saved_timestamp = siemplify.fetch_timestamp()
        if saved_timestamp:
            # Tolerate downtime up to the CreatedAt lookback - alerts older than
            # that age out of the fetch window anyway
            last_sync_cursor = max(saved_timestamp, unix_now() - lookback_ms)
        else:
            last_sync_cursor = unix_now() - hours_backwards * 60 * 60 * 1000
        # On the first run the cursor reaches further back than the lookback, so
        # honor "Max Hours Backwards" instead of capping the backfill. On later
        # runs the cursor is already clamped to the lookback, so this is a no-op.
        created_at_start = min(unix_now() - lookback_ms, last_sync_cursor)
        siemplify.LOGGER.info(f"Fetching alerts from last_sync cursor {last_sync_cursor}")

        existing_ids_set = set(existing_ids)
        fetched_alerts = []
        watermark = 0
        offset = 0
        stop_fetching = False

        while not stop_fetching:
            alerts = manager.get_alerts(
                start_timestamp=created_at_start,
                limit=fetch_limit,
                lowest_severity=lowest_severity,
                categories=category_filter,
                title_filter=siemplify.whitelist,
                title_filter_type=(BLACKLIST_FILTER if whitelist_as_a_blacklist else WHITELIST_FILTER),
                alert_types=alert_type_filter,
                lowest_score=lowest_score,
                last_sync_start_timestamp=last_sync_cursor,
                start_at_index=offset,
            )
            siemplify.LOGGER.info(
                f"Fetched page of {len(alerts)} alerts from last_sync cursor {last_sync_cursor}, offset {offset}"
            )

            if is_test_run:
                siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
                alerts = alerts[:1]
                stop_fetching = True

            for alert in alerts:
                try:
                    if is_approaching_timeout(connector_starting_time, script_timeout):
                        siemplify.LOGGER.info("Timeout is approaching. Connector will gracefully exit")
                        stop_fetching = True
                        break

                    if alert.alert_id in existing_ids_set:
                        # Already ingested in a previous run - advance the watermark
                        # over it so the connector makes progress even when a page
                        # contains only duplicates
                        watermark = max(watermark, alert.last_sync_ms)
                        continue

                    if len(processed_alerts) >= fetch_limit:
                        # Provide slicing for the alerts amount.
                        siemplify.LOGGER.info(
                            "Reached max number of alerts cycle. No more alerts will be processed in this cycle."
                        )
                        stop_fetching = True
                        break

                    siemplify.LOGGER.info(f"Started processing alert {alert.alert_id}")
                    alert.set_events()

                    # Update existing alerts
                    existing_ids.append(alert.alert_id)
                    existing_ids_set.add(alert.alert_id)
                    fetched_alerts.append(alert)
                    watermark = max(watermark, alert.last_sync_ms)

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
                    # The watermark may advance past this alert via later alerts in
                    # the page, so it will not be fetched again - log it as dropped
                    # rather than letting it disappear silently.
                    siemplify.LOGGER.error(
                        f"Failed to process alert {alert.alert_id}. It will be dropped and not retried."
                    )
                    siemplify.LOGGER.exception(e)

                    if is_test_run:
                        raise

                siemplify.LOGGER.info(f"Finished processing alert {alert.alert_id}")

            if (
                stop_fetching
                or len(alerts) < fetch_limit
                or len(processed_alerts) >= fetch_limit
            ):
                # A short page means there are no more alerts in the window, and a
                # full per-cycle quota means the next page would be discarded anyway
                break

            next_cursor = alerts[-1].last_sync_ms
            if next_cursor <= last_sync_cursor:
                # A full page within a single last_sync second (second-resolution
                # ties) - the range start can't move, so page deeper with an offset.
                # Never skip past the tie: rows beyond this page may be unseen.
                # Tie ordering has no secondary sort key, so offsets are only
                # meaningful within this run's back-to-back requests - do not carry
                # the offset across runs. A row that shuffles out of view returns on
                # its next last_sync rewrite, unless its CreatedAt has meanwhile aged
                # out of the lookback window; dedup absorbs the rest.
                offset += len(alerts)
            else:
                last_sync_cursor = next_cursor
                offset = 0

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            if len(existing_ids) > STORED_IDS_LIMIT:
                siemplify.LOGGER.info(
                    f"Alert ids cache exceeded {STORED_IDS_LIMIT} entries, oldest ids will be evicted. "
                    f"If this repeats every run, duplicate cases are possible for re-synced alerts."
                )
            write_ids(siemplify, existing_ids, stored_ids_limit=STORED_IDS_LIMIT)

            if watermark:
                siemplify.LOGGER.info(f"Saving last_sync watermark: {watermark}")
                siemplify.save_timestamp(new_timestamp=watermark)
            else:
                siemplify.LOGGER.info("Timestamp is not updated since no alerts were handled")

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
