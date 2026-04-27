from __future__ import annotations
import sys

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler, unix_now, utc_now

from TIPCommon import (
    extract_connector_param,
    read_ids,
    write_ids,
    is_overflowed,
    save_timestamp,
    is_approaching_timeout,
    get_last_success_time,
    pass_whitelist_filter,
    DATETIME_FORMAT,
    TIMEOUT_THRESHOLD,
)
from EnvironmentCommon import GetEnvironmentCommonFactory

from ..core.AWSCloudTrailManager import AWSCloudTrailManager
from ..core.consts import (
    CONNECTOR_DISPLAY_NAME,
    INTEGRATION_DISPLAY_NAME,
    DEFAULT_ALERT_SEVERITY,
    INSIGHTS_ALERT_SEVERITIES,
    DEFAULT_TIMEOUT_IN_SECONDS,
    DEFAULT_MAX_INSIGHTS_TO_FETCH,
    DEFAULT_MAX_HOURS_BACKWARDS,
)


@output_handler
def main(is_test_run):
    connector_starting_time = unix_now()

    processed_alerts = []
    processed_insights = []

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

    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        default_value=DEFAULT_TIMEOUT_IN_SECONDS,
        print_value=True,
    )

    alert_severity = extract_connector_param(
        siemplify,
        param_name="Alert Severity",
        default_value=DEFAULT_ALERT_SEVERITY,
        is_mandatory=False,
        print_value=True,
    )

    max_insights_to_fetch = extract_connector_param(
        siemplify,
        param_name="Max Insights To Fetch",
        input_type=int,
        default_value=DEFAULT_MAX_INSIGHTS_TO_FETCH,
        is_mandatory=False,
        print_value=True,
    )

    max_hours_backwards = extract_connector_param(
        siemplify,
        param_name="Fetch Max Hours Backwards",
        default_value=DEFAULT_MAX_HOURS_BACKWARDS,
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

    if alert_severity.lower() not in INSIGHTS_ALERT_SEVERITIES:
        # Severity value is invalid
        raise Exception(
            f"Alert severity {alert_severity} is invalid. Valid values are: "
            f"Informational, Low, Medium, High, Critical"
        )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        siemplify.LOGGER.info(f"Connecting to {INTEGRATION_DISPLAY_NAME} Service")

        manager = AWSCloudTrailManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )
        manager.test_connectivity()
        siemplify.LOGGER.info(
            f"Successfully connected to {INTEGRATION_DISPLAY_NAME} Service"
        )

        # Read already existing alert ids from ids.json file
        siemplify.LOGGER.info("Loading existing ids from IDS file.")
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(f"Found {len(existing_ids)} existing ids in ids.json")

        last_success_time = get_last_success_time(
            siemplify=siemplify,
            offset_with_metric={"hours": max_hours_backwards},
            time_format=DATETIME_FORMAT,
        )
        siemplify.LOGGER.info(f"Fetching insights...")

        filtered_insights = manager.get_events(
            start_time=last_success_time,
            end_time=utc_now(),
            limit=max_insights_to_fetch,
            last_success_time=last_success_time,
            existing_ids=existing_ids,
        )  # fetch single page of findings

        siemplify.LOGGER.info(
            f"Successfully fetched {len(filtered_insights)} new insights"
        )

        filtered_insights = sorted(
            filtered_insights,
            key=lambda filtered_insight: filtered_insight.event_time_ms,
        )
        ignored_insights = []

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_insights = filtered_insights[:1]

        # process alerts in connector cycle
        for insight in filtered_insights:
            try:
                if len(processed_alerts) >= max_insights_to_fetch:
                    # Provide slicing for the alarms amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle of value "
                        f"{filtered_insights}. No more alerts will be processed in "
                        "this cycle."
                    )
                    break

                if is_approaching_timeout(
                    connector_starting_time, python_process_timeout, TIMEOUT_THRESHOLD
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                existing_ids.append(insight.event_id)

                if not pass_whitelist_filter(
                    siemplify=siemplify,
                    whitelist_as_a_blacklist=use_whitelist_as_blacklist,
                    model=insight,
                    model_key="event_name",
                    whitelist=whitelist,
                ):
                    siemplify.LOGGER.info(
                        f"Insight {insight.event_id} did not pass whitelist. "
                        "Skipping..."
                    )
                    ignored_insights.append(insight)
                    continue

                siemplify.LOGGER.info(f"Started processing insight {insight.event_id}")

                # Get environment
                common_environment = (
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify=siemplify,
                        environment_field_name=environment_field_name,
                        environment_regex_pattern=environment_regex_pattern,
                    )
                )
                alert_info = insight.get_alert_info(common_environment, alert_severity)

                siemplify.LOGGER.info(
                    f"Insight ID: {insight.event_id}, Name: {insight.event_name}, "
                    f"Time: {insight.event_time}"
                )

                # Add alert to processed findings (regardless of overflow status) to mark it as processed
                processed_insights.append(insight)

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        '{alert_name}-{alert_identifier}-{environment}-{product} '
                        'found as overflow alert. Skipping.'.format(
                            alert_name=alert_info.rule_generator,
                            alert_identifier=alert_info.ticket_id,
                            environment=alert_info.environment,
                            product=alert_info.device_product,
                        )
                    )
                    # If is overflowed we should skip
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {insight.event_id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed to process alert {insight.event_id}",
                    alert_id=insight.event_id,
                )
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(
                f"Finished processing Alert {insight.event_id}",
                alert_id=insight.event_id,
            )

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(siemplify, existing_ids)
            # Save timestamp based on the processed findings (processed = alert info created, regardless of overflow
            # status) and the ignored findings (= alerts that didn't pass whitelist/blacklist). New timestamp
            # should be the latest among all of those
            save_timestamp(
                siemplify=siemplify,
                alerts=processed_insights + ignored_insights,
                timestamp_key="event_time_ms",
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
