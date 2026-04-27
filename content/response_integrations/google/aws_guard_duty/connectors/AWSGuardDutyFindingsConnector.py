from __future__ import annotations
import sys

from TIPCommon.extraction import extract_connector_param
from TIPCommon.smp_io import read_ids_by_timestamp, write_ids_with_timestamp
from TIPCommon.smp_time import (
    get_last_success_time,
    is_approaching_timeout,
    save_timestamp,
)
from TIPCommon.utils import is_overflowed
from TIPCommon.filters import pass_whitelist_filter
from EnvironmentCommon import GetEnvironmentCommonFactory

from ..core.consts import (
    CONNECTOR_NAME,
    DEFAULT_FETCH_LIMIT,
    DEFAULT_HOURS_BACKWARDS,
    PAGE_SIZE,
)
from ..core.AWSGuardDutyManager import AWSGuardDutyManager
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_datetime_to_unix_time


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

    detector_id = extract_connector_param(
        siemplify, param_name="Detector ID", is_mandatory=True, print_value=True
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
        default_value=DEFAULT_FETCH_LIMIT,
        print_value=True,
    )

    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Fetch Max Hours Backwards",
        input_type=int,
        is_mandatory=False,
        default_value=DEFAULT_HOURS_BACKWARDS,
        print_value=True,
    )

    min_severity = extract_connector_param(
        siemplify,
        param_name="Lowest Severity To Fetch",
        is_mandatory=True,
        print_value=True,
        input_type=int,
    )

    if min_severity < 1 or min_severity > 8:
        # Severity value is invalid
        raise Exception(
            "Severity {} is invalid. Valid values are in range from 1 to 8."
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

        siemplify.LOGGER.info("Connecting to AWS GuardDuty Service")
        manager = AWSGuardDutyManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
            verify_ssl=verify_ssl,
        )
        manager.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to AWS GuardDuty service")

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

        search_after_token, fetched_findings = manager.get_findings_page(
            detector_id=detector_id,
            min_severity=min_severity,
            page_size=min(fetch_limit, PAGE_SIZE),
            updated_at=convert_datetime_to_unix_time(last_success_time),
            asc=True,
        )  # fetch single page of findings

        filtered_findings = []  # new fetched findings that passed whitelist filter
        ignored_findings = (
            []
        )  # findings that exists in ids or in whitelist should be ignored

        # process fetched alerts and fetch more if didn't reach fetch limit
        while fetched_findings:
            if is_approaching_timeout(
                python_process_timeout=python_process_timeout,
                connector_starting_time=connector_starting_time,
            ):
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
                    whitelist=whitelist,
                ):
                    # Save ID to whitelist to prevent processing it in the future
                    existing_ids.update({alert.id: unix_now()})
                    ignored_findings.append(alert)
                else:
                    filtered_findings.append(alert)

            # Check if more alerts can be fetched
            if len(filtered_findings) >= fetch_limit:
                break

            if search_after_token:  # if more findings can be fetched from Security Hub
                search_after_token, fetched_findings = manager.get_findings_page(
                    detector_id=detector_id,
                    min_severity=min_severity,
                    page_size=min(fetch_limit, PAGE_SIZE),
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

        # process alerts in connector cycle
        for alert in filtered_findings:
            try:
                if len(processed_alerts) >= fetch_limit:
                    # Provide slicing for the alarms amount.
                    siemplify.LOGGER.info(
                        f"Reached max number of alerts cycle of value {fetch_limit}. No more alerts will be processed in this cycle."
                    )
                    break

                if is_approaching_timeout(
                    connector_starting_time=connector_starting_time,
                    python_process_timeout=python_process_timeout,
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                siemplify.LOGGER.info(
                    f"Started processing Alert {alert.id}", alert_id=alert.id
                )

                existing_ids.update({alert.id: unix_now()})

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
