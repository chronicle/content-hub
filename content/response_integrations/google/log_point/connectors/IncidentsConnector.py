from __future__ import annotations
import sys

from ..core.exceptions import LogPointNotFoundException
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler
from ..core.LogPointManager import LogPointManager
from TIPCommon import (
    extract_connector_param,
    is_approaching_timeout,
    get_last_success_time,
    pass_whitelist_filter,
    save_timestamp,
    is_overflowed,
    write_ids,
    read_ids,
    UNIX_FORMAT,
    string_to_multi_value,
    unix_now,
)
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from EnvironmentCommon import GetEnvironmentCommonFactory
from ..core.consts import (
    INCIDENTS_CONNECTOR_SCRIPT_NAME,
    INCIDENT_RISK_LEVEL_MAPPING,
    LOW_RISK,
    CHART_STRING,
    EVENTS_LIMIT_PER_ALERT,
    STORED_IDS_LIMIT,
)

connector_starting_time = unix_now()

# CONSTANTS
MAX_INCIDENTS_TO_FETCH = 10
DEFAULT_TIME_FRAME = 1


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = INCIDENTS_CONNECTOR_SCRIPT_NAME
    processed_incidents = []
    fetched_incidents = []
    all_incidents = []

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    ip_address = extract_connector_param(
        siemplify, param_name="IP Address", is_mandatory=True
    )
    username = extract_connector_param(
        siemplify, param_name="Username", is_mandatory=True
    )
    secret = extract_connector_param(siemplify, param_name="Secret", is_mandatory=True)
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )
    ca_certificate_file = extract_connector_param(
        siemplify, param_name="CA Certificate File"
    )

    environment_field_name = extract_connector_param(
        siemplify, param_name="Environment Field Name", default_value=""
    )
    environment_regex_pattern = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern"
    )
    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )

    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Max Hours Backwards",
        input_type=int,
        default_value=DEFAULT_TIME_FRAME,
    )
    lowest_risk_level_to_fetch = extract_connector_param(
        siemplify, param_name="Lowest Risk To Fetch", default_value=LOW_RISK
    )
    incidents_fetch_limit = extract_connector_param(
        siemplify,
        param_name="Max Incidents To Fetch",
        input_type=int,
        default_value=MAX_INCIDENTS_TO_FETCH,
    )
    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use whitelist as a blacklist",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    user_filter = extract_connector_param(
        siemplify, param_name="User Filter", print_value=True
    )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        manager = LogPointManager(
            ip_address=ip_address,
            username=username,
            secret=secret,
            ca_certificate_file=ca_certificate_file,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
        )

        filtered_users = {}
        if user_filter:
            usernames = string_to_multi_value(
                string_value=user_filter, only_unique=True
            )
            users = {user.user_id: user.username for user in manager.get_users()}
            filtered_users = {
                key: value for key, value in users.items() if value in usernames
            }

            if not filtered_users:
                raise LogPointNotFoundException(
                    "None of the users provided in the parameter 'User Filter' were "
                    "found. Please check the spelling."
                )

            if len(filtered_users.items()) != len(usernames):
                for username in list(set(usernames) - set(filtered_users.values())):
                    siemplify.LOGGER.info(f"User {username} was not found.")

        # Read already existing alerts ids
        siemplify.LOGGER.info("Reading already existing alerts ids...")
        existing_ids = read_ids(siemplify)

        siemplify.LOGGER.info("Fetching incidents...")

        incidents = manager.get_incidents(
            start_time=int(
                get_last_success_time(
                    siemplify=siemplify,
                    offset_with_metric={"hours": hours_backwards},
                    time_format=UNIX_FORMAT,
                )
                / 1000
            ),
            end_time=int(unix_now() / 1000),
        )

        siemplify.LOGGER.info(f"Fetched {len(incidents)} incidents")

        for incident in incidents:
            siemplify.LOGGER.info("\n")
            try:
                if len(fetched_incidents) >= incidents_fetch_limit:
                    siemplify.LOGGER.info(
                        f"{len(fetched_incidents)} incidents were fetched. Stopping "
                        "the connector"
                    )
                    break

                if is_test_run and fetched_incidents:
                    siemplify.LOGGER.info(
                        "Maximum incidents limit(1) for test run reached!"
                    )
                    break

                if is_approaching_timeout(
                    connector_starting_time, python_process_timeout
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                siemplify.LOGGER.info(f"Started processing incident {incident.id}")

                all_incidents.append(incident)

                if incident.id in existing_ids:
                    siemplify.LOGGER.info(
                        f"Incident {incident.id} already fetched. Skipping..."
                    )
                    continue

                if not pass_whitelist_filter(
                    siemplify, whitelist_as_a_blacklist, incident, "alert_name"
                ):
                    continue

                if not pass_risk_filter(
                    siemplify, incident, lowest_risk_level_to_fetch
                ):
                    continue

                siemplify.LOGGER.info("Processing incident")

                if filtered_users and not pass_user_filter(
                    siemplify, incident, filtered_users.keys()
                ):
                    continue

                events = []
                if not incident.is_search_type():
                    try:
                        siemplify.LOGGER.info(
                            f"Incident type is {incident.type}. Loading events..."
                        )
                        main_events = manager.get_information_about_incident(
                            incident.id,
                            incident.incident_id,
                            incident.detection_timestamp,
                        )
                        if incident.query.count(CHART_STRING) == 1:
                            for event in main_events:
                                events.extend(
                                    manager.get_aggregated_events(
                                        incident.query, event, incident.time_range
                                    )
                                )
                                events.extend(event.participating_events)
                        else:
                            events.extend(main_events)

                            for event in main_events:
                                events.extend(event.participating_events)

                        siemplify.LOGGER.info(f"Loaded {len(events)} events")
                    except Exception as e:
                        siemplify.LOGGER.error(f'Failed to load events. Error is "{e}"')

                environment_common = (
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify=siemplify,
                        environment_field_name=environment_field_name,
                        environment_regex_pattern=environment_regex_pattern,
                    )
                )

                if len(events) > EVENTS_LIMIT_PER_ALERT:
                    alert_info_list = []
                    for event_chunk in [
                        events[x : x + EVENTS_LIMIT_PER_ALERT]
                        for x in range(0, len(events), EVENTS_LIMIT_PER_ALERT)
                    ]:
                        alert_info_list.append(
                            incident.get_alert_info(
                                AlertInfo(), environment_common, event_chunk
                            )
                        )
                else:
                    alert_info_list = [
                        incident.get_alert_info(AlertInfo(), environment_common, events)
                    ]

                alert_info = alert_info_list[0]
                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}-"
                        f"{alert_info.environment}-{alert_info.device_product} "
                        "found as overflow alert. Skipping."
                    )
                    # If is overflowed we should skip
                    continue

                fetched_incidents.append(incident)
                processed_incidents.extend(alert_info_list)
                siemplify.LOGGER.info(
                    f"Incident {incident.id} was created with {len(alert_info_list)} "
                    "cases."
                )

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process incident {incident.id}")
                siemplify.LOGGER.exception(e)
                if is_test_run:
                    raise
            siemplify.LOGGER.info("\n")

        if not is_test_run and all_incidents:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(
                siemplify,
                existing_ids + [incident.id for incident in all_incidents],
                stored_ids_limit=STORED_IDS_LIMIT,
            )
            save_timestamp(siemplify=siemplify, alerts=all_incidents)

    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {err}")
        siemplify.LOGGER.exception(err)
        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_incidents)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_incidents)


def pass_risk_filter(siemplify, incident, lowest_risk_level_to_fetch):
    filter_passed = INCIDENT_RISK_LEVEL_MAPPING.get(
        incident.risk_level.lower(), 100
    ) >= INCIDENT_RISK_LEVEL_MAPPING.get(lowest_risk_level_to_fetch.lower(), 0)
    if not filter_passed:
        siemplify.LOGGER.info(
            f"Incident {incident.id} with risk_level {incident.risk_level} did not "
            "pass risk filter"
        )
    return filter_passed


def pass_user_filter(siemplify, incident, user_ids):
    if incident.user_id not in user_ids:
        siemplify.LOGGER.info(
            f"Incident {incident.id} with user ID {incident.user_id} did not pass user "
            "filter"
        )
        return False

    return True


if __name__ == "__main__":
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
