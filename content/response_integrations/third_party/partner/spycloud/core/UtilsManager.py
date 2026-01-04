from __future__ import annotations
import requests
import datetime
from datetime import timezone
import re
from .SpyCloudExceptions import SpyCloudException
from .constants import TIMEFRAME_MAPPING
from soar_sdk.SiemplifyUtils import convert_string_to_datetime

VALID_EMAIL_REGEXP = "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"


def is_valid_email(user_name):
    """
    Check if the user_name is valid email.
    :param user_name: {str} User name
    :return: {bool} True if valid email, else False
    """
    return bool(re.search(VALID_EMAIL_REGEXP, user_name))


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {unicode} Default message to display on error
    """
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        try:
            response.json()
        except Exception:
            raise SpyCloudException(f"{error_msg}: {error} {error.response.content}")

        raise SpyCloudException(
            f"{error_msg}: {error} {response.json().get('message') or response.content}"
        )


def get_timestamps_from_range(range_string):
    """
    Get start and end time timestamps from range
    :param range_string: {str} Time range string
    :return: {tuple} start and end time timestamps
    """
    now = datetime.datetime.now()
    today_datetime = datetime.datetime(
        year=now.year, month=now.month, day=now.day, hour=0, second=0
    )
    timeframe = TIMEFRAME_MAPPING.get(range_string)

    if timeframe == TIMEFRAME_MAPPING.get("Last Year"):
        end_time = today_datetime.today().replace(
            year=now.year - 1, month=12, day=31, hour=0, minute=0, second=0
        )
        start_time = today_datetime.today().replace(
            year=end_time.year, month=1, day=1, hour=0, minute=0, second=0
        )
    elif timeframe == TIMEFRAME_MAPPING.get("Last Week"):
        start_time, end_time = (
            today_datetime + datetime.timedelta(-today_datetime.weekday(), weeks=-1),
            today_datetime + datetime.timedelta(-today_datetime.weekday()),
        )

    elif timeframe == TIMEFRAME_MAPPING.get("Last Month"):
        end_time = today_datetime.today().replace(
            day=1, hour=0, minute=0, second=0
        ) - datetime.timedelta(days=1)
        start_time = today_datetime.today().replace(
            day=1, hour=0, minute=0, second=0
        ) - datetime.timedelta(days=end_time.day)
        end_time = end_time + datetime.timedelta(days=1)
    else:
        return None, None

    return start_time, end_time


def get_timestamps(range_string, start_time_string, end_time_string):
    """
    Get start and end time timestamps
    :param range_string: {str} Time range string
    :param start_time_string: {str} Start time
    :param end_time_string: {str} End time
    :return: {tuple} start and end time timestamps
    """
    start_time, end_time = get_timestamps_from_range(range_string)

    if not start_time and start_time_string:
        start_time = convert_string_to_datetime(start_time_string)

    if not end_time and end_time_string:
        end_time = convert_string_to_datetime(end_time_string)

    if not start_time:
        raise Exception(
            '"Start Time" should be provided, when "Custom" is selected in "Time Frame" parameter.'
        )

    if not end_time:
        end_time = datetime.datetime.now().replace(tzinfo=timezone.utc)

    if start_time > end_time:
        raise Exception('"End Time" should be later than "Start Time"')

    return start_time.date(), end_time.date()


def convert_comma_separated_to_list(comma_separated):
    """
    Convert comma-separated string to list
    :param comma_separated: String with comma-separated values
    :return: List of values
    """
    return [item.strip() for item in comma_separated.split(",")] if comma_separated else []


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
