from __future__ import annotations
import sys
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from ..core.Dome9Manager import Dome9Manager
from ..core.UtilsManager import (
    get_environment_common,
    get_last_success_time,
    is_overflowed,
    save_timestamp,
    read_ids,
    write_ids,
    is_approaching_timeout,
)
from TIPCommon import extract_connector_param


# =====================================
#             CONSTANTS               #
# =====================================
CONNECTOR_NAME = "Check Point Cloud Guard - Alerts Connector"
WHITELIST_FILTER = "whitelist"
BLACKLIST_FILTER = "blacklist"
SEVERITIES_MAP = {
    "Low": [],  # All severities - no filtering
    "Medium": ["Medium", "High"],
    "High": ["High"],
}
HOURS_LIMIT_IN_IDS_FILE = 72
PAGE_SIZE = 100
TIMEOUT_THRESHOLD = 0.9


@output_handler
def main(is_test_run):
    connector_starting_time = unix_now()
    processed_alerts = []
    processed_findings = []
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    api_key_id = extract_connector_param(
        siemplify, param_name="API Key ID", is_mandatory=True
    )
    api_key_secret = extract_connector_param(
        siemplify, param_name="API Key Secret", is_mandatory=True
    )
    verify_ssl = extract_connector_param(
        siemplify, param_name="Verify SSL", default_value=True, input_type=bool
    )

    environment_field_name = extract_connector_param(
        siemplify,
        param_name="Environment Field Name",
        default_value="",
        print_value=True,
    )
    environment_regex_pattern = extract_connector_param(
        siemplify,
        param_name="Environment Regex Pattern",
        default_value="",
        print_value=True,
    )

    fetch_limit = extract_connector_param(
        siemplify,
        param_name="Max Alerts To Fetch",
        input_type=int,
        is_mandatory=False,
        default_value=50,
        print_value=True,
    )
    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Fetch Max Hours Backwards",
        input_type=int,
        is_mandatory=False,
        default_value=1,
        print_value=True,
    )

    min_severity = extract_connector_param(
        siemplify,
        param_name="Lowest Severity To Fetch",
        is_mandatory=True,
        print_value=True,
    )

    if min_severity not in SEVERITIES_MAP:
        # Severity value is invalid
        raise Exception("Severity {} is invalid. Valid values are: Low, Medium, High.")

    severities = SEVERITIES_MAP[min_severity]

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

        manager = Dome9Manager(
            api_key_id=api_key_id, api_key_secret=api_key_secret, verify_ssl=verify_ssl
        )

        # Read already existing alerts ids
        siemplify.LOGGER.info("Loading existing ids from IDS file.")
        existing_ids = read_ids(siemplify, max_hours_backwards=HOURS_LIMIT_IN_IDS_FILE)
        siemplify.LOGGER.info(
            "Found {} existing ids in ids.json".format(len(existing_ids))
        )

        last_success_time = get_last_success_time(
            siemplify=siemplify, offset_with_metric={"hours": hours_backwards}
        )
        siemplify.LOGGER.info(
            "Fetching findings since {}".format(last_success_time.isoformat())
        )

        search_after, fetched_findings = manager.get_findings_page(
            start_time=last_success_time,
            page_size=min(fetch_limit, PAGE_SIZE),
            severities=severities,
        )

        filtered_findings = []
        ignored_findings = []

        while fetched_findings:
            if is_approaching_timeout(
                python_process_timeout, connector_starting_time, TIMEOUT_THRESHOLD
            ):
                # Stop loading an try to process as much as we can in the remaining time
                break

            # Filter already seen alerts
            new_alerts = [
                finding
                for finding in fetched_findings
                if finding.id not in existing_ids
            ]

            for alert in new_alerts:
                if not pass_whitelist_filter(
                    siemplify, alert, whitelist, whitelist_filter_type
                ):
                    # Save ID to whitelist to prevent processing it in the future
                    existing_ids.update({alert.id: unix_now()})
                    ignored_findings.append(alert)
                else:
                    filtered_findings.append(alert)

            # As long as there are more pages and we still have place under the limit - fetch more findings
            if len(filtered_findings) >= fetch_limit:
                break

            search_after, fetched_findings = manager.get_findings_page(
                start_time=last_success_time,
                page_size=min(fetch_limit, PAGE_SIZE),
                severities=severities,
                search_after=search_after,
            )

        siemplify.LOGGER.info(
            "Found new {} findings out of total of {} findings.".format(
                len(filtered_findings), len(filtered_findings) + len(ignored_findings)
            )
        )

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_findings = filtered_findings[:1]

        for alert in filtered_findings:
            try:
                if len(processed_alerts) >= fetch_limit:
                    # Provide slicing for the alarms amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle. No more alerts will be processed in this cycle."
                    )
                    break

                siemplify.LOGGER.info(
                    "Started processing Alert {}".format(alert.id), alert_id=alert.id
                )

                if is_approaching_timeout(
                    python_process_timeout, connector_starting_time, TIMEOUT_THRESHOLD
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                existing_ids.update({alert.id: unix_now()})

                alert_info = alert.as_alert_info(
                    get_environment_common(
                        siemplify, environment_field_name, environment_regex_pattern
                    )
                )

                siemplify.LOGGER.info(
                    "Finding ID: {}, Rule Name: {}, CreatedTime: {}, Severity: {}".format(
                        alert.id, alert.rule_name, alert.created_time, alert.severity
                    )
                )

                # Add alert to processed findings (regardless of overflow status) to mark it as processed
                processed_findings.append(alert)

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        "{alert_name}-{alert_identifier}-{environment}-{product} found as overflow alert. Skipping.".format(
                            alert_name=alert_info.rule_generator,
                            alert_identifier=alert_info.ticket_id,
                            environment=alert_info.environment,
                            product=alert_info.device_product,
                        )
                    )
                    # If is overflowed we should skip
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info("Alert {} was created.".format(alert.id))

            except Exception as e:
                siemplify.LOGGER.error(
                    "Failed to process alert {}".format(alert.id), alert_id=alert.id
                )
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(
                "Finished processing Alert {}".format(alert.id), alert_id=alert.id
            )

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(siemplify, existing_ids)
            # Save timestamp based on the processed findings (processed = alert info created, regardless of overflow
            # status) and the ignored findings (= alerts that didn't pass whitelist/blacklist). New timestamp
            # should be the latest among all of those
            save_timestamp(
                siemplify=siemplify,
                alerts=processed_findings + ignored_findings,
                timestamp_key="created_time_ms",
            )

    except Exception as err:
        siemplify.LOGGER.error("Got exception on main handler. Error: {}".format(err))
        siemplify.LOGGER.exception(err)
        if is_test_run:
            raise

    siemplify.LOGGER.info("Created total of {} cases".format(len(processed_alerts)))
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def pass_whitelist_filter(siemplify, alert, whitelist, whitelist_filter_type):
    # whitelist filter
    if whitelist:
        if whitelist_filter_type == BLACKLIST_FILTER and alert.rule_name in whitelist:
            siemplify.LOGGER.info(
                "Alert {} with rule: {} did not pass blacklist filter.".format(
                    alert.id, alert.rule_name
                )
            )
            return False

        if (
            whitelist_filter_type == WHITELIST_FILTER
            and alert.rule_name not in whitelist
        ):
            siemplify.LOGGER.info(
                "Alert {} with rule: {} did not pass whitelist filter.".format(
                    alert.id, alert.rule_name
                )
            )
            return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
