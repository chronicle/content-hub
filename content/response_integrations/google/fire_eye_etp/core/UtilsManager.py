from __future__ import annotations
import datetime

import requests
from dateutil.tz import tzoffset
from dateutil import parser


def naive_time_converted_to_aware(time_param, timezone_offset):
    """
    Converts naive time to aware time
    :param timezone_offset: UTC timezone offset
    :param time_param: Naive time to convert
    :return: {datetime}
    """
    parsed_date = parser.parse(time_param)
    return datetime.datetime(
        parsed_date.year,
        parsed_date.month,
        parsed_date.day,
        parsed_date.hour,
        parsed_date.minute,
        parsed_date.second,
        tzinfo=get_server_tzoffset(timezone_offset),
    )


def get_server_tzoffset(server_timezone):
    """
    get server timezone offset from utc
    :param server_timezone {str} UTC timezone offset
    :return: {tzoffset}
    """
    return tzoffset(None, float(server_timezone) * 60 * 60)


def current_server_time(timezone_offset):
    """
    get utc current time
    :param timezone_offset {str} UTC timezone offset
    :return: {datetime}
    """
    return datetime.datetime.now(tz=get_server_tzoffset(timezone_offset))


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {str} Default message to display on error
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        raise Exception(f"{error_msg}: {error} {error.response.content}")

    return True


def validate_timestamp(last_run_timestamp, offset_in_hours, current_time):
    """
    Validate timestamp in range
    :param last_run_timestamp: {datetime} last run timestamp
    :param offset_in_hours: {datetime} last run timestamp
    :param current_time: {str} Current server time
    :return: {datetime} if first run, return current time minus offset time, else return timestamp from file
    """
    # Check if first run
    if current_time - last_run_timestamp > datetime.timedelta(hours=offset_in_hours):
        return current_time - datetime.timedelta(hours=offset_in_hours)
    else:
        return last_run_timestamp
