from __future__ import annotations
import sys
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import (
    output_handler,
    utc_now,
    unix_now,
    convert_unixtime_to_datetime,
    convert_datetime_to_unix_time,
)
from ..core.BlueLivManager import BlueLivManager
from ..core.UtilsManager import (
    get_environment_common,
    read_ids,
    write_ids,
    is_overflowed,
    is_approaching_timeout,
    validate_timestamp,
    convert_comma_separated_to_list,
    convert_list_to_comma_string,
)
from TIPCommon import extract_connector_param
from datetime import timedelta

from ..core.consts import (
    THREATS_CONNECTOR_SCRIPT_NAME,
    WHITELIST_FILTER,
    BLACKLIST_FILTER,
    READING_STATUS_MAPPING,
    RELATED_INCIDENTS_MAPPING,
    MAX_RESULTS_LIMIT,
    DEFAULT_RESULTS_LIMIT,
)

connector_starting_time = unix_now()


@output_handler
def main(is_test_run):
    processed_alerts = []
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = THREATS_CONNECTOR_SCRIPT_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    try:
        siemplify.LOGGER.info(
            "------------------- Main - Param Init -------------------"
        )

        api_root = extract_connector_param(
            siemplify, param_name="API URL", is_mandatory=True, print_value=True
        )
        username = extract_connector_param(
            siemplify, param_name="User Name", is_mandatory=True, print_value=True
        )
        password = extract_connector_param(
            siemplify, param_name="Password", is_mandatory=True, print_value=False
        )
        organization_id = extract_connector_param(
            siemplify, param_name="Organization ID", is_mandatory=True, print_value=True
        )
        verify_ssl = extract_connector_param(
            siemplify,
            param_name="Verify SSL",
            default_value=False,
            input_type=bool,
            print_value=True,
        )
        hours_backwards = extract_connector_param(
            siemplify,
            param_name="Fetch Max Hours Backwards",
            input_type=int,
            is_mandatory=False,
            print_value=True,
        )
        fetch_limit = extract_connector_param(
            siemplify,
            param_name="Max Threats To Fetch",
            input_type=int,
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
            default_value=".*",
            print_value=True,
        )
        python_process_timeout = extract_connector_param(
            siemplify,
            param_name="PythonProcessTimeout",
            input_type=int,
            is_mandatory=True,
            print_value=True,
        )
        severity = extract_connector_param(
            siemplify, param_name="Severity", is_mandatory=True, print_value=True
        )

        analysis_type = extract_connector_param(
            siemplify,
            param_name="Analysis Results To Ingest",
            is_mandatory=False,
            print_value=True,
        )
        labels = extract_connector_param(
            siemplify,
            param_name="Labels To Filter By",
            is_mandatory=False,
            print_value=True,
        )
        read_status = extract_connector_param(
            siemplify,
            param_name="Reading Status To Ingest",
            is_mandatory=False,
            print_value=True,
        )
        only_starred = extract_connector_param(
            siemplify,
            param_name="Should ingest only starred threats?",
            input_type=bool,
            print_value=True,
        )
        only_related_to_incidents = extract_connector_param(
            siemplify,
            param_name="Should ingest threats related to incidents?",
            print_value=True,
        )
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

        if fetch_limit > MAX_RESULTS_LIMIT:
            fetch_limit = MAX_RESULTS_LIMIT
            siemplify.LOGGER.info(
                f"Fetch limit is too high, The maximum supported number is {MAX_RESULTS_LIMIT}. "
                f"Setting it to {MAX_RESULTS_LIMIT}"
            )
        elif fetch_limit <= 0:
            fetch_limit = DEFAULT_RESULTS_LIMIT
            siemplify.LOGGER.info(
                f"Given limit is negative. Setting it to default ({DEFAULT_RESULTS_LIMIT})."
            )

        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        # Read already existing alerts ids
        siemplify.LOGGER.info("Reading already existing alerts ids...")
        existing_ids = read_ids(siemplify)

        siemplify.LOGGER.info("Fetching alerts...")
        manager = BlueLivManager(
            api_root=api_root,
            username=username,
            password=password,
            organization_id=organization_id,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        if is_test_run:
            siemplify.LOGGER.info("This is a test run. Ignoring stored timestamps")
            last_success_time_datetime = validate_timestamp(
                utc_now() - timedelta(hours=hours_backwards), hours_backwards
            )
        else:
            last_success_time_datetime = validate_timestamp(
                siemplify.fetch_timestamp(datetime_format=True), hours_backwards
            )

        label_ids = []
        if labels:
            labels_list = convert_comma_separated_to_list(labels)
            organization_labels = manager.get_labels()
            label_ids = [
                label.label_id
                for label in organization_labels
                if label.label_name in labels_list
            ]

        fetched_alerts = []
        filtered_alerts = manager.get_threats(
            existing_ids=existing_ids,
            limit=fetch_limit,
            timestamp=convert_datetime_to_unix_time(last_success_time_datetime),
            analysis_type=analysis_type,
            labels=convert_list_to_comma_string(label_ids),
            read_status=READING_STATUS_MAPPING.get(read_status, 0),
            only_starred=only_starred,
            only_related_to_incidents=RELATED_INCIDENTS_MAPPING.get(
                only_related_to_incidents
            ),
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} alerts")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                siemplify.LOGGER.info(
                    f"Started processing Alert {alert.id} - {alert.title}",
                    alert_id=alert.id,
                )

                if is_approaching_timeout(
                    connector_starting_time, python_process_timeout
                ):
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
                        f"Alert {alert.id} did not pass filters skipping...."
                    )
                    continue

                alert_events = manager.create_events_by_module_type(alert)
                alert_info = alert.to_alert_info(
                    environment=get_environment_common(
                        siemplify, environment_field_name, environment_regex_pattern
                    ),
                    severity=severity,
                    events=alert_events,
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}-"
                        f"{alert_info.device_product} found as overflow alert. Skipping."
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
            if fetched_alerts:
                new_timestamp = fetched_alerts[-1].changed_at
                siemplify.save_timestamp(new_timestamp=new_timestamp)
                siemplify.LOGGER.info(
                    f"New timestamp {convert_unixtime_to_datetime(new_timestamp).isoformat()} has been saved"
                )

            write_ids(siemplify, existing_ids)

    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {err}")
        siemplify.LOGGER.exception(err)
        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def pass_whitelist_filter(siemplify, alert, whitelist, whitelist_filter_type):
    # whitelist filter
    if whitelist:
        if whitelist_filter_type == BLACKLIST_FILTER and alert.module_type in whitelist:
            siemplify.LOGGER.info(
                f"Alert with module type: {alert.module_type} did not pass blacklist filter."
            )
            return False

        if (
            whitelist_filter_type == WHITELIST_FILTER
            and alert.module_type not in whitelist
        ):
            siemplify.LOGGER.info(
                f"Alert with module type: {alert.module_type} did not pass whitelist filter."
            )
            return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
