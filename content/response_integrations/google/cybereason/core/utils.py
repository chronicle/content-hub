from __future__ import annotations
from typing import Any
from collections import defaultdict
import os
import datetime
import json

from soar_sdk.SiemplifyUtils import utc_now, unix_now
from EnvironmentCommon import EnvironmentHandle
from TIPCommon import validate_map_file

from .constants import SHA1, MD5, SUPPORTED_FILE_HASH_TYPES, FILE_FIELDS

IDS_FILE = "ids.json"
MAP_FILE = "map.json"
ALERT_ID_FIELD = "guid"
LIMIT_IDS_IN_IDS_FILE = 1000
TIMEOUT_THRESHOLD = 0.9
GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1


def is_async_action_global_timeout_approaching(siemplify, start_time):
    return (
        siemplify.execution_deadline_unix_time_ms - start_time
        < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60
    )


def is_approaching_timeout(connector_starting_time, python_process_timeout):
    """
    Check if a timeout is approaching.
    :param connector_starting_time: {int} Connector start time
    :param python_process_timeout: {int} The python process timeout
    :return: {bool} True if timeout is close, False otherwise
    """
    processing_time_ms = unix_now() - connector_starting_time
    return processing_time_ms > python_process_timeout * 1000 * TIMEOUT_THRESHOLD


def validate_timestamp(last_run_timestamp, offset_in_hours):
    """
    Validate timestamp in range
    :param last_run_timestamp: {datetime} last run timestamp
    :param offset_in_hours: {int} backward hours count
    :return: {datetime} if first run, return current time minus offset time, else return timestamp from file
    """
    current_time = utc_now()
    # Check if first run
    if current_time - last_run_timestamp > datetime.timedelta(hours=offset_in_hours):
        return current_time - datetime.timedelta(hours=offset_in_hours)
    else:
        return last_run_timestamp


def validate_end_time(end_time):
    """
    Validate end time interval
    :param end_time: {datetime} Last run timestamp + 12 hours interval
    :return: {datetime} if end_time > current_time, return current time, else return end_time
    """
    current_time = utc_now()
    if end_time > current_time:
        return current_time
    else:
        return end_time


# Move to TIPCommon
def get_environment_common(
    siemplify, environment_field_name, environment_regex_pattern, map_file=MAP_FILE
):
    """
    Get environment common
    :param siemplify: {siemplify} Siemplify object
    :param environment_field_name: {string} The environment field name
    :param environment_regex_pattern: {string} The environment regex pattern
    :param map_file: {string} The map file
    :return: {EnvironmentHandle}
    """
    map_file_path = os.path.join(siemplify.run_folder, map_file)
    validate_map_file(siemplify, map_file_path)
    return EnvironmentHandle(
        map_file_path,
        siemplify.LOGGER,
        environment_field_name,
        environment_regex_pattern,
        siemplify.context.connector_info.environment,
    )


# Move to TIPCommon
def filter_old_alerts(logger, alerts, existing_ids, id_key=ALERT_ID_FIELD):
    """
    Filter alerts that were already processed
    :param logger: {SiemplifyLogger} Siemplify logger
    :param alerts: {list} The alerts to filter
    :param existing_ids: {list} The ids to filter
    :param id_key: {str} The key of identifier
    :return: {list} The filtered alerts
    """
    filtered_alerts = []
    for alert in alerts:
        id = getattr(alert, id_key)
        if id not in existing_ids.keys():
            filtered_alerts.append(alert)
        else:
            logger.info(f"The alert {id} skipped since it has been fetched before")

    return filtered_alerts


# Move to TIPCommon
def read_ids(siemplify, ids_file_name=IDS_FILE):
    """
    Read existing alerts IDs from ids file (from last 24h only)
    :param siemplify: {Siemplify} Siemplify object.
    :param ids_file_name: {str} The name of the ids file
    :return: {list} List of ids
    """
    ids_file_path = os.path.join(siemplify.run_folder, ids_file_name)
    if not os.path.exists(ids_file_path):
        return {}

    try:
        with open(ids_file_path, "r") as f:
            return json.loads(f.read())
    except Exception as e:
        siemplify.LOGGER.error(f"Unable to read ids file: {e}")
        siemplify.LOGGER.exception(e)
        return {}


# Move to TIPCommon
def write_ids(siemplify, ids, ids_file_name=IDS_FILE):
    """
    Write ids to the ids file
    :param siemplify: {Siemplify} Siemplify object.
    :param ids: {dict} The ids to write to the file
    :param ids_file_name: {str} The name of the ids file.
    :return: {bool}
    """
    try:
        ids_file_path = os.path.join(siemplify.run_folder, ids_file_name)
        if not os.path.exists(os.path.dirname(ids_file_path)):
            os.makedirs(os.path.dirname(ids_file_path))

        with open(ids_file_path, "w") as f:
            try:
                for chunk in json.JSONEncoder().iterencode(ids):
                    f.write(chunk)
            except:
                # Move seeker to start of the file
                f.seek(0)
                # Empty the content of the file (the partially written content that was written before the exception)
                f.truncate()
                # Write an empty dict to the events data file
                f.write("{}")
                raise
        return True
    except Exception as err:
        siemplify.LOGGER.error(f"Failed writing IDs to IDs file, ERROR: {err}")
        siemplify.LOGGER.exception(err)
        return False


# Move to TIPCommon
def is_overflowed(siemplify, alert_info, is_test_run):
    """
    Check if overflowed
    :param siemplify: {Siemplify} Siemplify object.
    :param alert_info: {AlertInfo}
    :param is_test_run: {bool} Whether test run or not.
    :return: {bool}
    """
    try:
        return siemplify.is_overflowed_alert(
            environment=alert_info.environment,
            alert_identifier=alert_info.ticket_id,
            alert_name=alert_info.rule_generator,
            product=alert_info.device_product,
        )

    except Exception as err:
        siemplify.LOGGER.error(f"Error validation connector overflow, ERROR: {err}")
        siemplify.LOGGER.exception(err)
        if is_test_run:
            raise

    return False


def convert_comma_separated_to_list(comma_separated):
    # type: (str) -> list
    """
    Convert comma-separated string to list
    @param comma_separated: String with comma-separated values
    @return: List of values
    """
    return (
        [item.strip() for item in comma_separated.split(",")] if comma_separated else []
    )


def convert_list_to_comma_string(values_list):
    # type: (list) -> str
    """
    Convert list to comma-separated string
    @param values_list: List of values
    @return: String with comma-separated values
    """
    return (
        ", ".join(str(v) for v in values_list)
        if values_list and isinstance(values_list, list)
        else values_list
    )


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def get_domain_from_entity(identifier):
    """
    Extract domain from entity identifier
    :param identifier: {str} the identifier of the entity
    :return: {str} domain part from entity identifier
    """
    if "@" in identifier:
        return identifier.split("@", 1)[-1]
    try:
        import tldextract

        result = tldextract.extract(identifier)
        join_with = "."
        result_to_join = [
            item for item in [result.subdomain, result.domain, result.suffix] if item
        ]
        return join_with.join(result_to_join)

    except ImportError:
        raise ImportError("tldextract is not installed. Use pip and install it.")


def get_hash_type(file_hash):
    """
    Determine the type of a hash
    :param file_hash: {str} The hash type
    :return: {str} The hash type
    """
    if len(file_hash) == 32:
        return MD5

    if len(file_hash) == 40:
        return SHA1


def get_supported_file_hashes(siemplify, file_hashes):
    """
    Filter file hashes
    :param siemplify: {Siemplify} Siemplify object.
    :param file_hash: {str} The hash type
    :return: {list} supported file hashes
    """
    supported_file_hashes = []
    if file_hashes:
        for file_hash in file_hashes:
            hash_type = get_hash_type(file_hash)
            if hash_type in SUPPORTED_FILE_HASH_TYPES:
                supported_file_hashes.append(file_hash)
                continue
            siemplify.LOGGER.info(
                f"Hash {file_hash} is not supported. Supported types are MD5, SHA1. Skipping."
            )
        if not supported_file_hashes:
            raise Exception(
                f'Hashes {", ".join(file_hashes)} are not supported. Supported types are MD5, SHA1'
            )
    return supported_file_hashes


def validate_fields_to_return(fields_to_return, possible_fields=None):
    """
    Validate fields to return
    :param fields_to_return: {list} fields to return
    :return: {list}, {list} Valid and invalid fields
    """
    valid_field_to_return, invalid_field_to_return = [], []
    if possible_fields:
        for field in fields_to_return:
            if field not in possible_fields:
                invalid_field_to_return.append(field)
                continue
            valid_field_to_return.append(field)
    else:
        for field in fields_to_return:
            if field not in FILE_FIELDS:
                invalid_field_to_return.append(field)
                continue
            valid_field_to_return.append(field)

    return valid_field_to_return, invalid_field_to_return


def validate_positive_integer(limit):
    if limit <= 0:
        raise Exception('"Results Limit" should be a positive number.')


def string_to_multi_value(string_value, delimiter=",", only_unique=False):
    # type: (str, str, bool) -> list
    """
    String to multi value.
    @param string_value: {str} String value to convert multi value.
    @param delimiter: {str} Delimiter to extract multi values from single value string.
    @param only_unique: {bool} include only uniq values
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


def milliseconds_to_human_time(milliseconds):
    try:
        dt = datetime.timedelta(milliseconds=int(milliseconds))
        return f"{dt.days} days {int(dt.seconds // 3600)} hours {int(dt.seconds // 60) % 60} minutes {dt.seconds % 60} seconds"
    except:
        return milliseconds


def update_ids_get_status_result_data(
    result_data: dict[str, Any], process_name: str
) -> dict[str, Any]:
    """Add custom keys in json result for remediation process response.

    Args:
        result_data (dict): remediation process response dict data.
        process_name (str): file name for which remediation action called.

    Returns:
        dict: udpated remediation response with added custom keys.
              ["final_status", "remediation_action", "target_name"]
    """
    last_status_log = result_data["statusLog"][-1]

    status = last_status_log["status"]
    result_data["final_status"] = status
    result_data["remediation_action"] = last_status_log["actionType"]
    result_data["target_name"] = process_name

    return result_data


def merge_result_json_data(*raw_data: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge all results of successful, unsuccessful, failed entities.

    Returns:
        dict: updated json result with merged all the dict object.
    """
    merged_json_data = defaultdict(list)
    for data in raw_data:
        for key, value in data.items():
            merged_json_data[key].extend(value)

    merged_json_data = dict(merged_json_data)

    return merged_json_data


def search_unique_ids_in_malop(
    data_list: list[MalopSuspeciousDetails], unique_ids: list[str]
) -> tuple[list[MalopSuspeciousDetails], list[str]]:
    """Search unique ids in the Malop Data.

    Args:
        data_list (list[MalopSuspeciousDetails]): List of MalopSuspeciousDetails
        object.
        unique_ids (list[str]): Action parameter "Remediation Unique IDs" list
        values.

    Returns:
        tuple: tuple of found MalopSuspeciousDetails object list and not found
        unique id list.
    """

    found_unique_ids_data = []
    found_unique_ids = []
    not_found_unique_ids = []

    for data_obj in data_list:
        unique_id = data_obj.unique_id

        if unique_id in unique_ids:
            found_unique_ids_data.append(data_obj)
            found_unique_ids.append(unique_id)

    [
        not_found_unique_ids.append(unique_id)
        for unique_id in unique_ids
        if unique_id not in found_unique_ids
    ]

    return found_unique_ids_data, not_found_unique_ids
