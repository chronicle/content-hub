from __future__ import annotations
import sys

from TIPCommon import (
    extract_connector_param,
    get_last_success_time,
    UNIX_FORMAT,
    read_ids_by_timestamp,
    write_ids_with_timestamp,
    is_overflowed,
    save_timestamp,
    is_approaching_timeout,
    pass_whitelist_filter,
)
from EnvironmentCommon import GetEnvironmentCommonFactory

from ..core.AWSIAMAnalyzerManager import AWSIAMAnalyzerManager
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from ..core.consts import (
    DEFAULT_TIMEOUT_IN_SECONDS,
    DEFAULT_ALERT_SEVERITY,
    DEFAULT_MAX_FINDINGS_TO_FETCH,
    CONNECTOR_DISPLAY_NAME,
    DEFAULT_HOURS_BACKWARDS,
    SEVERITIES,
    INTEGRATION_NAME,
)


@output_handler
def main(is_test_run):
    connector_starting_time = unix_now()
    processed_alerts = []
    processed_findings = []

    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = CONNECTOR_DISPLAY_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    aws_access_key = extract_connector_param(
        siemplify, param_name="AWS Access Key ID", is_mandatory=True
    )

    aws_secret_key = extract_connector_param(
        siemplify, param_name="AWS Secret Key", print_value=False, is_mandatory=True
    )

    aws_default_region = extract_connector_param(
        siemplify, param_name="AWS Default Region", is_mandatory=True
    )

    environment_field_name = extract_connector_param(
        siemplify,
        param_name="Environment Field Name",
        is_mandatory=False,
        default_value="",
        print_value=True,
    )

    environment_regex_pattern = extract_connector_param(
        siemplify,
        param_name="Environment Regex Pattern",
        default_value=".*",
        is_mandatory=False,
        print_value=True,
    )

    script_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        default_value=DEFAULT_TIMEOUT_IN_SECONDS,
        print_value=True,
    )

    analyzer_name = extract_connector_param(
        siemplify, param_name="Analyzer Name", is_mandatory=True, print_value=True
    )

    alert_severity = extract_connector_param(
        siemplify,
        param_name="Alert Severity",
        default_value=DEFAULT_ALERT_SEVERITY,
        is_mandatory=False,
        print_value=True,
    )

    max_findings_to_fetch = extract_connector_param(
        siemplify,
        param_name="Max Findings To Fetch",
        input_type=int,
        default_value=DEFAULT_MAX_FINDINGS_TO_FETCH,
        is_mandatory=False,
        print_value=True,
    )

    max_hours_backwards = extract_connector_param(
        siemplify,
        param_name="Max Hours Backwards",
        default_value=DEFAULT_HOURS_BACKWARDS,
        input_type=int,
        is_mandatory=False,
        print_value=True,
    )

    use_whitelist_as_blacklist = extract_connector_param(
        siemplify,
        param_name="Use whitelist as a blacklist",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    whitelist = siemplify.whitelist

    if alert_severity.upper() not in SEVERITIES:
        # Severity value is invalid
        raise Exception(
            "Alert severity {} is invalid. Valid values are: Informational, Low, Medium, High, Critical"
        )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        siemplify.LOGGER.info(f"Connecting to {INTEGRATION_NAME} Service")
        manager = AWSIAMAnalyzerManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
            verify_ssl=verify_ssl,
            analyzer_name=analyzer_name,
            siemplify=siemplify,
        )
        manager.test_connectivity()
        siemplify.LOGGER.info(f"Successfully connected to {INTEGRATION_NAME} Service")

        siemplify.LOGGER.info(f"Checking if analyzer: {analyzer_name} is available")
        analyzer = manager.get_analyzer()
        siemplify.LOGGER.info(f"Analyzer: {analyzer_name} is available")

        # Read already existing alert ids from ids.json file
        siemplify.LOGGER.info("Loading existing ids from IDS file.")
        existing_ids = read_ids_by_timestamp(siemplify)
        siemplify.LOGGER.info(f"Found {len(existing_ids)} existing ids in ids.json")

        last_success_time = get_last_success_time(
            siemplify=siemplify,
            offset_with_metric={"hours": max_hours_backwards},
            time_format=UNIX_FORMAT,
        )

        siemplify.LOGGER.info(f"Fetching findings")

        # API does not support querying findings from a specific time, but support sorting by time. So findings will be searched among
        # the latest findings that are older than the last success time of the connector - (last successfully processed alert or Max Hours
        # Backwards if first run)
        filtered_findings = manager.get_findings(
            analyzer_arn=analyzer.arn,
            limit=max_findings_to_fetch,
            existing_ids=existing_ids,
            resource_types=whitelist if not use_whitelist_as_blacklist else [],
            last_success_time=last_success_time,
        )
        filtered_findings = sorted(
            filtered_findings,
            key=lambda filtered_finding: filtered_finding.updated_time_ms,
        )
        ignored_findings = []

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_findings = filtered_findings[:1]

        siemplify.LOGGER.info("Start processing findings as alerts")
        for alert in filtered_findings:
            try:
                if is_approaching_timeout(
                    python_process_timeout=script_timeout,
                    connector_starting_time=connector_starting_time,
                ):
                    break

                if len(processed_alerts) >= max_findings_to_fetch:
                    siemplify.LOGGER.info(
                        "Reached max number of alerts per cycle. No more alert will be processed in this cycle."
                    )
                    break

                existing_ids.update({alert.id: unix_now()})

                if not pass_whitelist_filter(
                    siemplify=siemplify,
                    whitelist_as_a_blacklist=use_whitelist_as_blacklist,
                    model=alert,
                    model_key="resource_type",
                    whitelist=whitelist,
                ):
                    siemplify.LOGGER.info(
                        f"Alert {alert.id} did not pass whitelist. Skipping..."
                    )
                    ignored_findings.append(alert)
                    continue

                siemplify.LOGGER.info(f"Started processing Alert {alert.id}")

                alert_info = alert.as_alert_info(
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify=siemplify,
                        environment_field_name=environment_field_name,
                        environment_regex_pattern=environment_regex_pattern,
                    ),
                    severity=alert_severity,
                )

                siemplify.LOGGER.info(
                    f"Finding ID: {alert.id}, Type: {alert.resource_type}, CreatedTime: "
                    f"{alert.created_at}, UpdatedTime: {alert.updated_at}, Severity: {alert_severity}"
                )

                processed_findings.append(alert)

                if is_overflowed(
                    siemplify=siemplify, alert_info=alert_info, is_test_run=is_test_run
                ):
                    siemplify.LOGGER.info(
                        f"{alert_info.name} - {alert_info.ticket_id} - {alert_info.environment} - "
                        f"{alert_info.product} found as overflow alert. Skipping."
                    )

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

    except Exception as error:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {error}")
        siemplify.LOGGER.exception(error)
        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
