from __future__ import annotations
import json
from typing import Any
import requests
from dateutil.relativedelta import relativedelta

from forti_analyzer.core.FortiAnalyzerExceptions import FortiAnalyzerException
from forti_analyzer.core.constants import TIME_INTERVAL_CHUNK, DATETIME_FORMAT, TIME_FRAME_MAPPING
from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime, convert_string_to_datetime
import datetime
from datetime import timezone


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    Args:
        response (requests.Response): The response to validate
        error_msg (str): Default message to display on error

    Returns:
        True, if successful, FortiAnalyzerException otherwise
    """
    try:
        response.raise_for_status()
        api_error = response.json().get("error", {})

        if api_error:
            raise FortiAnalyzerException(f"{error_msg}: {api_error.get('message', '')}")

    except requests.HTTPError as error:
        try:
            response.json()
        except Exception:
            raise FortiAnalyzerException(
                f"{error_msg}: {error} {error.response.content}"
            )

        response_json = response.json()
        api_error = response_json.get("error", {})

        if api_error:
            raise FortiAnalyzerException(
                f"{error_msg}: {error} {api_error.get('message') or response.content}"
            )
        else:
            raise FortiAnalyzerException(f"{error_msg}: {error} {response.content}")

    result = response.json().get("result", [])
    if isinstance(result, list) and result:
        statuses = [res.get("status", {}) for res in result]
        errors_message = "\n".join(
            [status.get("message") for status in statuses if status.get("code") != 0]
        )
        if errors_message:
            raise FortiAnalyzerException(f"{error_msg}: {errors_message}")


def get_entity_original_identifier(entity: Any) -> str:
    """
    Helper function for getting entity original identifier
    Args:
        entity: entity from which function will get original identifier

    Returns:
        original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def seconds_to_milliseconds(seconds: int) -> int:
    """
    Convert seconds to milliseconds
    Args:
        seconds (str): seconds to convert

    Returns:
        (int): converted value to milliseconds
    """
    try:
        return int(seconds) * 1000
    except Exception:
        return seconds


def prepare_time_ranges(
    start_timestamp: int, chunk: int = TIME_INTERVAL_CHUNK
) -> [(str, str)]:
    """
    Prepare time ranges by splitting time from given timestamp to current time to intervals
    Args:
        start_timestamp (int): start timestamp for range
        chunk (str): chunk to split range

    Returns:
        ([(str, str)]): list of time ranges
    """
    start = convert_unixtime_to_datetime(start_timestamp)
    end = datetime.datetime.now(timezone.utc)
    interval = datetime.timedelta(hours=chunk)
    intervals = []
    interval_start = start

    while interval_start < end:
        interval_end = min(interval_start + interval, end)
        intervals.append(
            (
                interval_start.strftime(DATETIME_FORMAT),
                interval_end.strftime(DATETIME_FORMAT),
            )
        )
        interval_start = interval_end + datetime.timedelta(seconds=1)

    return intervals


def datetime_to_rfc3339(datetime_obj):
    """
    Convert datetime object to RFC 3999 representation
    Args:
        datetime_obj (datetime.datetime): The datetime object to convert
    Returns:
        (str): The RFC 3999 representation of the datetime
    """
    return datetime_obj.strftime(DATETIME_FORMAT)


def get_timestamps_from_range(range_string):
    """
    Get start and end time timestamps from range
    Args:
        range_string (str): Time range string
    Returns:
        (tuple): start and end time timestamps
    """
    now = datetime.datetime.utcnow()
    timeframe = TIME_FRAME_MAPPING.get(range_string)

    if isinstance(timeframe, dict):
        start_time, end_time = now - datetime.timedelta(**timeframe), now
    elif timeframe == TIME_FRAME_MAPPING.get("Last Week"):
        start_time, end_time = now - datetime.timedelta(weeks=1), now
    elif timeframe == TIME_FRAME_MAPPING.get("Last Month"):
        start_time, end_time = now - relativedelta(months=1), now
    else:
        return None, None

    return datetime_to_rfc3339(start_time), datetime_to_rfc3339(end_time)


def get_timestamps(range_string, start_time_string=None, end_time_string=None):
    """
    Get start and end time timestamps
    Args:
        range_string (str): Time range string
        start_time_string (str): Start time
        end_time_string (str): End time
    Returns:
        (tuple): start and end time
    """
    start_time, end_time = get_timestamps_from_range(range_string)
    current_time_rfc3339 = datetime_to_rfc3339(datetime.datetime.utcnow())

    if not start_time and start_time_string:
        start_time = datetime_to_rfc3339(
            convert_string_to_datetime(
                start_time_string, timezone_str=datetime.timezone.utc
            )
        )

    if not end_time and end_time_string:
        end_time = datetime_to_rfc3339(
            convert_string_to_datetime(
                end_time_string, timezone_str=datetime.timezone.utc
            )
        )

    if not start_time:
        raise Exception(
            '"Start Time" should be provided, when "Custom" is selected in "Time Frame" parameter.'
        )

    if not end_time or end_time > current_time_rfc3339:
        end_time = current_time_rfc3339

    if start_time > end_time:
        raise Exception('"End Time" should be later than "Start Time"')

    return start_time, end_time


def convert_string_to_json(string):
    """
    Convert string to json
    Args:
        string (str): string to convert
    Returns:
        (dict): json dict
    """
    try:
        return json.loads(string)
    except Exception:
        return string
