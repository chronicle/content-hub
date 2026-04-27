from __future__ import annotations
import sys
from datetime import timedelta

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler, convert_string_to_datetime
from ..core.SymantecATPManager import SymantecATPManager
from EnvironmentCommon import GetEnvironmentCommonFactory
from TIPCommon import (
    extract_connector_param,
    utc_now,
    unix_now,
    convert_comma_separated_to_list,
    read_ids,
    filter_old_alerts,
    is_approaching_timeout,
    write_ids,
    validate_timestamp,
    siemplify_fetch_timestamp,
    siemplify_save_timestamp,
)

from ..core.validators import SymantecATPValidator
from ..core.constants import (
    INCIDENTS_CONNECTOR_NAME,
    WHITELIST_FILTER,
    BLACKLIST_FILTER,
    ATP_QUERIES_TIME_FORMAT,
    ACCEPTABLE_TIME_INTERVAL_IN_MINUTES,
    ALERT_ID_FIELD,
    LIMIT_IDS_IN_IDS_FILE,
)


@output_handler
def main(is_test_run):
    connector_starting_time = unix_now()
    incidents = []
    all_incidents = []
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = INCIDENTS_CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button" "Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("==================== Main - Param Init ====================")

    environment = extract_connector_param(
        siemplify,
        param_name="Environment Field Name",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    environment_regex = extract_connector_param(
        siemplify,
        param_name="Environment Regex Pattern",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    api_root = extract_connector_param(
        siemplify,
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    client_id = extract_connector_param(
        siemplify,
        param_name="Client ID",
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )

    client_secret = extract_connector_param(
        siemplify,
        param_name="Client Secret",
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )

    priorities_str = extract_connector_param(
        siemplify,
        param_name="Priority Filter",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    offset_hours = extract_connector_param(
        siemplify,
        param_name="Fetch Max Hours Backwards",
        input_type=int,
        is_mandatory=False,
        print_value=True,
    )

    limit = extract_connector_param(
        siemplify,
        param_name="Max Incidents To Fetch",
        input_type=int,
        is_mandatory=False,
        print_value=True,
    )

    whitelist_as_blacklist = extract_connector_param(
        siemplify,
        param_name="Use whitelist as a blacklist",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Use SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )

    priorities = convert_comma_separated_to_list(priorities_str)
    SymantecATPValidator.validate_priorities(priorities)
    whitelist_as_blacklist = (
        BLACKLIST_FILTER if whitelist_as_blacklist else WHITELIST_FILTER
    )

    siemplify.LOGGER.info("------------------- Main - Started -------------------")

    environment_common = GetEnvironmentCommonFactory.create_environment_manager(
        siemplify=siemplify,
        environment_field_name=environment,
        environment_regex_pattern=environment_regex,
    )

    if is_test_run:
        siemplify.LOGGER.info("This is a test run. Ignoring stored timestamps")
        last_success_time_datetime = validate_timestamp(
            utc_now() - timedelta(hours=offset_hours), offset_hours
        )
    else:
        last_success_time_datetime = validate_timestamp(
            siemplify_fetch_timestamp(siemplify, datetime_format=True), offset_hours
        )

    # Read already existing alerts ids
    existing_ids = read_ids(siemplify=siemplify)

    try:
        client = SymantecATPManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
        )

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            limit = 1

        fetched_incidents = client.get_incidents(
            priorities=priorities,
            last_event_seen=last_success_time_datetime,
            limit=limit,
        )

        siemplify.LOGGER.info(
            f"{len(fetched_incidents)} incidents were fetched from timestamp {last_success_time_datetime}"
        )

        filtered_incidents = filter_old_alerts(
            siemplify=siemplify,
            alerts=fetched_incidents,
            existing_ids=existing_ids,
            id_key=ALERT_ID_FIELD,
        )
        siemplify.LOGGER.info(
            f"Found {len(filtered_incidents)} new incidents in since {last_success_time_datetime.isoformat()}."
        )
        filtered_incidents = [
            client.fetch_events_for_incident(incident)
            for incident in filtered_incidents
        ]
        filtered_incidents = sorted(
            filtered_incidents, key=lambda inc: inc.last_event_seen
        )
    except Exception as e:
        siemplify.LOGGER.error(str(e))
        siemplify.LOGGER.exception(e)
        sys.exit(1)

    for incident in filtered_incidents:
        try:
            if is_approaching_timeout(
                python_process_timeout=python_process_timeout,
                connector_starting_time=connector_starting_time,
            ):
                siemplify.LOGGER.info(
                    "Timeout is approaching. Connector will gracefully exit."
                )
                break

            if len(incidents) >= limit:
                siemplify.LOGGER.info(f"Stop processing alerts, limit {limit} reached")
                break

            siemplify.LOGGER.info(f"Processing incident {incident.uuid}")

            if not incident.pass_time_filter():
                siemplify.LOGGER.info(
                    f"Incident {incident.uuid} is newer than {ACCEPTABLE_TIME_INTERVAL_IN_MINUTES} minutes. Stopping connector..."
                )
                # Breaking connector loop because next incident can pass acceptable time
                # and we can lose incidents that did not pass before in one loop
                break

            all_incidents.append(incident)
            existing_ids.append(incident.uuid)

            if not incident.pass_whitelist_or_blacklist_filter(
                siemplify.whitelist, whitelist_as_blacklist
            ):
                siemplify.LOGGER.info(
                    f"Incident with id: {incident.uuid} and name: {incident.rule_name} did not pass {whitelist_as_blacklist} filter. Skipping..."
                )
                continue

            is_overflowed = False
            siemplify.LOGGER.info(
                f"Started creating Alert {incident.uuid}", alert_id=incident.uuid
            )
            incident_info = incident.to_alert(environment_common)
            siemplify.LOGGER.info(
                f"Finished creating Alert {incident.uuid}", alert_id=incident.uuid
            )

            try:
                is_overflowed = siemplify.is_overflowed_alert(
                    environment=incident_info.environment,
                    alert_identifier=incident_info.ticket_id,
                    alert_name=incident_info.rule_generator,
                    product=incident_info.device_product,
                )

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Error validation connector overflow, ERROR: {e}"
                )
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            if is_overflowed:
                siemplify.LOGGER.info(
                    f"{incident_info.rule_generator}-{incident_info.ticket_id}-{incident_info.environment}-{incident_info.device_product} found as overflow alert. Skipping."
                )
                continue
            else:
                incidents.append(incident_info)
                siemplify.LOGGER.info(f"Incident {incident.uuid} was created.")

        except Exception as e:
            siemplify.LOGGER.error(
                f"Failed to process incident {incident.uuid}", alert_id=incident.uuid
            )
            siemplify.LOGGER.exception(e)

            if is_test_run:
                raise

    if not is_test_run:
        if all_incidents:
            new_timestamp = convert_string_to_datetime(
                all_incidents[-1].last_event_seen
            )
            siemplify_save_timestamp(siemplify=siemplify, new_timestamp=new_timestamp)
            siemplify.LOGGER.info(
                f"New timestamp {new_timestamp.strftime(ATP_QUERIES_TIME_FORMAT)} has been saved"
            )

        write_ids(
            siemplify=siemplify,
            ids=existing_ids,
            stored_ids_limit=LIMIT_IDS_IN_IDS_FILE,
        )

    siemplify.LOGGER.info(
        f"Incidents Processed: {len(incidents)} of {len(all_incidents)}"
    )
    siemplify.LOGGER.info(f"Created total of {len(incidents)} incidents")

    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(incidents)


if __name__ == "__main__":
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
