from __future__ import annotations
import sys

from TIPCommon import (
    extract_connector_param,
    get_last_success_time,
    read_ids_by_timestamp,
    write_ids_with_timestamp,
    is_overflowed,
    save_timestamp,
    is_approaching_timeout,
    pass_whitelist_filter,
)
from EnvironmentCommon import GetEnvironmentCommonFactory
from ..core import consts
from ..core import utils
from ..core.AmazonMacieManager import AmazonMacieManager
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_datetime_to_unix_time
from ..core.exceptions import AmazonMacieValidationException

# =====================================
#             CONSTANTS               #
# =====================================
CONNECTOR_NAME = "Amazon Macie - Findings Connector"


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
        param_name="Max findings to fetch",
        input_type=int,
        is_mandatory=False,
        default_value=consts.DEFAULT_FETCH_LIMIT,
        print_value=True,
    )

    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Fetch Max Hours Backwards",
        input_type=int,
        is_mandatory=False,
        default_value=consts.DEFAULT_HOURS_BACKWARDS,
        print_value=True,
    )

    severities = extract_connector_param(
        siemplify,
        param_name="Finding severity to ingest",
        is_mandatory=False,
        print_value=True,
    )

    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use whitelist as a blacklist",
        is_mandatory=True,
        input_type=bool,
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

        severities = (
            utils.load_csv_to_list(severities, "Severity") if severities else []
        )
        for severity in severities:
            if severity.lower() not in consts.VALID_SEVERITIES:
                raise AmazonMacieValidationException(
                    f"Severity {severity} is invalid. Valid values are: Low, Medium, High."
                )

        # Adjust severities case
        severities = [
            consts.VALID_SEVERITIES.get(severity.lower()) for severity in severities
        ]

        siemplify.LOGGER.info("Connecting to Amazon Macie Service")
        manager = AmazonMacieManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
            verify_ssl=verify_ssl,
        )
        manager.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to Amazon Macie service")

        # Read already existing alerts ids
        siemplify.LOGGER.info("Loading existing ids from IDS file.")
        existing_ids = read_ids_by_timestamp(siemplify)
        siemplify.LOGGER.info(f"Found {len(existing_ids)} existing ids in ids.json")

        last_success_time = get_last_success_time(
            siemplify=siemplify, offset_with_metric={"hours": hours_backwards}
        )

        siemplify.LOGGER.info(
            f"Fetching findings with update time greater than {last_success_time.isoformat()}"
        )

        # if whitelist_as_a_blacklist is False - only findings of type specified in the whitelist will be ingested,
        # otherwise, fetch all findings and process ignored findings later
        if not whitelist_as_a_blacklist:
            finding_types = whitelist if whitelist else None
            siemplify.LOGGER.info(
                "Whitelist as Blacklist is False. Only finding of type specified in the whitelist will be ingested"
            )
        else:
            finding_types = None
            siemplify.LOGGER.info(
                "Whitelist as Blacklist is True. Only finding of type that is not specified in the whitelist will be ingested"
            )

        search_after_token, fetched_findings = manager.get_findings_page(
            finding_types=finding_types,
            severities=severities,
            page_size=min(fetch_limit, consts.PAGE_SIZE),
            updated_at=convert_datetime_to_unix_time(last_success_time),
            asc=True,
        )  # fetch single page of findings

        # new fetched findings that passed whitelist filter and never processed before
        filtered_findings = []

        # findings that exists in ids (already processed) or should be ignored due to whitelist logic
        ignored_findings = []

        # pre-process fetched alerts and fetch more alerts if didn't reach fetch limit
        # this include checking if finding passes whitelist logic
        # and does not already exist in ids.json file
        while fetched_findings:
            if is_approaching_timeout(connector_starting_time, python_process_timeout):
                # Stop loading an try to process as much as we can in the remaining time
                break

            # Filter already seen alerts
            new_alerts = [
                finding
                for finding in fetched_findings
                if finding.id not in existing_ids
            ]

            for alert in new_alerts:  # filter alerts by whitelist/blacklist filter
                if not pass_whitelist_filter(
                    siemplify=siemplify,
                    whitelist_as_a_blacklist=whitelist_as_a_blacklist,
                    model=alert,
                    model_key="type",
                ):
                    # Save ID to whitelist to prevent processing it in the future
                    existing_ids.update({alert.id: unix_now()})
                    ignored_findings.append(alert)
                else:
                    filtered_findings.append(alert)

            # Check if more alerts can be fetched
            if len(filtered_findings) >= fetch_limit:
                break

            if search_after_token:  # if more findings can be fetched from Amazon Macie
                search_after_token, fetched_findings = manager.get_findings_page(
                    finding_types=finding_types,
                    severities=severities,
                    page_size=min(fetch_limit, consts.PAGE_SIZE),
                    updated_at=convert_datetime_to_unix_time(last_success_time),
                    search_after_token=search_after_token,
                    asc=True,
                )  # fetch single page of findings
            else:
                break  # no more alerts to fetch

        siemplify.LOGGER.info(
            f"Found new {len(filtered_findings)} findings out of total of {len(filtered_findings) + len(ignored_findings)} findings."
        )

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_findings = filtered_findings[:1]

        # process filtered fetched alerts in connector cycle
        for alert in filtered_findings:
            try:
                if len(processed_alerts) >= fetch_limit:
                    # Provide slicing for the alarms amount.
                    siemplify.LOGGER.info(
                        f"Reached max number of alerts cycle of value {fetch_limit}. No more alerts will be processed in this cycle."
                    )
                    break

                if is_approaching_timeout(
                    python_process_timeout, connector_starting_time
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                siemplify.LOGGER.info(
                    f"Started processing Alert {alert.id}", alert_id=alert.id
                )

                # update alert as "seen" in ids.json file
                existing_ids.update({alert.id: unix_now()})

                # get alert info with specific environment mapped from environment name/regex parameters
                common_env = GetEnvironmentCommonFactory.create_environment_manager(
                    siemplify=siemplify,
                    environment_field_name=environment_field_name,
                    environment_regex_pattern=environment_regex_pattern,
                )
                alert_info = alert.as_alert_info(common_env)

                siemplify.LOGGER.info(
                    f"Finding ID: {alert.id}, Type: {alert.type}, CreatedTime: {alert.created_time}, UpdatedTime: {alert.updated_time}, Severity: {alert.severity}, Count: {alert.count}"
                )

                # Add alert to processed findings (regardless of overflow status) to mark it as processed
                processed_findings.append(alert)

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
