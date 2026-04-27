from __future__ import annotations
import sys

from soar_sdk.SiemplifyUtils import output_handler, unix_now
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

from TIPCommon.extraction import extract_connector_param
from TIPCommon.smp_io import read_ids, write_ids

from ..core.constants import (
    BLACKLIST_FILTER,
    CONNECTOR_NAME,
    DEFAULT_TIME_FRAME,
    WHITELIST_FILTER,
    MAX_RISK_SCORE,
    MIN_RISK_SCORE,
    UNIX_FORMAT,
)
from ..core.CofenseTriageExceptions import CofenseTriageException
from ..core.CofenseTriageManager import CofenseTriageManager
from ..core.UtilsManager import (
    get_environment_common,
    get_last_success_time,
    hours_to_milliseconds,
    is_approaching_timeout,
    is_overflowed,
    save_timestamp,
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
        siemplify, param_name="API Root", is_mandatory=True, print_value=True
    )
    client_id = extract_connector_param(
        siemplify, param_name="Client ID", is_mandatory=True, print_value=True
    )
    client_secret = extract_connector_param(
        siemplify, param_name="Client Secret", is_mandatory=True
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
    fetch_limit = extract_connector_param(
        siemplify, param_name="Max Reports To Fetch", input_type=int, print_value=True
    )
    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Fetch Max Hours Backwards",
        input_type=int,
        default_value=DEFAULT_TIME_FRAME,
        print_value=True,
    )
    padding_period = extract_connector_param(
        siemplify,
        "Padding Time",
        is_mandatory=False,
        input_type=int,
        print_value=True,
        default_value=0,
    )
    lowest_risk_score = extract_connector_param(
        siemplify,
        param_name="Lowest Risk Score To Fetch",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )
    report_location = extract_connector_param(
        siemplify,
        param_name="Report Location",
        print_value=True,
    )
    categorization_tags = extract_connector_param(
        siemplify,
        param_name="Category",
        print_value=True,
    )

    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use whitelist as a blacklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    disable_overflow = extract_connector_param(
        siemplify,
        "Disable Overflow",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    whitelist_filter_type = (
        BLACKLIST_FILTER if whitelist_as_a_blacklist else WHITELIST_FILTER
    )
    whitelist = siemplify.whitelist

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        if lowest_risk_score < MIN_RISK_SCORE or lowest_risk_score > MAX_RISK_SCORE:
            raise CofenseTriageException(
                f"Risk Score value should be in range from "
                f"{MIN_RISK_SCORE} to {MAX_RISK_SCORE}"
            )
        if padding_period < 0:
            raise CofenseTriageException(
                "Padding period value should be a non-negative number"
            )

        # Read already existing alerts ids
        siemplify.LOGGER.info("Reading already existing alerts ids...")
        existing_ids = read_ids(siemplify)

        siemplify.LOGGER.info("Fetching alerts...")
        manager = CofenseTriageManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        last_success_timestamp = get_last_success_time(
            siemplify=siemplify,
            offset_with_metric={"hours": hours_backwards},
            time_format=UNIX_FORMAT,
        )

        if padding_period > 0:
            start_time = last_success_timestamp - hours_to_milliseconds(padding_period)
            siemplify.LOGGER.info(
                f"Using Start time of last success time - padding time"
                f"to fetch alerts. "
                f"Unix: {start_time} will be used as "
                f"Start time"
            )
        else:
            start_time = last_success_timestamp

        fetched_alerts = []
        all_alerts, filtered_alerts = manager.get_alerts(
            existing_ids=existing_ids,
            limit=fetch_limit,
            start_timestamp=start_time,
            lowest_risk_score=lowest_risk_score,
            report_location=report_location,
            categorization_tags=categorization_tags,
            is_test_run=is_test_run,
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
                        "Reached max number of alerts cycle. No more alerts will be "
                        "processed in this cycle."
                    )
                    break

                siemplify.LOGGER.info(f"Started processing alert with id {alert.id}")

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
                        f"Alert with id {alert.id} did not pass filters skipping..."
                    )
                    continue

                alert_info = alert.get_alert_info(
                    AlertInfo(),
                    get_environment_common(
                        siemplify, environment_field_name, environment_regex_pattern
                    ),
                    api_root,
                )

                if not disable_overflow and is_overflowed(
                    siemplify,
                    alert_info,
                    is_test_run,
                ):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}-"
                        f"{alert_info.environment}-{alert_info.device_product} "
                        f"found as overflow alert. Skipping."
                    )
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert with id {alert.id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed to process alert with id {alert.id}", alert_id=alert.id
                )
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(
                f"Finished processing alert with id {alert.id}", alert_id=alert.id
            )

        if not is_test_run:
            save_timestamp(
                siemplify=siemplify,
                alerts=all_alerts,
                timestamp_key="updated_at",
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
        if whitelist_filter_type == BLACKLIST_FILTER and alert.name in whitelist:
            siemplify.LOGGER.info(
                f"Alert with name: {alert.name} did not pass blacklist filter."
            )
            return False

        if whitelist_filter_type == WHITELIST_FILTER and alert.name not in whitelist:
            siemplify.LOGGER.info(
                f"Alert with name: {alert.name} did not pass whitelist filter."
            )
            return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable
    # from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
