from __future__ import annotations
import sys
import json

from TIPCommon import (
    extract_connector_param,
    read_ids,
    write_ids,
    get_last_success_time,
    is_approaching_timeout,
    is_overflowed,
    save_timestamp,
    pass_whitelist_filter,
    read_content,
    write_content,
)
from EnvironmentCommon import GetEnvironmentCommonFactory
from ..core import datamodels
from ..core.RSAManager import RSAManager
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from ..core.UtilsManager import (
    convert_datetime_to_string,
    limit_events_per_siemplify_alert,
    convert_minutes_to_milliseconds,
    convert_milliseconds_to_minutes,
)
from ..core.constants import (
    CONNECTOR_NAME,
    SEVERITY_MAP,
    MIN_HOURS_BACKWARDS,
    DEFAULT_FETCH_MAX_HOURS_BACKWARDS,
    DEFAULT_FETCH_MAX_REPORTS,
    DEFAULT_LOWEST_RISK_SCORE,
    MIN_RISK_SCORE,
    MAX_RISK_SCORE,
    MIN_REPORTS_TO_FETCH,
    MAX_REPORTS_TO_FETCH,
    PROVIDER_NAME,
    INCIDENT_TIME_THRESHOLD_MINUTES,
    MAX_EVENTS_PER_ALERT,
    DEFAULT_USERNAME_STRING,
    DEFAULT_PASSWORD_STRING,
    UNPROCESSED_INCIDENT_DB_KEY,
    UNPROCESSED_INCIDENT_FILE_NAME,
)
from ..core.RSAExceptions import RSAAuthenticationException

connector_starting_time = unix_now()


@output_handler
def main(is_test_run):
    processed_alerts = []
    all_alerts = []
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    # Integration Configuration
    ui_api_root = extract_connector_param(
        siemplify, param_name="Web API Root", is_mandatory=True
    )
    ui_username = extract_connector_param(
        siemplify, param_name="Web Username", is_mandatory=True
    )
    ui_password = extract_connector_param(
        siemplify, param_name="Web Password", is_mandatory=True
    )
    broker_api_root = extract_connector_param(siemplify, param_name="Broker API Root")
    broker_username = extract_connector_param(
        siemplify, param_name="Broker API Username"
    )
    broker_password = extract_connector_param(
        siemplify, param_name="Broker API Password"
    )
    concentrator_api_root = extract_connector_param(
        siemplify, param_name="Concentrator API Root"
    )
    concentrator_username = extract_connector_param(
        siemplify, param_name="Concentrator API Username"
    )
    concentrator_password = extract_connector_param(
        siemplify, param_name="Concentrator API Password"
    )
    credentials_json = extract_connector_param(
        siemplify, param_name="Credential JSON Object"
    )
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        is_mandatory=True,
        default_value=False,
        input_type=bool,
    )

    # Connector parameters
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
    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Fetch Max Hours Backwards",
        print_value=True,
        input_type=int,
        default_value=DEFAULT_FETCH_MAX_HOURS_BACKWARDS,
    )
    lowest_risk_score = extract_connector_param(
        siemplify,
        param_name="Lowest Risk Score To Fetch",
        print_value=True,
        input_type=int,
        default_value=DEFAULT_LOWEST_RISK_SCORE,
    )
    severity_fallback = extract_connector_param(
        siemplify, param_name="Severity Fallback", is_mandatory=True, print_value=True
    )
    max_reports_to_fetch = extract_connector_param(
        siemplify,
        param_name="Max Incidents To Fetch",
        print_value=True,
        input_type=int,
        default_value=DEFAULT_FETCH_MAX_REPORTS,
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

    whitelist = siemplify.whitelist

    credentials_dict = {}
    if credentials_json:
        try:
            credentials_dict = json.loads(credentials_json)
            broker_api_root = None
            broker_username = (None,)
            broker_password = (None,)
            concentrator_api_root = (None,)
            concentrator_username = (None,)
            concentrator_password = None
            if (
                DEFAULT_PASSWORD_STRING not in credentials_dict
                or DEFAULT_USERNAME_STRING not in credentials_dict
            ):
                raise
        except:
            raise Exception("Invalid JSON object provided. Please double check it")

    if not SEVERITY_MAP.get(severity_fallback):
        raise Exception(
            f'"Severity Fallback" {severity_fallback} is invalid. Valid values are: Informational, Low, Medium, High, Critical'
        )

    if lowest_risk_score < MIN_RISK_SCORE or lowest_risk_score > MAX_RISK_SCORE:
        raise Exception(
            f'"Lowest Risk Score To Fetch" parameter is invalid. Value must be between {MIN_RISK_SCORE} and'
            f" {MAX_RISK_SCORE}"
        )

    if max_reports_to_fetch > MAX_REPORTS_TO_FETCH:
        siemplify.LOGGER.info(
            f'"Max Incidents To Fetch" parameter provided is greater than {MAX_REPORTS_TO_FETCH}. Using parameter value '
            f"of {MAX_REPORTS_TO_FETCH}"
        )
        max_reports_to_fetch = MAX_REPORTS_TO_FETCH

    if max_reports_to_fetch < MIN_REPORTS_TO_FETCH:
        siemplify.LOGGER.info(
            f'"Max Incidents To Fetch" parameter provided is non-positive. Using default value of {DEFAULT_FETCH_MAX_REPORTS}'
        )
        max_reports_to_fetch = DEFAULT_FETCH_MAX_REPORTS

    if hours_backwards < MIN_HOURS_BACKWARDS:
        siemplify.LOGGER.info(
            f'"Fetch Max Hours Backwards" parameter provided is non-positive. Using default value of {DEFAULT_FETCH_MAX_HOURS_BACKWARDS}'
        )
        hours_backwards = DEFAULT_FETCH_MAX_HOURS_BACKWARDS

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        # Read already existing alerts ids
        siemplify.LOGGER.info("Reading already existing alerts ids...")
        existing_ids = read_ids(siemplify)

        if any(isinstance(item, str) for item in existing_ids):
            refactored_ids_list = [
                {"id": item, "event_count": "N/A"} for item in existing_ids
            ]
            existing_ids = refactored_ids_list

        siemplify.LOGGER.info("Reading unprocessed incident data...")
        unprocessed_incident_data = read_content(
            siemplify=siemplify,
            file_name=UNPROCESSED_INCIDENT_FILE_NAME,
            db_key=UNPROCESSED_INCIDENT_DB_KEY,
        )

        siemplify.LOGGER.info(f"Connecting to {PROVIDER_NAME}..")
        rsa_manager = RSAManager(
            broker_api_root=broker_api_root,
            broker_username=broker_username,
            broker_password=broker_password,
            concentrator_api_root=concentrator_api_root,
            concentrator_username=concentrator_username,
            concentrator_password=concentrator_password,
            ui_api_root=ui_api_root,
            ui_username=ui_username,
            ui_password=ui_password,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )
        rsa_manager.test_connectivity()
        siemplify.LOGGER.info(f"Successfully connected to {PROVIDER_NAME}")

        siemplify.LOGGER.info("Fetching incidents since ...")

        if unprocessed_incident_data:
            filtered_alerts = [
                rsa_manager.parser.build_incident_object(
                    unprocessed_incident_data.get("incident", {})
                )
            ]
        else:
            filtered_alerts = rsa_manager.get_incidents(
                limit=max_reports_to_fetch,
                existing_ids=existing_ids,
                start_time=convert_datetime_to_string(
                    get_last_success_time(
                        siemplify=siemplify,
                        offset_with_metric={"hours": hours_backwards},
                    )
                ),
            )
        filtered_alerts = sorted(
            filtered_alerts, key=lambda filtered_alert: filtered_alert.created_ms
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} incidents")

        fetched_alerts = []
        ignored_alerts = []

        if is_test_run:
            siemplify.LOGGER.info(
                "This is a TEST run. Only 1 incident will be processed."
            )
            filtered_alerts = filtered_alerts[:1]

        for alert in filtered_alerts:
            try:
                if len(processed_alerts) >= max_reports_to_fetch:
                    # Provide slicing for the alerts amount.
                    siemplify.LOGGER.info(
                        "Reached max number of reports to fetch cycle. No more incidents will be processed in this cycle."
                    )
                    break

                siemplify.LOGGER.info(
                    f"Started processing incident {alert.id} - {alert.title}"
                )

                if is_approaching_timeout(connector_starting_time, script_timeout):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                if not pass_time_filter(
                    siemplify=siemplify,
                    alert=alert,
                    acceptable_time_threshold_minutes=INCIDENT_TIME_THRESHOLD_MINUTES,
                ):
                    siemplify.LOGGER.info(
                        f"Incident {alert.id} didn't pass time frame threshold filter of "
                        f"{INCIDENT_TIME_THRESHOLD_MINUTES} minutes. Skipping..."
                    )
                    continue

                # Update existing alerts
                existing_item = next(
                    (item for item in existing_ids if item.get("id", "") == alert.id),
                    None,
                )
                if existing_item:
                    existing_item["event_count"] = alert.event_count
                else:
                    existing_ids.append(
                        {"id": alert.id, "event_count": alert.event_count}
                    )

                fetched_alerts.append(alert)
                unprocessed_incident_alerts = (
                    rsa_manager.parser.build_alert_object_list(
                        unprocessed_incident_data
                    )
                )

                if not pass_whitelist_filter(
                    siemplify=siemplify,
                    whitelist_as_a_blacklist=whitelist_as_a_blacklist,
                    model=alert,
                    model_key="title",
                    whitelist=whitelist,
                ):
                    siemplify.LOGGER.info(
                        f"Incident {alert.id} did not pass whitelist filter skipping..."
                    )
                    ignored_alerts.append(alert)
                    continue

                if (
                    alert.risk_score is not None
                    and alert.risk_score < lowest_risk_score
                ):
                    siemplify.LOGGER.info(
                        f"Incident {alert.id} did not pass lowest risk score filter skipping..."
                    )
                    ignored_alerts.append(alert)
                    continue

                if (
                    alert.risk_score is None
                ):  # If risk score is not available, set it to severity fallback
                    siemplify.LOGGER.info(
                        f'Incident {alert.id} has no risk score. Using default Severity Fallback "{severity_fallback}"'
                    )
                    alert.risk_score = SEVERITY_MAP.get(severity_fallback, -1)

                siemplify.LOGGER.info(f"Fetching incident alerts")
                events = (
                    unprocessed_incident_alerts[:MAX_EVENTS_PER_ALERT]
                    if unprocessed_incident_alerts
                    else rsa_manager.get_incident_alerts(incident_id=alert.id)
                )
                siemplify.LOGGER.info(
                    f"Successfully fetched {len(events)} incident alerts"
                )

                if len(events) > MAX_EVENTS_PER_ALERT:
                    unprocessed_incident_data["incident"] = alert.to_json()
                    unprocessed_incident_data["items"] = [
                        event.to_json() for event in events
                    ]
                    siemplify.LOGGER.info(
                        f"Found Incident with alerts count more than {MAX_EVENTS_PER_ALERT}. "
                        f"Connector will gracefully exit and continue processing Incident {alert.id} "
                        f"during next iterations"
                    )
                    break

                # Fetch events additional data
                for event in events:
                    for entry in event.events:
                        entry.additional_data = rsa_manager.get_event_details(
                            event_source=entry.event_source,
                            event_source_id=entry.event_source_id,
                            custom_credentials=credentials_dict,
                        )

                # Limit number of siemplify events in a siemplify alert.
                # Incident alert can have multiple entries in the "events" list field, to enable event mapping we create
                # new event for each entry.
                siemplify_events = limit_events_per_siemplify_alert(
                    [
                        event.as_event(entry)
                        for event in events
                        for entry in event.events
                    ]
                )

                # Creating AlertInfos for an Incident alert
                environment_common = (
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify=siemplify,
                        environment_field_name=environment_field_name,
                        environment_regex_pattern=environment_regex_pattern,
                    )
                )
                alert_infos = [
                    alert.as_alert_info(events, environment_common)
                    for events in siemplify_events
                ]

                if unprocessed_incident_data.get("items"):
                    unprocessed_incident_data["items"] = unprocessed_incident_data[
                        "items"
                    ][MAX_EVENTS_PER_ALERT:]
                else:
                    unprocessed_incident_data = {}

                all_alerts.extend(alert_infos)
                non_overflowed_alert_infos = []

                for alert_info in alert_infos:
                    if not disable_overflow:
                        if is_overflowed(siemplify, alert_info, is_test_run):
                            siemplify.LOGGER.info(
                                f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}-{alert_info.device_product} found as overflow alert. Skipping."
                            )
                            # If is overflowed we should skip
                            continue

                    processed_alerts.append(alert_info)
                    non_overflowed_alert_infos.append(alert_info)

                siemplify.LOGGER.info(
                    f"{len(non_overflowed_alert_infos)} AlertInfos for Incident {alert.id} were created."
                )

            except RSAAuthenticationException as e:
                raise Exception(e)

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process incident {alert.id}")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(f"Finished processing incident {alert.id}")

        if not is_test_run:
            save_timestamp(
                siemplify=siemplify,
                alerts=fetched_alerts + ignored_alerts,
                timestamp_key="created_ms",
            )
            write_ids(siemplify, existing_ids)

        write_content(
            siemplify=siemplify,
            content_to_write=unprocessed_incident_data,
            file_name=UNPROCESSED_INCIDENT_FILE_NAME,
            db_key=UNPROCESSED_INCIDENT_DB_KEY,
        )

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {e}")
        siemplify.LOGGER.exception(e)

        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def pass_time_filter(
    siemplify: SiemplifyConnectorExecution,
    alert: datamodels.Incident,
    acceptable_time_threshold_minutes: int,
) -> bool:
    """
    Check if an incident passes time filter.
    :param siemplify: {SiemplifyConnectorExecution} Siemplify Connector Execution instance
    :param alert: {datamodels.Incident} Fetched alert
    :param acceptable_time_threshold_minutes: {int} Time threshold for alerts to pass time filter. Alerts that were created and detected
    less than the threshold will not pass the time filter
    :return: {bool} True if passed time filter, otherwise False
    """
    min_allowed_timestamp_threshold_in_milliseconds = (
        connector_starting_time
        - convert_minutes_to_milliseconds(acceptable_time_threshold_minutes)
    )
    if alert.created_ms > min_allowed_timestamp_threshold_in_milliseconds:
        siemplify.LOGGER.info(
            f"Alert did not pass time filter. Detected approximately {convert_milliseconds_to_minutes(connector_starting_time - alert.created_ms)} minutes ago."
        )
        return False
    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
