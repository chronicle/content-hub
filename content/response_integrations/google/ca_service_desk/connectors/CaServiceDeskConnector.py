from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# -*- coding: utf-8 -*-
# ==============================================================================
# title           :.py
# description     :This is CA Desk Manager Connector.
# author          :victor@siemplify.co
# date            :01-11-18
# python_version  :2.7
# libraries       : import CaSoapManager, SiemplifyConnectors, uuid, datetime, logging, urllib3, requests, pytz
# requirements    :
# product_version : 1.0
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from ..core.CaSoapManager import CaSoapManager
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import CaseInfo
import logging
import json
import os
import uuid
import sys


# =====================================
#              FILTERS                #
# =====================================
NOT_FORM_USER_FILTER = []
CATEGORIES_FILTER = []
GROUPS_FILTER = []

# =====================================
#             CONSTANTS               #
# =====================================
# Configurations.
DONE_INCIDENTS_FILE_NAME = "CA_DESK_MANAGER_INCIDENTS_IDS.json"
# Consts.
VENDOR = "CA Corp."
PRODUCT = "CA Desk Manager"
CASES_RULE = "CA Desk Manager Ticket."

# Formats.
CASE_NAME_FORMAT = "CA Desk Manager Incident: {0}"  # {0} Incident ID.

MAX_INCIDENTS_TO_FETCH = 1000


# =====================================
#              CLASSES                #
# =====================================
def create_event_for_case(ticket_data, start_time_field, end_time_field):
    """
    From a Siemplify event for a Ca incident id.
    :param ticket_data: {dict}
    :param start_time_field: the string that represent the key of the start time at the event {string}
    :param end_time_field: the string that represent the key of the end time at the event {string}
    :return: Siemplify event {dict}
    """
    result_event = {}
    # Set event product.
    result_event["device_product"] = PRODUCT

    # Set event vendor.
    result_event["device_vendor"] = VENDOR

    # Set event times.
    # '000' added because the time at the ticket comes in seconds but milliseconds needed.
    result_event["StartTime"] = ticket_data[start_time_field] + "000"
    # '000' added because the time at the ticket comes in seconds but milliseconds needed.
    result_event["EndTime"] = ticket_data[end_time_field] + "000"

    # Inject all the rest ticket data parameters.
    for key, val in ticket_data.items():
        if val:
            result_event[str(key)] = str(val).encode("utf-8")
        else:
            result_event[str(key)] = "None"
    # Return result event.
    return result_event


def create_case_package(
    event, category_default_field, category_fallback_field, id_field, environment
):
    """
    Create case package object.
    :param event: event data dictionary {dict}
    :param category_default_field: string that represent the category key at the event dict {string}
    :param category_fallback_field: category field fallback {string}
    :param id_field: incident id field key as it appear at the ticket JSON {string}
    :param environment: connector environment, fetched from connector parameters {string}
    :return: case object {case obj}
    """
    case_info = CaseInfo()

    # Set alert name.
    if category_default_field in list(event.keys()):
        alert_name = f"{event[id_field]}_{event[category_default_field]}"
    elif category_fallback_field in list(event.keys()):
        alert_name = f"{event[id_field]}_{event[category_fallback_field]}"
    else:
        raise Exception(
            f'No mandatory field for "Category" in event, for event with id: {event[id_field]}'
        )

    case_info.name = alert_name

    # Set case environment.
    case_info.environment = environment

    # Set case product.
    case_info.device_product = PRODUCT
    # Set case vendor.
    case_info.device_vendor = VENDOR

    # Set case time.
    case_info.start_time = event.get("StartTime", 1)
    case_info.end_time = event.get("EndTime", 1)

    # Set case rule.
    case_info.rule_generator = CASES_RULE

    # Set case name.
    case_info.name = CASE_NAME_FORMAT.format(event.get(id_field, "No event in case."))

    # Set case ticket id.
    case_info.ticket_id = event.get(id_field, "No event in case.")

    case_info.display_id = event.get(id_field, str(uuid.uuid4()))

    # Set case unique identifier.
    case_info.identifier = str(uuid.uuid4())

    # Set case priority.
    case_info.priority = 60  # 60 will be translated to medium in Siemplify.

    # Set case's event.
    case_info.events = [event]

    return case_info


def filter_done_incidents(incident_ids, done_incidents_file_path):
    """
    Pop ids of done incidents from the given incident ids list.
    :param incident_ids: list of incident ids {list}
    :param done_incidents_file_path: the path of the file which stores the done incidents ids {string}
    :return: ids that did not appeared {list}
    """
    if not os.path.exists(done_incidents_file_path):
        done_ids = []
    else:
        with open(done_incidents_file_path, "r+") as incident_ids_vault:
            done_ids = json.loads(incident_ids_vault.read())

    return [incident_id for incident_id in incident_ids if incident_id not in done_ids]


def validate_file_dir_exists(file_path):
    """
    Validate that file dir exists else create it.
    :param file_path: file path to check {string}
    :return: {void}
    """
    file_directory = os.path.dirname(file_path)
    if not os.path.exists(file_directory):
        os.mkdir(file_directory)


def mark_done_incidents(incident_ids, done_incident_ids_file_name):
    """
    Save ids of the incidents that were already fetched.
    :param incident_ids: list of incident ids {list}
    :param done_incident_ids_file_name: json file which stores the ids of the done incidents {string}
    :return: {void}
    """
    file_path = done_incident_ids_file_name

    validate_file_dir_exists(file_path)

    if not os.path.exists(file_path):
        done_ids = []
    else:
        with open(file_path, "r+") as incident_ids_vault:
            done_ids = json.loads(incident_ids_vault.read())

    incidents = list(set().union(done_ids, incident_ids))
    incidents = sorted(incidents)[-MAX_INCIDENTS_TO_FETCH:]

    with open(file_path, "w+") as incident_ids_vault:
        incident_ids_vault.write(json.dumps(incidents))


@output_handler
def main():
    connector_scope = SiemplifyConnectorExecution()
    try:
        # Define variables
        connector_scope.LOGGER.info(
            "--------------- CONNECTOR ITERATION STARTED ---------------"
        )
        done_incident_ids_file_path = (
            rf"{connector_scope.run_folder}/{DONE_INCIDENTS_FILE_NAME}"
        )
        incident_ids = []  # The list collects all relevant ticket ids.
        cases = []
        output_variables = {}
        log_items = []

        # Parameters
        # Credentials
        api_root = connector_scope.parameters.get("API Root")
        username = connector_scope.parameters.get("Username")
        password = connector_scope.parameters.get("Password")

        # Fields
        ticket_id_field = connector_scope.parameters.get("Ticket ID Field", "ref_num")
        start_time_field = connector_scope.parameters.get(
            "Start Time Field", "open_date"
        )
        end_time_field = connector_scope.parameters.get("End Time Field", "last_mod_dt")
        category_default_field = connector_scope.parameters.get(
            "Category Default Field", "category"
        )
        category_fallback_field = connector_scope.parameters.get(
            "Category Fallback Field", "category.sym"
        )
        user_id_field = connector_scope.parameters.get(
            "User ID Field", "customer.userid"
        )
        ticket_fields_str = connector_scope.parameters.get("Ticket Fields")

        # Filters
        not_from_user_filter_str = connector_scope.parameters.get(
            "List Of Users To Ignore", None
        )
        categories_filter_str = connector_scope.parameters.get("Categories List", None)
        groups_filers_str = connector_scope.parameters.get("Groups List", None)

        connector_scope.LOGGER.info("All parameters had been received.")

        # Convert string params to list.
        ticket_fields = ticket_fields_str.split(",") if ticket_fields_str else []

        # Verify optional fields.
        not_from_user_filter = (
            not_from_user_filter_str.split(",") if not_from_user_filter_str else []
        )
        categories_filter = (
            categories_filter_str.split(",") if categories_filter_str else []
        )
        groups_filers = groups_filers_str.split(",") if groups_filers_str else []

        # Define CA Desk Manager instance.
        try:
            ca_manager = CaSoapManager(api_root, username, password)
            connector_scope.LOGGER.info("Initiated CA Desk Manager instance.")
        except Exception as err:
            connector_scope.LOGGER.error(f"Connection Error Occurred, ERROR: {err}")
            connector_scope.LOGGER._log.exception(err)
            raise

        # Get last connector successful run.
        last_run_time = connector_scope.fetch_timestamp(datetime_format=False)
        connector_scope.LOGGER.info(f"Got last successful run: {str(last_run_time)}")

        # Get incident ids since last run time by filters.
        # Get incidents by groups.
        if groups_filers:
            for group in groups_filers:
                connector_scope.LOGGER.info(
                    f'Getting incidents for group: {group.encode("utf-8")}'
                )
                try:
                    incident_ids.extend(
                        ca_manager.get_incident_ids_by_filter(
                            last_modification_unixtime_milliseconds=last_run_time,
                            group_filter=str(group).encode("utf-8"),
                        )
                    )
                except Exception as err:
                    connector_scope.LOGGER.error(
                        f"Error fetching tickets for group {group}, ERROR: {err}"
                    )
                    connector_scope.LOGGER._log.exception(err)

            connector_scope.LOGGER.info(
                f"Found {str(len(incident_ids))} for groups, the ids are: {str(incident_ids)}"
            )
        # Get incidents by categories.
        elif categories_filter:
            connector_scope.LOGGER.info(
                f"--- Get incidents by categories: {str(categories_filter)} ---"
            )
            for category in categories_filter:
                connector_scope.LOGGER.info(
                    f"Getting incidents for category: {category}"
                )
                try:
                    incident_ids.extend(
                        ca_manager.get_incident_ids_by_filter(
                            last_modification_unixtime_milliseconds=last_run_time,
                            area_filter=category,
                        )
                    )
                except Exception as err:
                    connector_scope.LOGGER.error(
                        f"Error fetching tickets for category {category}, ERROR: {err}"
                    )
                    connector_scope.LOGGER._log.exception(err)
            connector_scope.LOGGER.info(
                f"Found {str(len(incident_ids))} for categories, the ids are: {str(incident_ids)}"
            )
        else:
            connector_scope.LOGGER.info(
                "--- Get incidents by last run time(No filters were  inserted)"
            )
            try:
                incident_ids.extend(
                    ca_manager.get_incident_ids_by_filter(
                        last_modification_unixtime_milliseconds=last_run_time
                    )
                )
            except Exception as err:
                connector_scope.LOGGER.error(
                    f"Error fetching tickets by last run time, ERROR: {err}"
                )
                connector_scope.LOGGER._log.exception(err)

            connector_scope.LOGGER.info(
                f"Found {str(len(incident_ids))} since last run time, the ids are: {str(incident_ids)}"
            )

        # Filter out already done incidents
        try:
            incident_ids = filter_done_incidents(
                incident_ids, done_incident_ids_file_path
            )
        except Exception as err:
            connector_scope.LOGGER.error(f"Error filtering ticket ids, ERROR: {err}")
            connector_scope.LOGGER._log.exception(err)

        # Unify ids list.
        connector_scope.LOGGER.info("Unify ids list.")
        unique_incident_ids = list(set(incident_ids))
        connector_scope.LOGGER.info(f"Unified ids list is: {str(unique_incident_ids)}")

        # Get incidents data and produce it to cases.
        for incident_id in unique_incident_ids:
            connector_scope.LOGGER.info(
                f"Getting data for incident with id: {incident_id}"
            )
            try:
                ticket_data = ca_manager.get_incident_by_id(incident_id, ticket_fields)
                connector_scope.LOGGER.info(f"Got data for incident: {incident_id}")
            except Exception as err:
                connector_scope.LOGGER.error(
                    f"Error fetching ticket data for incident with id: {incident_id}, ERROR: {err}"
                )
                connector_scope.LOGGER._log.exception(err)
                ticket_data = {}

            # Verify User Filter in order to exclude tickets that were created by Siemplify system.
            connector_scope.LOGGER.info(
                f"Check if creator is in users filter: {str(not_from_user_filter)}"
            )

            if (
                ticket_data.get(user_id_field)
                and not ticket_data.get(user_id_field) in not_from_user_filter
            ):
                # Build Siemplify event.
                connector_scope.LOGGER.info("Build event for incident.")
                try:
                    event = create_event_for_case(
                        ticket_data, start_time_field, end_time_field
                    )
                except Exception as err:
                    connector_scope.LOGGER.error(
                        f"Error creating an event for incident with id: {incident_id}"
                    )
                    connector_scope.LOGGER._log.exception(err)
                    # If not event created, return an empty event.
                    event = {}

                # Add to an event number of attachments.
                connector_scope.LOGGER.info(
                    f"Get attachments for incident with id: {incident_id}"
                )
                try:
                    incidents_attachments_count = len(
                        ca_manager.get_incident_attachments(incident_id)
                    )
                    connector_scope.LOGGER.info(
                        f"Got {incidents_attachments_count} attachment for  for incident with id: {incidents_attachments_count}"
                    )
                    event["attachments_count"] = incidents_attachments_count
                except Exception as err:
                    connector_scope.LOGGER.error(
                        f"Error fetching attachments for incident with id:{incident_id}, Error:{err}"
                    )
                    connector_scope.LOGGER._log.exception(err)

                # Add incident properties to event.
                connector_scope.LOGGER.info(
                    f"Get properties for incident with id: {incident_id}"
                )
                try:
                    incident_properties = ca_manager.get_incident_properties(
                        incident_id
                    )
                    for counter, property in enumerate(incident_properties):
                        prop_key = f"prop_{counter}"
                        if property.get("Name"):
                            event[prop_key] = (
                                f"{str(property.get('Value', 'None')).encode('utf-8')}:{str(property['Name']).encode('utf-8')}"
                            )
                    connector_scope.LOGGER.info(
                        f"Got properties for incident with id:{incident_id}"
                    )
                except Exception as err:
                    connector_scope.LOGGER.error(
                        f"Error fetching properties for incident with id: {incident_id}, Error: {err}"
                    )
                    connector_scope.LOGGER._log.exception(err)

                connector_scope.LOGGER.info(f"Built event for incident: {incident_id}")

                # create case package and append it to case list.
                connector_scope.LOGGER.info("Creating case package.")

                # Create case object.
                case = create_case_package(
                    event,
                    category_default_field,
                    category_fallback_field,
                    ticket_id_field,
                    connector_scope.context.connector_info.environment,
                )

                # Verify that the case is not overflowed.
                # TODO: implement overflow logic, in the beginning of the flow
                is_overflowed = False
                # is_overflowed = connector_scope.is_overflowed_alert(alert_identifier=case.display_id,
                #                                                     environment=ConnectorInfo.environment,
                #                                                     ingestion_time=datetime.datetime.now())

                if not is_overflowed:
                    connector_scope.LOGGER.info("Case package created.")
                    cases.append(case)

                else:
                    connector_scope.LOGGER.info(
                        f'Case with display id: "{case.display_id}" and rule "{case.rule_generator}" is overflowed.'
                    )
            else:
                connector_scope.LOGGER.info(
                    f"Incident with id {incident_id} does not match by creator"
                )
        logging.debug(f"Got {str(len(cases))} cases since {str(last_run_time)}")

        # Save done incidents to incidents ids vault
        try:
            mark_done_incidents(unique_incident_ids, done_incident_ids_file_path)
        except Exception as err:
            connector_scope.LOGGER.error(f"Error marking done incidents, ERROR: {err}")
            connector_scope.LOGGER._log.exception(err)

        # Update last successful run time.
        connector_scope.save_timestamp(datetime_format=False)
        connector_scope.LOGGER.info(
            "--------------- CONNECTOR ITERATION FINISHED ---------------"
        )

        # Send packages to connector.
        connector_scope.return_package(cases, output_variables, log_items)

    except Exception as err:
        connector_scope.LOGGER.error(f"Got exception on main handler.Error: {err}")
        connector_scope.LOGGER._log.exception(err)


@output_handler
def test():
    connector_scope = SiemplifyConnectorExecution()
    try:
        # Define variables
        connector_scope.LOGGER.info(
            "--------------- CONNECTOR ITERATION STARTED ---------------"
        )
        done_incident_ids_file_path = (
            rf"{connector_scope.run_folder}/{DONE_INCIDENTS_FILE_NAME}"
        )
        incident_ids = []  # The list collects all relevant ticket ids.
        cases = []
        output_variables = {}
        log_items = []

        # Parameters
        # Credentials
        api_root = connector_scope.parameters.get("API Root")
        username = connector_scope.parameters.get("Username")
        password = connector_scope.parameters.get("Password")

        # Fields
        ticket_id_field = connector_scope.parameters.get("Ticket ID Field", "ref_num")
        start_time_field = connector_scope.parameters.get(
            "Start Time Field", "open_date"
        )
        end_time_field = connector_scope.parameters.get("End Time Field", "last_mod_dt")
        category_default_field = connector_scope.parameters.get(
            "Category Default Field", "category"
        )
        category_fallback_field = connector_scope.parameters.get(
            "Category Fallback Field", "category.sym"
        )
        user_id_field = connector_scope.parameters.get(
            "User ID Field", "customer.userid"
        )
        ticket_fields_str = connector_scope.parameters.get("Ticket Fields")

        # Filters
        not_from_user_filter_str = connector_scope.parameters.get(
            "List Of Users To Ignore", None
        )
        categories_filter_str = connector_scope.parameters.get("Categories List", None)
        groups_filers_str = connector_scope.parameters.get("Groups List", None)

        connector_scope.LOGGER.info("All parameters had been received.")

        # Convert string params to list.
        ticket_fields = ticket_fields_str.split(",") if ticket_fields_str else []

        # Verify optional fields.
        not_from_user_filter = (
            not_from_user_filter_str.split(",") if not_from_user_filter_str else []
        )
        categories_filter = (
            categories_filter_str.split(",") if categories_filter_str else []
        )
        groups_filers = groups_filers_str.split(",") if groups_filers_str else []

        # Define CA Desk Manager instance.
        try:
            ca_manager = CaSoapManager(api_root, username, password)
            connector_scope.LOGGER.info("Initiated CA Desk Manager instance.")
        except Exception as err:
            connector_scope.LOGGER.error(f"Connection Error Occurred, ERROR: {err}")
            connector_scope.LOGGER._log.exception(err)
            raise

        # Get last connector successful run.
        last_run_time = connector_scope.fetch_timestamp(datetime_format=False)
        connector_scope.LOGGER.info(f"Got last successful run: {str(last_run_time)}")

        # Get incident ids since last run time by filters.
        # Get incidents by groups.
        if groups_filers:
            for group in groups_filers:
                connector_scope.LOGGER.info(
                    f'Getting incidents for group: {group.encode("utf-8")}'
                )
                try:
                    incident_ids.extend(
                        ca_manager.get_incident_ids_by_filter(
                            last_modification_unixtime_milliseconds=last_run_time,
                            group_filter=str(group).encode("utf-8"),
                        )
                    )
                except Exception as err:
                    connector_scope.LOGGER.error(
                        f'Error fetching tickets for group {group.encode("utf-8")}, ERROR: {err}'
                    )
                    connector_scope.LOGGER._log.exception(err)
                    raise

            connector_scope.LOGGER.info(
                f"Found {str(len(incident_ids))} for groups, the ids are: {str(incident_ids)}"
            )
        # Get incidents by categories.
        elif categories_filter:
            connector_scope.LOGGER.info(
                f"--- Get incidents by categories: {str(categories_filter)} ---"
            )
            for category in categories_filter:
                connector_scope.LOGGER.info(
                    f"Getting incidents for category: {category}"
                )
                try:
                    incident_ids.extend(
                        ca_manager.get_incident_ids_by_filter(
                            last_modification_unixtime_milliseconds=last_run_time,
                            area_filter=category,
                        )
                    )
                except Exception as err:
                    connector_scope.LOGGER.error(
                        f"Error fetching tickets for category {category}, ERROR: {err}"
                    )
                    connector_scope.LOGGER._log.exception(err)
                    raise

            connector_scope.LOGGER.info(
                f"Found {str(len(incident_ids))} for categories, the ids are: {str(incident_ids)}"
            )
        else:
            connector_scope.LOGGER.info(
                "--- Get incidents by last run time(No filters were  inserted)"
            )
            try:
                incident_ids.extend(
                    ca_manager.get_incident_ids_by_filter(
                        last_modification_unixtime_milliseconds=last_run_time
                    )
                )
            except Exception as err:
                connector_scope.LOGGER.error(
                    f"Error fetching tickets by last run time, ERROR: {err}"
                )
                connector_scope.LOGGER._log.exception(err)
                raise

            connector_scope.LOGGER.info(
                f"Found {str(len(incident_ids))} since last run time, the ids are: {str(incident_ids)}"
            )

        # Filter out already done incidents
        try:
            incident_ids = filter_done_incidents(
                incident_ids, done_incident_ids_file_path
            )
        except Exception as err:
            connector_scope.LOGGER.error(f"Error filtering ticket ids, ERROR: {err}")
            connector_scope.LOGGER._log.exception(err)

        # Unify ids list.
        connector_scope.LOGGER.info("Unify ids list.")
        # Slice to one - for test
        unique_incident_ids = list(set(incident_ids))[:1]
        connector_scope.LOGGER.info(f"Unified ids list is: {str(unique_incident_ids)}")

        # Get incidents data and produce it to cases.
        for incident_id in unique_incident_ids:
            connector_scope.LOGGER.info(
                f"Getting data for incident with id: {incident_id}"
            )
            try:
                ticket_data = ca_manager.get_incident_by_id(incident_id, ticket_fields)
                connector_scope.LOGGER.info(f"Got data for incident: {incident_id}")
            except Exception as err:
                connector_scope.LOGGER.error(
                    f"Error fetching ticket data for incident with id: {incident_id}, ERROR: {err}"
                )
                connector_scope.LOGGER._log.exception(err)
                ticket_data = {}
                raise

            # Verify User Filter in order to exclude tickets that were created by Siemplify system.
            connector_scope.LOGGER.info(
                f"Check if creator is in users filter: {str(not_from_user_filter)}"
            )

            if (
                ticket_data.get(user_id_field)
                and not ticket_data.get(user_id_field) in not_from_user_filter
            ):
                # Build Siemplify event.
                connector_scope.LOGGER.info("Build event for incident.")
                try:
                    event = create_event_for_case(
                        ticket_data, start_time_field, end_time_field
                    )
                except Exception as err:
                    connector_scope.LOGGER.error(
                        f"Error creating an event for incident with id: {incident_id}"
                    )
                    connector_scope.LOGGER._log.exception(err)
                    # If not event created, return an empty event.
                    event = {}
                    raise

                # Add to an event number of attachments.
                connector_scope.LOGGER.info(
                    f"Get attachments for incident with id: {incident_id}"
                )
                try:
                    incidents_attachments_count = len(
                        ca_manager.get_incident_attachments(incident_id)
                    )
                    connector_scope.LOGGER.info(
                        f"Got {incidents_attachments_count} attachment for  for incident with id: {incidents_attachments_count}"
                    )
                    event["attachments_count"] = incidents_attachments_count
                except Exception as err:
                    connector_scope.LOGGER.error(
                        f"Error fetching attachments for incident with id:{incident_id}, Error:{err}"
                    )
                    connector_scope.LOGGER._log.exception(err)
                    raise

                # Add incident properties to event.
                connector_scope.LOGGER.info(
                    f"Get properties for incident with id: {incident_id}"
                )
                try:
                    incident_properties = ca_manager.get_incident_properties(
                        incident_id
                    )
                    for counter, property in enumerate(incident_properties):
                        prop_key = f"prop_{counter}"
                        if property.get("Name"):
                            event[prop_key] = (
                                f"{str(property.get('Value', 'None')).encode('utf-8')}:{str(property['Name']).encode('utf-8')}"
                            )
                    connector_scope.LOGGER.info(
                        f"Got properties for incident with id:{incident_id}"
                    )
                except Exception as err:
                    connector_scope.LOGGER.error(
                        f"Error fetching properties for incident with id: {incident_id}, Error: {err}"
                    )
                    connector_scope.LOGGER._log.exception(err)
                    raise

                connector_scope.LOGGER.info(f"Built event for incident: {incident_id}")

                # create case package and append it to case list.
                connector_scope.LOGGER.info("Creating case package.")

                # Create case object.
                case = create_case_package(
                    event,
                    category_default_field,
                    category_fallback_field,
                    ticket_id_field,
                    connector_scope.context.connector_info.environment,
                )

                # Verify that the case is not overflowed.
                # TODO: implement overflow logic, in the beginning of the flow
                is_overflowed = False
                # is_overflowed = connector_scope.is_overflowed_alert(alert_identifier=case.display_id,
                #                                                     environment=ConnectorInfo.environment,
                #                                                     ingestion_time=datetime.datetime.now())

                if not is_overflowed:
                    connector_scope.LOGGER.info("Case package created.")
                    cases.append(case)

                else:
                    connector_scope.LOGGER.info(
                        f'Case with display id: "{case.display_id}" and rule "{case.rule_generator}" is overflowed.'
                    )
            else:
                connector_scope.LOGGER.info(
                    f"Incident with id {incident_id} does not match by creator"
                )
        logging.debug(f"Got {str(len(cases))} cases since {str(last_run_time)}")

        connector_scope.return_package(cases, output_variables, log_items)

    except Exception as err:
        connector_scope.LOGGER.error(f"Got exception on main handler.Error: {err}")
        connector_scope.LOGGER._log.exception(err)
        raise


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "True":
        print("Main execution started")
        main()
    else:
        print("Test execution started")
        test()
