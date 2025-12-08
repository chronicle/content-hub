from __future__ import annotations

import base64
import datetime
import time
from typing import Any

import dateutil.parser
import requests
from constants import (
    BEHAVIOUR_VISIBILITY_FILTER_VALUES,
    ERROR_TEXT,
    MAX_PADDING_TIME,
    MILI_SECOND,
    MILLISECONDS_IN_HOUR,
    TIME_FORMAT,
    TIMEFRAME_MAPPING,
)
from DarktraceExceptions import (
    ErrorInResponseException,
    InvalidTimeException,
    NotFoundException,
)
from dateutil.relativedelta import relativedelta
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import convert_string_to_datetime, unix_now
from TIPCommon.exceptions import ParameterValidationError
from TIPCommon.extraction import extract_connector_param
from TIPCommon.smp_time import get_last_success_time

# Move to TIPCommon
STORED_IDS_LIMIT = 3000
TIMEOUT_THRESHOLD = 0.9
WHITELIST_FILTER = 1
BLACKLIST_FILTER = 2
UNIX_FORMAT = 1
DATETIME_FORMAT = 2


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {str} Default message to display on error
    """
    try:
        response.raise_for_status()

        if _response_contains_errors(response):
            raise ErrorInResponseException

    except requests.HTTPError as error:
        if response.status_code == 404:
            raise NotFoundException(error)

        raise Exception(f"{error_msg}: {error} {error.response.content}")


def _response_contains_errors(response: requests.Response) -> bool:
    return (
        response.content
        and isinstance(response.json(), dict)
        and response.json().get("response") == ERROR_TEXT
    )


def get_timestamps_from_range(range_string):
    """
    Get start and end time timestamps from range
    :param range_string: {str} Time range string
    :return: {tuple} start and end time timestamps
    """
    now = datetime.datetime.utcnow()
    today_datetime = datetime.datetime(
        year=now.year, month=now.month, day=now.day, hour=0, second=0
    )
    timeframe = TIMEFRAME_MAPPING.get(range_string)

    if isinstance(timeframe, dict):
        start_time, end_time = now - datetime.timedelta(**timeframe), now
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

    return (
        start_time.replace(tzinfo=datetime.timezone.utc).timestamp(),
        end_time.replace(tzinfo=datetime.timezone.utc).timestamp(),
    )


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
        start_time = convert_string_to_timestamp(start_time_string)

    if not end_time and end_time_string:
        end_time = convert_string_to_timestamp(end_time_string)

    if not start_time:
        raise InvalidTimeException

    if not end_time:
        end_time = time.time()

    return start_time, end_time


def convert_string_to_timestamp(datetime_string):
    """
    Convert datetime string to timestamp
    :param datetime_string: {str} Datetime string
    :return: {int} The timestamp
    """
    datetime_object = dateutil.parser.parse(datetime_string)
    return datetime.datetime.timestamp(datetime_object)


def datetime_to_rfc3339(datetime_obj):
    """
    Convert datetime object to RFC 3999 representation
    :param datetime_obj: {datetime.datetime} The datetime object to convert
    :return: {str} The RFC 3999 representation of the datetime
    """
    return datetime_obj.strftime(TIME_FORMAT)


def get_datetimes_from_range(range_string, alert_start_time=None, alert_end_time=None):
    """
    Get start and end datetimes from range
    :param range_string: {str} Time range string
    :param alert_start_time: {str} Start time of the alert
    :param alert_end_time: {str} End time of the alert
    :return: {tuple} start and end datetimes
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
        start_time, end_time = (
            alert_start_time - datetime.timedelta(minutes=5),
            alert_end_time + datetime.timedelta(minutes=5),
        )
    elif timeframe == TIMEFRAME_MAPPING.get("30 Minutes Around Alert Time"):
        start_time, end_time = (
            alert_start_time - datetime.timedelta(minutes=30),
            alert_end_time + datetime.timedelta(minutes=30),
        )
    elif timeframe == TIMEFRAME_MAPPING.get("1 Hour Around Alert Time"):
        start_time, end_time = (
            alert_start_time - datetime.timedelta(hours=1),
            alert_end_time + datetime.timedelta(hours=1),
        )
    else:
        return None, None

    return datetime_to_rfc3339(start_time), datetime_to_rfc3339(end_time)


def get_datetimes(
    range_string,
    start_time_string=None,
    end_time_string=None,
    alert_start_time=None,
    alert_end_time=None,
):
    """
    Get start and end datetimes
    :param range_string: {str} Time range string
    :param start_time_string: {str} Start time
    :param end_time_string: {str} End time
    :param alert_start_time: {str} Start time of the alert
    :param alert_end_time: {str} End time of the alert
    :return: {tuple} start and end datetimes
    """
    start_time, end_time = get_datetimes_from_range(range_string, alert_start_time, alert_end_time)
    current_time_rfc3339 = datetime_to_rfc3339(datetime.datetime.utcnow())

    if not start_time and start_time_string:
        start_time = datetime_to_rfc3339(convert_string_to_datetime(start_time_string))

    if not end_time and end_time_string:
        end_time = datetime_to_rfc3339(convert_string_to_datetime(end_time_string))

    if not start_time:
        raise InvalidTimeException

    if not end_time or end_time > current_time_rfc3339:
        end_time = current_time_rfc3339

    if start_time > end_time:
        raise Exception('"End Time" should be later than "Start Time"')

    return start_time, end_time


def string_to_base64(string):
    """
    Convert string to base64 format
    :param string: {str} string to convert
    :return: {str} base64 string
    """
    return base64.b64encode(str.encode(string)).decode()


def behaviour_check_value(value) -> bool:
    """
    Validates behavior filter values
    :param string: {csv} comma separated values
    :return: {bool} Boolean
    """
    val_set = set(word.lower().strip() for word in value.split(","))
    return len(val_set - BEHAVIOUR_VISIBILITY_FILTER_VALUES) == 0


def extract_connector_param_wrapper(
    siemplify: SiemplifyConnectorExecution,
    param_name: str,
    default_value: Any | None = None,
    input_type: type = str,
    is_mandatory: bool = False,
    print_value: bool = False,
    remove_whitespaces: bool = True,
) -> Any:
    """Wrapper for extract_connector_param method from TIPCommon

    Args:
        siemplify: The Siemplify object.
        param_name: The name of the parameter to extract.
        default_value: The default value to return if the parameter is not found.
        input_type: The type of the parameter.
        is_mandatory: Whether the parameter is mandatory.
        print_value: Whether to print the value of the parameter.
        remove_whitespaces: Whether to remove whitespaces from the value of the parameter.

    Returns:
        Any: The value of the parameter.
    """
    try:
        return extract_connector_param(
            siemplify,
            param_name=param_name,
            default_value=default_value,
            input_type=input_type,
            is_mandatory=is_mandatory,
            print_value=print_value,
            remove_whitespaces=remove_whitespaces,
        )
    except ValueError as err:
        err_msg = f"The value must be {input_type.__name__}"
        raise ParameterValidationError(
            param_name=param_name,
            value=None,
            message=err_msg,
            print_value=False,
            print_error=False,
        ) from err


def hours_to_milliseconds(hours: int) -> int:
    return int(datetime.timedelta(hours=hours).total_seconds() * MILI_SECOND)


def calculate_last_success_time(
    siemplify: SiemplifyConnectorExecution,
    hours_backwards: int,
    padding_time: int | None = None,
) -> int:
    """Calculates the last success time, considering padding time.

    Args:
        siemplify: Siemplify connector execution instance.
        hours_backwards: Number of hours to look back.
        padding_time: Padding time in hours.

    Returns:
        int: The calculated last success timestamp.

    Raises:
        InvalidTimeException: If padding time is invalid.
    """
    last_success_timestamp = get_last_success_time(
        siemplify=siemplify,
        offset_with_metric={"hours": hours_backwards},
        time_format=UNIX_FORMAT,
    )

    if padding_time is not None:
        if not 0 <= padding_time <= MAX_PADDING_TIME:
            raise InvalidTimeException(
                f"Padding Time value must be in range 0 to {MAX_PADDING_TIME}"
            )

        padding_period = unix_now() - (padding_time * MILLISECONDS_IN_HOUR)
        if last_success_timestamp > padding_period:
            last_success_timestamp = padding_period
            siemplify.LOGGER.info(
                "Last success timestamp is greater than the padding period "
                f"({padding_time} hours). {last_success_timestamp} will be used "
                "as the last success timestamp."
            )

    return last_success_timestamp
