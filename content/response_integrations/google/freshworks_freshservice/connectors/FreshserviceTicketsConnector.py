from __future__ import annotations
import sys

from EnvironmentCommon import GetEnvironmentCommonFactory
from ..core.FreshworksFreshserviceManager import FreshworksFreshserviceManager
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import (
    read_ids,
    write_ids,
    get_last_success_time,
    is_approaching_timeout,
    is_overflowed,
    save_timestamp,
    pass_whitelist_filter,
    extract_connector_param,
    WHITELIST_FILTER,
    BLACKLIST_FILTER,
    unix_now,
)
from ..core.consts import (
    TICKETS_CONNECTOR_NAME,
    DEFAULT_TIME_FRAME,
    TICKET_PRIORITIES,
    TICKET_STATUSES,
    MINIMUM_TICKET_PRIORITIES,
    MINIMUM_PRIORITY_TO_FETCH_DEFAULT_VALUE,
    MAX_TICKETS_PER_CYCLE_DEFAULT_VALUE,
    PARAMETERS_DEFAULT_DELIMITER,
    TICKETS_CONNECTOR_SUPPORTED_TICKET_TYPES,
    MAPPED_TICKET_PRIORITIES,
    MAPPED_TICKET_STATUSES,
    DATE_FORMAT,
    STORED_IDS_LIMIT,
)
from ..core.exceptions import FreshworksFreshserviceTicketsConnectorError
from ..core.utils import load_csv_to_list

CONNECTOR_STARTING_TIME = unix_now()


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = TICKETS_CONNECTOR_NAME
    processed_alerts = []
    fetched_alerts = []
    overflowed = 0

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("=================== Main - Param Init ===================")

    api_root = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True, print_value=True
    )
    api_key = extract_connector_param(
        siemplify,
        param_name="API Key",
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=False,
        default_value=True,
        print_value=True,
    )
    environment_field_name = extract_connector_param(
        siemplify,
        param_name="Environment Field Name",
        default_value="",
        print_value=True,
    )
    environment_regex_pattern = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern", print_value=True
    )
    script_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        is_mandatory=True,
        input_type=int,
        default_value=300,
        print_value=True,
    )
    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Offset time in hours",
        input_type=int,
        default_value=DEFAULT_TIME_FRAME,
        print_value=True,
    )
    minimum_priority_to_fetch = extract_connector_param(
        siemplify,
        param_name="Minimum Priority to Fetch",
        is_mandatory=False,
        default_value=MINIMUM_PRIORITY_TO_FETCH_DEFAULT_VALUE,
        print_value=True,
    )
    minimum_priority_to_fetch = minimum_priority_to_fetch.strip()
    max_tickets_per_cycle = extract_connector_param(
        siemplify,
        param_name="Max Tickets Per Cycle",
        input_type=int,
        default_value=MAX_TICKETS_PER_CYCLE_DEFAULT_VALUE,
        print_value=True,
    )
    tickets_status_to_fetch = extract_connector_param(
        siemplify,
        param_name="Tickets Status to Fetch",
        is_mandatory=False,
        print_value=True,
    )
    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        "Use dynamic list as a blocklist",
        is_mandatory=True,
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    workspace_id = extract_connector_param(
        siemplify,
        param_name="Workspace ID",
        print_value=True,
    )

    whitelist_filter_type = (
        BLACKLIST_FILTER if whitelist_as_a_blacklist else WHITELIST_FILTER
    )
    whitelist = (
        siemplify.whitelist
        if isinstance(siemplify.whitelist, list)
        else [siemplify.whitelist]
    )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        # validate minimum ticket priority to fetch
        if minimum_priority_to_fetch not in TICKET_PRIORITIES:
            raise FreshworksFreshserviceTicketsConnectorError(
                "Invalid values provided for 'Minimum Priority to Fetch' parameter."
                " Possible values are:"
                f" {PARAMETERS_DEFAULT_DELIMITER.join(TICKET_PRIORITIES)}."
            )

        # validate ticket statuses
        if tickets_status_to_fetch:
            tickets_status_to_fetch = load_csv_to_list(
                tickets_status_to_fetch, "Tickets Status to Fetch"
            )
            invalid_statuses = [
                status
                for status in tickets_status_to_fetch
                if status not in TICKET_STATUSES
            ]
            if invalid_statuses:
                raise FreshworksFreshserviceTicketsConnectorError(
                    "Following values are invalid for the"
                    "'Tickets Status to Fetch' parameter: "
                    f"{PARAMETERS_DEFAULT_DELIMITER.join(invalid_statuses)}."
                    " Possible values are: "
                    f"{PARAMETERS_DEFAULT_DELIMITER.join(TICKET_STATUSES)}"
                )

        # validate whitelist
        if whitelist:
            invalid_ticket_types = (
                type
                for type in whitelist
                if type.strip() not in TICKETS_CONNECTOR_SUPPORTED_TICKET_TYPES
            )
            if any(True for _ in invalid_ticket_types):
                invalid_ticket_types = list(invalid_ticket_types)
                ticket_con_supp_ticket_type = TICKETS_CONNECTOR_SUPPORTED_TICKET_TYPES
                raise FreshworksFreshserviceTicketsConnectorError(
                    f"Following values are invalid for the whitelist: "
                    f"{PARAMETERS_DEFAULT_DELIMITER.join(invalid_ticket_types)}."
                    " Possible values are: "
                    f"{PARAMETERS_DEFAULT_DELIMITER.join(ticket_con_supp_ticket_type)}"
                )
            if whitelist_as_a_blacklist and set(
                TICKETS_CONNECTOR_SUPPORTED_TICKET_TYPES
            ).issubset(whitelist):
                raise FreshworksFreshserviceTicketsConnectorError(
                    "All supported ticket types are blacklisted. "
                    "No alerts will be ingested."
                )

        if max_tickets_per_cycle <= 0:
            siemplify.LOGGER.info(
                "'Max Tickets Per Cycle' must be positive."
                f"The default value {MAX_TICKETS_PER_CYCLE_DEFAULT_VALUE} will be used"
            )
            max_tickets_per_cycle = MAX_TICKETS_PER_CYCLE_DEFAULT_VALUE

        if hours_backwards < 0:
            siemplify.LOGGER.info(
                "Max Hours Backwards must be non-negative. "
                f"The default value {DEFAULT_TIME_FRAME} will be used"
            )
            hours_backwards = DEFAULT_TIME_FRAME

        # Read already existing alerts ids
        existing_ids = read_ids(siemplify)
        siemplify.LOGGER.info(f"Successfully loaded {len(existing_ids)} existing ids")

        manager = FreshworksFreshserviceManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        filtered_alerts = manager.get_tickets(
            existing_ids=existing_ids,
            limit=max_tickets_per_cycle,
            updated_since=get_last_success_time(
                siemplify=siemplify, offset_with_metric={"hours": hours_backwards}
            ).strftime(DATE_FORMAT),
            ticket_type=(
                whitelist[0]
                if isinstance(whitelist, list)
                and len(whitelist) == 1
                and whitelist_filter_type == WHITELIST_FILTER
                else None
            ),
            workspace_id=workspace_id,
        )

        siemplify.LOGGER.info(f"Fetched {len(filtered_alerts)} alerts")

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            filtered_alerts = filtered_alerts[:1]

        departments, fetched_departments = [], False
        agent_groups, fetched_agent_groups = [], False
        responders, fetched_responders = [], False
        locations, fetched_locations = [], False

        for alert in filtered_alerts:
            try:
                if is_approaching_timeout(
                    python_process_timeout=script_timeout,
                    connector_starting_time=CONNECTOR_STARTING_TIME,
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                if len(processed_alerts) >= max_tickets_per_cycle:
                    # Provide slicing for the alerts amount.
                    siemplify.LOGGER.info(
                        "Reached max number of alerts cycle. No more alerts will be processed in this cycle."
                    )
                    break

                siemplify.LOGGER.info(
                    f"Started processing alert {alert.id} - {alert.subject}"
                )

                # Check if already processed
                if alert.id in existing_ids:
                    siemplify.LOGGER.info(
                        f"Alert {alert.id} skipped since it has been fetched before"
                    )
                    fetched_alerts.append(alert)
                    continue

                # Update existing alerts
                existing_ids.append(alert.id)
                fetched_alerts.append(alert)

                # Check if alert passes filters
                if not pass_filters(
                    siemplify,
                    whitelist,
                    whitelist_as_a_blacklist,
                    alert,
                    "type",
                    minimum_priority_to_fetch,
                    tickets_status_to_fetch,
                ):
                    continue

                (
                    department_name,
                    agent_group_name,
                    responder,
                    responder_email,
                    responder_location_name,
                ) = (None, None, None, None, None)

                # Look up for department name
                if alert.department_id is not None:
                    if not fetched_departments:
                        siemplify.LOGGER.info("Fetching departments..")
                        fetched_departments = True
                        try:
                            departments = manager.get_departments()
                        except Exception as error:
                            siemplify.LOGGER.error(
                                f"Failed to list departments. Error is: {error}"
                            )
                            siemplify.LOGGER.exception(error)

                    if departments and isinstance(departments, list):
                        department_name = [
                            department.name
                            for department in departments
                            if alert.department_id == department.id
                        ]
                        department_name = (
                            department_name[0] if department_name else None
                        )

                # Look up for agent group name
                if alert.group_id is not None:
                    if not fetched_agent_groups:
                        siemplify.LOGGER.info("Fetching agent groups..")
                        fetched_agent_groups = True
                        try:
                            agent_groups = manager.get_agent_groups()
                        except Exception as error:
                            siemplify.LOGGER.error(
                                f"Failed to list agent groups. Error is: {error}"
                            )
                            siemplify.LOGGER.exception(error)

                    if agent_groups and isinstance(agent_groups, list):
                        agent_group_name = [
                            group.name
                            for group in agent_groups
                            if alert.group_id == group.id
                        ]
                        agent_group_name = (
                            agent_group_name[0] if agent_group_name else None
                        )

                # Look up for responder name
                if alert.responder_id is not None:
                    if not fetched_responders:
                        siemplify.LOGGER.info("Fetching agents..")
                        fetched_responders = True
                        try:
                            responders = manager.get_agents()
                        except Exception as error:
                            siemplify.LOGGER.error(
                                f"Failed to list agents. Error is: {error}"
                            )
                            siemplify.LOGGER.exception(error)

                    if responders and isinstance(responders, list):
                        responder = [
                            responder
                            for responder in responders
                            if alert.responder_id == responder.agent_id
                        ]
                        responder = responder[0] if responder else None
                        responder_email = (
                            responder.email if responder and responder.email else None
                        )

                # Lookup responder's location name
                if responder and responder.location_id is not None:
                    if not fetched_locations:
                        siemplify.LOGGER.info(f"Fetching locations..")
                        fetched_locations = True
                        try:
                            locations = manager.get_locations()
                        except Exception as error:
                            siemplify.LOGGER.error(
                                f"Failed to list locations. Error is: {error}"
                            )
                            siemplify.LOGGER.exception(error)
                    if locations and isinstance(locations, list):
                        responder_location_name = [
                            location.name
                            for location in locations
                            if location.id == responder.location_id
                        ]
                        responder_location_name = (
                            responder_location_name[0]
                            if responder_location_name
                            else None
                        )

                environment_common = (
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify=siemplify,
                        environment_regex_pattern=environment_regex_pattern,
                        environment_field_name=environment_field_name,
                    )
                )

                alert_info = alert.get_alert_info(
                    AlertInfo(),
                    environment_common,
                    department_name,
                    agent_group_name,
                    responder_email,
                    responder_location_name,
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}"
                        f"-{alert_info.environment}-{alert_info.device_product}"
                        " found as overflow alert. Skipping..."
                    )
                    # If is overflowed we should skip
                    overflowed += 1
                    continue

                processed_alerts.append(alert_info)
                siemplify.LOGGER.info(f"Alert '{alert.id}' was created.")

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process alert {alert.id}")
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(f"Finished processing alert {alert.id}")

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(siemplify, existing_ids, stored_ids_limit=STORED_IDS_LIMIT)
            save_timestamp(
                siemplify=siemplify,
                alerts=fetched_alerts,
                timestamp_key="updated_at_unix",
            )

        siemplify.LOGGER.info(
            f"Alerts processed: {len(processed_alerts)} out of {len(fetched_alerts)}"
            f" (Overflowed: {overflowed})"
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
    whitelist,
    whitelist_as_a_blacklist,
    alert,
    model_key,
    minimum_priority_to_fetch,
    tickets_status_to_fetch,
):
    """
    Filters an alert based on whitelist, priority, and status criteria.

    Parameters:
    siemplify (object): The Siemplify integration object.
    whitelist (list): List of whitelisted items.
    whitelist_as_a_blacklist (bool): Whether to treat the whitelist as a blacklist.
    alert (object): The alert object containing alert details.
    model_key (str): The key to the model being used.
    minimum_priority_to_fetch (int): The minimum priority of alerts to fetch.
    tickets_status_to_fetch (list): List of ticket statuses to fetch.

    Returns:
    bool: True if the alert passes all filters, False otherwise.
    """
    # filter alert by whitelist logic
    if not pass_whitelist_filter(
        siemplify, whitelist_as_a_blacklist, alert, model_key, whitelist
    ):
        return False

    # filter alert by ticket priority
    ticket_priority = MAPPED_TICKET_PRIORITIES.get(alert.priority, -1)
    if (
        alert.priority
        and minimum_priority_to_fetch
        and (
            ticket_priority not in MINIMUM_TICKET_PRIORITIES[minimum_priority_to_fetch]
        )
    ):
        siemplify.LOGGER.info(
            f"Alert with id: '{alert.id}' (priority: {ticket_priority})"
            " did not pass ticket priority filter. Skipping..."
        )
        return False

    # filter alert by ticket status
    ticket_status = MAPPED_TICKET_STATUSES.get(alert.status, -1)
    if (
        alert.status
        and tickets_status_to_fetch
        and (ticket_status not in tickets_status_to_fetch)
    ):
        siemplify.LOGGER.info(
            f"Alert with id: '{alert.id}' (status: {ticket_status})"
            " did not pass ticket status filter. Skipping..."
        )
        return False

    return True


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
