from __future__ import annotations
import sys
from ..core import consts
from ..core.AWSSecurityHubManager import AWSSecurityHubManager
from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import (
    extract_connector_param,
    get_last_success_time,
    read_ids_by_timestamp,
    write_ids_with_timestamp,
    is_overflowed,
    is_approaching_timeout,
    pass_whitelist_filter,
    save_timestamp,
)

CONNECTOR_NAME = "AWS Security Hub - Findings Connector "
WHITELIST_FILTER = "whitelist"
BLACKLIST_FILTER = "blacklist"
SEVERITIES_MAP = {
    "INFORMATIONAL": (),  # All severities - no filtering
    "LOW": ("LOW", "MEDIUM", "HIGH", "CRITICAL"),
    "MEDIUM": ("MEDIUM", "HIGH", "CRITICAL"),
    "HIGH": ("HIGH", "CRITICAL"),
    "CRITICAL": ("CRITICAL",),
}
HOURS_LIMIT_IN_IDS_FILE = 72
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

    aws_access_key = extract_connector_param(
        siemplify, param_name="AWS Access Key ID", is_mandatory=True
    )

    aws_secret_key = extract_connector_param(
        siemplify, param_name="AWS Secret Key", is_mandatory=True
    )

    aws_default_region = extract_connector_param(
        siemplify, param_name="AWS Default Region", is_mandatory=True
    )

    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        print_value=True,
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
        param_name="Max Findings To Fetch",
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

    device_product_field = extract_connector_param(
        siemplify, "DeviceProductField", is_mandatory=True
    )

    min_severity = extract_connector_param(
        siemplify,
        param_name="Lowest Severity To Fetch",
        is_mandatory=True,
        print_value=True,
    )

    min_severity = min_severity.upper()

    if min_severity not in SEVERITIES_MAP:
        # Severity value is invalid
        raise Exception(
            "Severity {} is invalid. Valid values are: Informational, Low, Medium, "
            "High, Critical"
        )

    severities = SEVERITIES_MAP[min_severity]

    use_whitelist_as_blacklist = extract_connector_param(
        siemplify,
        param_name="Use whitelist as a blacklist",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
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

        siemplify.LOGGER.info("Connecting to AWS Security Hub Service")
        hub_client = AWSSecurityHubManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
            verify_ssl=verify_ssl,
        )
        hub_client.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to AWS Security Hub service")

        # Read already existing alerts ids
        siemplify.LOGGER.info("Loading existing ids from IDS file.")
        existing_ids = read_ids_by_timestamp(siemplify)
        siemplify.LOGGER.info(f"Found {len(existing_ids)} existing ids in ids.json")

        last_success_time = get_last_success_time(
            siemplify=siemplify, offset_with_metric={"hours": hours_backwards}
        )

        siemplify.LOGGER.info(
            f"Fetching findings with LastObserved time {last_success_time.isoformat()}"
        )

        search_after_token, fetched_findings = hub_client.get_findings_page(
            severities=severities,
            page_size=min(fetch_limit, consts.PAGE_SIZE),
            start_time=last_success_time,
            end_time=connector_starting_time,
        )  # fetch single page of findings

        siemplify.LOGGER.info(
            "Successfully fetched findings with LastObserved time "
            f"{last_success_time.isoformat()}"
        )

        filtered_findings = []  # new fetched findings that passed whitelist filter
        ignored_findings = (
            []
        )  # findings that exists in ids or in whitelist should be ignored

        # process fetched alerts and fetch more if didn't reach fetch limit
        while fetched_findings:
            if is_approaching_timeout(
                python_process_timeout, connector_starting_time, TIMEOUT_THRESHOLD
            ):
                # Stop loading and try to process as much as we can in the remaining time
                break

            # Filter already seen alerts
            new_alerts = [
                finding
                for finding in fetched_findings
                if finding.id not in existing_ids
            ]

            for alert in new_alerts:  # filter alerts by whitelist/blacklist filter
                is_whitelist = pass_whitelist_filter(
                    siemplify=siemplify,
                    whitelist_as_a_blacklist=use_whitelist_as_blacklist,
                    model=alert,
                    model_key="rule_name",
                    whitelist=whitelist,
                )
                if not is_whitelist:
                    # Save ID to whitelist to prevent processing it in the future
                    existing_ids.update({alert.id: unix_now()})
                    ignored_findings.append(alert)
                else:
                    filtered_findings.append(alert)

            # Check if more alerts can be fetched
            if len(filtered_findings) >= fetch_limit:
                siemplify.LOGGER.info(
                    f"Fetching alert reached max number of alerts cycle: {fetch_limit}"
                )
                break

            if search_after_token:  # if more findings can be fetched from Security Hub
                search_after_token, fetched_findings = hub_client.get_findings_page(
                    severities=severities,
                    page_size=min(fetch_limit, consts.PAGE_SIZE),
                    start_time=last_success_time,
                    end_time=connector_starting_time,
                    search_after_token=search_after_token,
                )  # fetch single page of findings
            else:
                break  # no more alerts to fetch

        siemplify.LOGGER.info(
            f"Found new {len(filtered_findings)} "
            "findings out of total of "
            f"{len(filtered_findings) + len(ignored_findings)} findings."
        )

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_findings = filtered_findings[:1]

        # process alerts in connector cycle
        for alert in filtered_findings:
            try:
                if len(processed_alerts) >= fetch_limit:
                    # Provide slicing for the alarms amount.
                    siemplify.LOGGER.info(
                        f"Reached max number of alerts cycle of value {fetch_limit}. "
                        f"No more alerts will be processed in this cycle."
                    )
                    break

                is_approaching_timeout_value = is_approaching_timeout(
                    python_process_timeout=python_process_timeout,
                    connector_starting_time=connector_starting_time,
                )

                if is_approaching_timeout_value:
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                siemplify.LOGGER.info(
                    f"Started processing Alert {alert.id}", alert_id=alert.id
                )

                existing_ids.update({alert.id: unix_now()})

                common_environment = (
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify=siemplify,
                        environment_field_name=environment_field_name,
                        environment_regex_pattern=environment_regex_pattern,
                    )
                )

                alert_info = alert.as_alert_info(
                    common_environment, device_product_field
                )

                siemplify.LOGGER.info(
                    f"Finding ID: {alert.id}, Rule Name: {alert.rule_name}, "
                    f"CreatedTime: {alert.created_time}, Severity: {alert.severity}"
                )

                # Add alert to processed findings (regardless of overflow status) to mark it as processed
                processed_findings.append(alert)
                is_overflowed_value = is_overflowed(
                    siemplify=siemplify, alert_info=alert_info, is_test_run=is_test_run
                )
                if is_overflowed_value:
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}"
                        f"-{alert_info.ticket_id}"
                        f"-{alert_info.environment}"
                        f"-{alert_info.device_product}"
                        f" found as overflow alert. Skipping."
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
                f"Finished processing Alert {alert.id}", alert_id=alert.id
            )

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids_with_timestamp(siemplify, existing_ids)
            # Save timestamp based on the processed findings (processed = alert info created, regardless of overflow
            # status) and the ignored findings (= alerts that didn't pass whitelist/blacklist). New timestamp
            # should be the latest among all of those
            save_timestamp(
                siemplify=siemplify,
                alerts=processed_findings + ignored_findings,
                timestamp_key="updated_time_ms",
            )

    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {err}")
        siemplify.LOGGER.exception(err)
        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
