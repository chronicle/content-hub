from __future__ import annotations
from soar_sdk.SiemplifyUtils import unix_now, convert_unixtime_to_datetime
from tanium.core.constants import (
    TIMEOUT_THRESHOLD,
    TIMEFRAME_MAPPING,
    GLOBAL_TIMEOUT_THRESHOLD_IN_MIN,
    TIME_FORMAT,
)
from tanium.core.exceptions import InvalidTimeException
import datetime
from dateutil.relativedelta import relativedelta
import dateutil.parser
import os


def is_async_action_global_timeout_approaching(siemplify, start_time):
    return (
        siemplify.execution_deadline_unix_time_ms - start_time
        < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60
    )


def string_to_multi_value(string_value, delimiter=",", only_unique=False):
    """
    String to multi value.
    :param string_value: {str} String value to convert multi value.
    :param delimiter: {str} Delimiter to extract multi values from single value string.
    :param only_unique: {bool} include only uniq values
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


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def is_approaching_timeout(action_starting_time, python_process_timeout):
    """
    Check if a timeout is approaching.
    :param action_starting_time: {int} Action start time
    :param python_process_timeout: {int} The python process timeout
    :return: {bool} True if timeout is close, False otherwise
    """
    processing_time_ms = unix_now() - action_starting_time
    return (
        processing_time_ms
        > (python_process_timeout - action_starting_time) * TIMEOUT_THRESHOLD
    )


def is_approaching_process_timeout(action_starting_time, python_process_timeout):
    """
    Check if a timeout is approaching.
    :param action_starting_time: {int} Action start time
    :param python_process_timeout: {int} The python process timeout
    :return: {bool} True if timeout is close, False otherwise
    """
    processing_time_ms = unix_now() - action_starting_time
    return processing_time_ms > python_process_timeout * 1000 * TIMEOUT_THRESHOLD


def convert_string_to_timestamp(datetime_string):
    """
    Convert datetime string to timestamp
    :param datetime_string: {str} Datetime string
    :return: {int} The timestamp
    """
    datetime_object = dateutil.parser.parse(datetime_string)
    return datetime.datetime.timestamp(datetime_object)


def get_timestamps_from_range(range_string, alert_start_time=None, alert_end_time=None):
    """
    Get start and end time timestamps from range
    :param range_string: {str} Time range string
    :param alert_start_time: {str} Start time of the alert
    :param alert_end_time: {str} End time of the alert
    :return: {tuple} start and end time timestamps
    """
    now = datetime.datetime.utcnow()
    timeframe = TIMEFRAME_MAPPING.get(range_string)

    if isinstance(timeframe, dict):
        start_time, end_time = now - datetime.timedelta(**timeframe), now
    elif timeframe == TIMEFRAME_MAPPING.get("Last Week"):
        start_time, end_time = now - datetime.timedelta(weeks=1), now
    elif timeframe == TIMEFRAME_MAPPING.get("Last Month"):
        start_time, end_time = now - relativedelta(months=1), now
    elif timeframe == TIMEFRAME_MAPPING.get("Alert Time Till Now"):
        start_time, end_time = alert_start_time, now
    elif timeframe == TIMEFRAME_MAPPING.get("5 Minutes Around Alert Time"):
        start_time, end_time = alert_start_time - datetime.timedelta(
            minutes=5
        ), alert_end_time + datetime.timedelta(minutes=5)
    elif timeframe == TIMEFRAME_MAPPING.get("30 Minutes Around Alert Time"):
        start_time, end_time = alert_start_time - datetime.timedelta(
            minutes=30
        ), alert_end_time + datetime.timedelta(minutes=30)
    elif timeframe == TIMEFRAME_MAPPING.get("1 Hour Around Alert Time"):
        start_time, end_time = alert_start_time - datetime.timedelta(
            hours=1
        ), alert_end_time + datetime.timedelta(hours=1)
    else:
        return None, None

    return start_time.timestamp(), end_time.timestamp()


def get_timestamps(
    range_string,
    start_time_string=None,
    end_time_string=None,
    alert_start_time=None,
    alert_end_time=None,
):
    """
    Get start and end time timestamps
    :param range_string: {str} Time range string
    :param start_time_string: {str} Start time
    :param end_time_string: {str} End time
    :param alert_start_time: {str} Start time of the alert
    :param alert_end_time: {str} End time of the alert
    :return: {tuple} start and end time timestamps
    """
    start_time, end_time = get_timestamps_from_range(
        range_string, alert_start_time, alert_end_time
    )
    current_time = datetime.datetime.utcnow().timestamp()

    if not start_time and start_time_string:
        start_time = convert_string_to_timestamp(start_time_string)

    if not end_time and end_time_string:
        end_time = convert_string_to_timestamp(end_time_string)

    if not start_time:
        raise InvalidTimeException

    if not end_time or end_time > current_time:
        end_time = current_time

    if start_time > end_time:
        raise Exception('"End Time" should be later than "Start Time"')

    return str(start_time * 1000).split(".")[0], str(end_time * 1000).split(".")[0]


def convert_comma_separated_to_list(comma_separated):
    """
    Convert comma-separated string to list
    :param comma_separated: String with comma-separated values
    :return: List of values
    """
    return (
        [item.strip() for item in comma_separated.split(",")] if comma_separated else []
    )


def convert_list_to_comma_string(values_list):
    """
    Convert list to comma-separated string
    :param values_list: List of values
    :return: String with comma-separated values
    """
    return (
        ", ".join(str(v) for v in values_list)
        if values_list and isinstance(values_list, list)
        else values_list
    )


def save_attachment(path, name, content):
    """
    Save attachment to local path
    :param path: {str} Path of the folder, where files should be saved
    :param name: {str} File name to be saved
    :param content: {str} File content
    :return: {str} Path to the downloaded files
    """

    if not os.path.exists(path):
        raise Exception(f"Folder {path} not found.")
    # File local path
    local_path = os.path.join(path, name)
    with open(local_path, "wb") as file:
        file.write(content)

    return local_path


def unixtime_to_rfc3339(unix_timestamp) -> str:
    """
    Convert unix timestamp to RFC 3999 representation
    :param unix_timestamp: {int} The unix timestamp object to convert
    :return: {str} The RFC 3999 representation of the datetime
    """
    datetime_obj = convert_unixtime_to_datetime(unix_timestamp)
    return datetime_obj.strftime(TIME_FORMAT)
