from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from TIPCommon import extract_connector_param
from ..core.constants import (
    CONNECTOR_NAME,
    DEFAULT_TIME_FRAME,
    DEFAULT_LIMIT,
    EVENTS_DEFAULT_LIMIT,
)
from ..core.UtilsManager import (
    read_ids,
    write_ids,
    get_last_success_time,
    is_approaching_timeout,
    get_environment_common,
    is_overflowed,
    save_timestamp,
    pass_whitelist_filter,
    UNIX_FORMAT,
    convert_comma_separated_to_list,
    construct_alert_info,
)
from ..core.FortiSIEMManager import FortiSIEMManager
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
import sys


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
        siemplify, param_name="API Root", is_mandatory=True, print_value=True
    )
    username = extract_connector_param(
        siemplify, param_name="Username", is_mandatory=True, print_value=True
    )
    password = extract_connector_param(
        siemplify, param_name="Password", is_mandatory=True
    )
    verify_ssl = extract_connector_param(
        siemplify, param_name="Verify SSL", input_type=bool, print_value=True
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

    target_organization_string = extract_connector_param(
        siemplify, param_name="Target Organization", print_value=True
    )

    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Max hours backwards",
        input_type=int,
        is_mandatory=True,
        default_value=DEFAULT_TIME_FRAME,
        print_value=True,
    )
    fetch_limit = extract_connector_param(
        siemplify,
        param_name="Max Incidents Per Cycle",
        input_type=int,
        is_mandatory=True,
        default_value=DEFAULT_LIMIT,
        print_value=True,
    )
    events_limit = extract_connector_param(
        siemplify,
        param_name="Max Events Per Incidents",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )
    statuses_string = extract_connector_param(
        siemplify, param_name="Incident Statuses to Fetch", print_value=True
    )
    min_severity = extract_connector_param(
        siemplify,
        param_name="Minimum Severity to Fetch",
        input_type=int,
        print_value=True,
    )

    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use whitelist as a blacklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    track_new_events = extract_connector_param(
        siemplify,
        "Track New Events Added to Already Ingested Incidents",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    track_new_events_threshold = extract_connector_param(
        siemplify,
        "Track New Events Threshold (hours)",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )

    device_product_field = extract_connector_param(
        siemplify, "DeviceProductField", is_mandatory=True
    )

    statuses = convert_comma_separated_to_list(statuses_string)
    target_organizations = convert_comma_separated_to_list(target_organization_string)

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        if fetch_limit < 0:
            siemplify.LOGGER.info(
                f'"Max Incidents Per Cycle" must be non-negative. The default value '
                f"{DEFAULT_LIMIT} will be used"
            )
            fetch_limit = DEFAULT_LIMIT

        if events_limit < 0:
            siemplify.LOGGER.info(
                f'"Max Events Per Incidents" must be non-negative. The default value '
                f"{EVENTS_DEFAULT_LIMIT} will be used"
            )
            events_limit = EVENTS_DEFAULT_LIMIT

        if hours_backwards < 0:
            siemplify.LOGGER.info(
                f'"Max Hours Backwards" must be non-negative. The default value '
                f"{DEFAULT_TIME_FRAME} will be used"
            )
            hours_backwards = DEFAULT_TIME_FRAME

        # Read already existing alerts ids
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(
            f"Successfully loaded {len(existing_ids.keys())} existing ids"
        )

        manager = FortiSIEMManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        fetched_alerts = []
        filtered_alerts = manager.get_incidents(
            existing_ids=existing_ids,
            limit=fetch_limit,
            start_timestamp=get_last_success_time(
                siemplify=siemplify,
                offset_with_metric={"hours": hours_backwards},
                time_format=UNIX_FORMAT,
            ),
            statuses=statuses,
            events_limit=events_limit,
            track_new_events=track_new_events,
            track_new_events_threshold=track_new_events_threshold,
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} alerts")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                if is_approaching_timeout(script_timeout, connector_starting_time):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                if len(processed_alerts) >= fetch_limit:
                    # Provide slicing for the alerts amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle. No more alerts will be processed in this cycle."
                    )
                    break

                siemplify.LOGGER.info(f"Started processing alert {alert.incident_id}")

                if not pass_filters(
                    siemplify,
                    whitelist_as_a_blacklist,
                    alert,
                    "event_type",
                    organization_filter_key="customer",
                    target_organizations=target_organizations,
                    severity_filter_key="event_severity",
                    min_severity=min_severity,
                ):
                    # Update existing alerts
                    existing_ids[alert.incident_id] = construct_alert_info(
                        alert, existing_ids.get(alert.incident_id, {})
                    )
                    fetched_alerts.append(alert)
                    continue

                events = manager.get_incident_events(alert.incident_id)
                alert.set_events(
                    events,
                    existing_ids.get(alert.incident_id, {}).get("event_ids", []),
                    events_limit,
                )

                # Update existing alerts
                existing_ids[alert.incident_id] = construct_alert_info(
                    alert, existing_ids.get(alert.incident_id, {})
                )
                fetched_alerts.append(alert)

                alert_info = alert.get_alert_info(
                    AlertInfo(),
                    get_environment_common(
                        siemplify, environment_field_name, environment_regex_pattern
                    ),
                    device_product_field,
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}"
                        f"-{alert_info.device_product} found as overflow alert. Skipping..."
                    )
                    # If is overflowed we should skip
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert {alert.incident_id} was created.")

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process alert {alert.incident_id}")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(f"Finished processing alert {alert.incident_id}")

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(siemplify, existing_ids)
            save_timestamp(
                siemplify=siemplify,
                alerts=fetched_alerts,
                timestamp_key="incident_last_seen",
            )

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


def pass_filters(
    siemplify,
    whitelist_as_a_blacklist,
    alert,
    model_key,
    organization_filter_key=None,
    target_organizations=None,
    severity_filter_key=None,
    min_severity=None,
):
    # All alert filters should be checked here
    if not pass_whitelist_filter(siemplify, whitelist_as_a_blacklist, alert, model_key):
        return False

    if (
        target_organizations
        and getattr(alert, organization_filter_key) not in target_organizations
    ):
        siemplify.LOGGER.info(
            f"'{alert.incident_title}' did not pass organization filter."
        )
        return False

    if min_severity and getattr(alert, severity_filter_key) < min_severity:
        siemplify.LOGGER.info(
            f"'{alert.incident_title}' did not pass severity  filter."
        )
        return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
