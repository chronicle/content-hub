from __future__ import annotations
import requests
import datetime
from soar_sdk.SiemplifyUtils import convert_string_to_datetime
from bit_sight.core.BitSightExceptions import BitSightException
from bit_sight.core.constants import TIMEFRAME_MAPPING, TIME_FORMAT, NOW
from dateutil.relativedelta import relativedelta


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    Args:
        response (requests.Response): The response to validate
        error_msg (str): Default message to display on error

    Returns:
        (void)

    Raises:
        BitSightException
    """
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        try:
            response.json()
        except Exception:
            raise BitSightException(f"{error_msg}: {error} {error.response.content}")

        raise BitSightException(
            f"{error_msg}: {error} {response.json().get('detail') or response.content}"
        )


def validate_positive_integer(
    number, err_msg="Limit parameter should be greater than 0"
):
    if number <= 0:
        raise Exception(err_msg)


def datetime_to_rfc3339(datetime_obj):
    """
    Convert datetime object to RFC 3999 representation
    Args:
        datetime_obj (datetime.datetime): The datetime object to convert
    Returns:
        (str): The RFC 3999 representation of the datetime
    """
    return datetime_obj.strftime(TIME_FORMAT)


def get_timestamps_from_range(range_string):
    """
    Get start and end time timestamps from range
    Args:
        range_string (str): Time range string
    Returns:
        (tuple): start and end time timestamps
    """
    now = datetime.datetime.utcnow()
    timeframe = TIMEFRAME_MAPPING.get(range_string)

    if isinstance(timeframe, dict):
        start_time, end_time = now - datetime.timedelta(**timeframe), now
    elif timeframe == TIMEFRAME_MAPPING.get("Last Week"):
        start_time, end_time = now - datetime.timedelta(weeks=1), now
    elif timeframe == TIMEFRAME_MAPPING.get("Last Month"):
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
        start_time = datetime_to_rfc3339(convert_string_to_datetime(start_time_string))

    if not end_time and end_time_string:
        if end_time_string.lower() == NOW:
            end_time = current_time_rfc3339
        else:
            end_time = datetime_to_rfc3339(convert_string_to_datetime(end_time_string))

    if not start_time:
        raise Exception(
            '"Start Time" should be provided, when "Custom" is selected in "Time Frame" parameter.'
        )

    if not end_time or end_time > current_time_rfc3339:
        end_time = current_time_rfc3339

    if start_time > end_time:
        raise Exception('"End Time" should be later than "Start Time"')

    return start_time, end_time


def convert_list_to_comma_string(values_list):
    """
    Convert list to comma-separated string
    :param values_list: List of values
    :return: String with comma-separated values
    """
    return (
        "; ".join(str(v) for v in values_list)
        if values_list and isinstance(values_list, list)
        else values_list
    )
