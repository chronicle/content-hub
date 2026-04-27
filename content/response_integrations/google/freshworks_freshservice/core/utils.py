from __future__ import annotations
import datetime
import json

from TIPCommon import utc_now
from .exceptions import FreshworksFreshserviceValidationError


def load_csv_to_list(csv: str, param_name: str):
    """
    Load comma separated values represented as string to a list. Remove duplicates if exist
    :param csv: {str} of comma separated values with delimiter ','
    :param param_name: {str} the name of the parameter we are loading csv to list
    :return: {[str]} List of separated string values
            raise FreshworksFreshserviceValidationError if failed to parse csv string
    """
    try:
        return list(set(value.strip() for value in csv.split(",")))
    except Exception as exc:
        raise FreshworksFreshserviceValidationError(
            f"Failed to load comma separated string parameter '{param_name}'"
        ) from exc


def load_kv_csv_to_dict(kv_csv: str, param_name: str):
    """
    Load comma separated values of 'key':'value' represented as string to a dictionary
    :param kv_csv: {str} of comma separated values of 'key':'value' represented as a string
    :param param_name: {str} name of the parameter
    :return: {dict} of key:value
            raise FreshworksFreshserviceValidationError if failed to parse key value csv
    """
    try:
        return {
            kv.split(":")[0].strip(): kv.split(":")[1].strip()
            for kv in kv_csv.split(",")
        }
    except Exception as exc:
        raise FreshworksFreshserviceValidationError(
            f'Failed to load comma separated key:value string parameter "{param_name}"'
        ) from exc


def load_json_string_to_dict(json_str: str, param_name: str):
    """
    Load string representing json data to a dictionary
    :param json_str: {str} String of json data
    :param param_name: {str} Name of the json data parameter
    :return: {dict} Dictionary of loaded json data
    """
    try:
        return json.loads(json_str)
    except Exception as exc:
        raise FreshworksFreshserviceValidationError(
            f"Failed to load JSON data of string parameter '{param_name}'."
            " Invalid JSON was provided."
        ) from exc


def remove_none_dictionary_values(**kwargs) -> dict:
    """
    Remove keys from dictionary that has the value None
    :param kwargs: key value arguments
    :return: {dict} dictionary without keys that have the value None
    """
    return {k: v for k, v in kwargs.items() if v is not None}


def validate_timestamp(last_run_timestamp, offset_in_hours):
    """
    Validate timestamp in range
    :param last_run_timestamp: {datetime} last run timestamp
    :param offset_in_hours: {datetime} last run timestamp
    :return: {datetime} if first run, return current time minus offset time, else return timestamp from file
    """
    current_time = utc_now()
    # Check if first run
    if current_time - last_run_timestamp > datetime.timedelta(hours=offset_in_hours):
        return current_time - datetime.timedelta(hours=offset_in_hours)
    else:
        return last_run_timestamp


def update_department_names(record, departments):
    """
    Update record raw data with department names
    :param record: {datamodels}  FreshService data model
    :param departments: {[datamodels.Department]} List of departments data models
    """
    agent_department_ids = record.department_ids
    agent_department_names = {
        dep.name for dep in departments if dep.id in agent_department_ids
    }
    record.raw_data.update({"department_names": list(agent_department_names)})


def update_record_location_name(record, locations):
    """
    Update agent's raw data with location name
    :param record: {datamodel} FreshService data model
    :param locations: {[datamodels.Location]} List of locations data models
    """
    location_id = record.location_id
    for location in locations:
        if location_id == location.id:
            record.raw_data.update({"location_name": location.name})
            return


def update_agent_group_names(agent, agent_groups):
    """
    Update agent's raw data with group names
    :param agent: {datamodels.Agent} Agent data model
    :param agent_groups: {[datamodels.AgentGroup]} List of Agent Group data models
    """
    agent_group_ids = agent.raw_data.get("member_of", [])
    agent_group_names = {
        agent_group.name
        for agent_group in agent_groups
        if agent_group.id in agent_group_ids
    }
    agent.raw_data.update({"member_group_names": list(agent_group_names)})


def update_agent_roles_names(agent, agent_roles):
    """
    Update agent's raw data with roles names
    :param agent: {datamodels.Agent} Agent data model
    :param agent_roles: {[datamodels.Role]} List of Agent Roles data models
    """
    agent_roles_data = agent.raw_data.get("roles", [])
    agent_roles_ids = [agent_role.get("role_id") for agent_role in agent_roles_data]
    agent_roles_names = {
        agent_role.name
        for agent_role in agent_roles
        if agent_role.id in agent_roles_ids
    }
    agent.raw_data.update({"agent_role_names": list(agent_roles_names)})


def get_group_ids_by_names(agent_groups, group_membership_set):
    """
    Get agent group ids from the groups names
    :param agent_groups: {[datamodels.AgentGroup]} agent groups data models list
    :param group_membership_set: {{str}} Set of group names
    :return: {[int]} List of agent group ids
    """
    agent_group_ids_names_dict = {
        agent_group.id: agent_group.name
        for agent_group in agent_groups
        if agent_group.name in group_membership_set
    }
    missing_groups = group_membership_set - set(agent_group_ids_names_dict.values())
    if missing_groups:
        raise FreshworksFreshserviceValidationError(
            f"The following groups do not exist: {', '.join(missing_groups)}"
        )

    return agent_group_ids_names_dict.keys()


def get_department_ids_by_names(departments, department_names_set):
    """
    Get departments ids from the department names
    :param departments: {[datamodels.Department]} departments data models list
    :param department_names_set: {{str}} Set of departments names
    :return: {[int]} List of department ids
    """
    department_ids_names_dict = {
        department.id: department.name
        for department in departments
        if department.name in department_names_set
    }
    missing_departments = department_names_set - set(department_ids_names_dict.values())
    if missing_departments:
        raise FreshworksFreshserviceValidationError(
            f"The following departments do not exist: {', '.join(missing_departments)}"
        )

    return department_ids_names_dict.keys()


def get_location_id_by_name(locations, location):
    """
    Get departments ids from the department names.
    :param locations: {[datamodels.Location]} locations data models list.
    :param location: {str} provided location name.
    :return: {int} location id of the provided location name.
    """
    for loc in locations:
        if loc.name == location:
            return loc.id

    raise FreshworksFreshserviceValidationError(
        f"The provided location ({location}) does not exist"
    )


def is_siemplify_alert_matches_freshservice_ticket(
    alert_data: dict, ticket_id: str, device_product: str
):
    """
    Check if Siemplify alert matches freshservice ticket
    :param alert_data: {dict} Alert data
    :param ticket_id: {str} Ticket ID of the freshservice ticket to match
    :param device_product: {str} Device product
    :return: {bool} True if alert matches freshservice ticket, otherwise False
    """
    return ticket_id == alert_data.get("additional_properties", {}).get(
        "TicketId"
    ) and device_product == alert_data.get("additional_properties", {}).get(
        "DeviceProduct"
    )


def string_to_multi_value(string_value, delimiter=",", only_unique=False):
    """
    String to multi value.
    :param string_value: {str} String value to convert multi value.
    :param delimiter: {str} Delimiter to extract multi values from single value string.
    :param only_unique: {bool} include only unique values
    :return: {dict} fixed dictionary.
    """
    if not string_value:
        return []

    values = [
        single_value.strip()
        for single_value in string_value.split(delimiter)
        if single_value.strip()
    ]
    if only_unique:
        seen = set()
        return [value for value in values if not (value in seen or seen.add(value))]

    return values
