# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import datetime
import dateutil.parser
import time

from .consts import (
    ACTION_TIMEOUT_THRESHOLD_IN_SEC,
    DATETIME_FORMAT,
    NUM_OF_HOURS_IN_DAY,
    NUM_OF_MILLI_IN_SEC,
    RFC_3339_TIME_FORMAT,
    _TIMEFRAME_MAPPING,
    TIMEOUT_THRESHOLD,
    UNIX_FORMAT,
)
from .exceptions import InvalidTimeException

from SiemplifyUtils import (
    convert_datetime_to_unix_time,
    convert_string_to_unix_time,
    pytz,
    unix_now,
    utc_now,
)


def change_timezone(dtime, current_tz, new_tz):
    # type: (datetime.datetime, str, str) -> datetime.datetime
    """Change a timezone of a datetime.datetime object

    Args:
        dtime (datetime.datetime): The datetime object to change its timezone
        current_tz (str): The current timezone
        new_tz (str): The timezone to change to

    Raises:
        ValueError: If one of the timezones is not valid

    Returns:
        datetime.datetime: A new datetime object with a new timezone
    """
    if current_tz not in pytz.all_timezones_set:
        raise ValueError(
            'The provided current time zone is not listed in '
            'pytz.all_timezones. Please check if it was parsed correctly.\n'
            'Current time zone: "{0}"'.format(current_tz)
        )

    if new_tz not in pytz.all_timezones_set:
        raise ValueError(
            'The provided new time zone is not listed in '
            'pytz.all_timezones. Please check if it was parsed correctly.\n'
            'New time zone: "{0}"'.format(new_tz)
        )

    ctz = pytz.timezone(current_tz)
    ntz = pytz.timezone(new_tz)

    if dtime.tzname() is None:
        dtime = ctz.localize(dtime)

    return dtime.astimezone(ntz)


def validate_timestamp(
    last_run_timestamp,
    offset_in_hours,
    offset_is_in_days=False
):
    """Validates timestamp in range.

    Args:
        last_run_timestamp (datetime): The last run timestamp.
        offset_in_hours (int): The time limit in hours.
        offset_is_in_days (bool, optional): Whether the offset is in days. Defaults to False.

    Raises:
        ValueError: If the timestamp is not valid.

    Returns:
        datetime: The validated timestamp.
    """

    current_time = utc_now()

    if offset_is_in_days:
        offset_in_hours = offset_in_hours * NUM_OF_HOURS_IN_DAY

    if current_time - last_run_timestamp > datetime.timedelta(
        hours=offset_in_hours
    ):
        return current_time - datetime.timedelta(hours=offset_in_hours)
    else:
        return last_run_timestamp


def save_timestamp(
    siemplify,
    alerts,
    timestamp_key='timestamp',
    incrementation_value=0,
    log_timestamp=True,
    convert_timestamp_to_micro_time=False,
    convert_a_string_timestamp_to_unix=False
):
    """Saves last timestamp for given alerts.

    Args:
        siemplify (obj): An instance of the SDK `SiemplifyConnectorExecution` class.
        alerts (dict): The list of alerts to find the last timestamp.
        timestamp_key (str, optional): The key for getting timestamp from alert. Defaults to 'timestamp'.
        incrementation_value (int, optional): The value to increment last timestamp by milliseconds. Defaults to 0.
        log_timestamp (bool, optional): Whether log timestamp or not. Defaults to True.
        convert_timestamp_to_micro_time (bool, optional): Whether to convert timestamp to micro time. Defaults to False.
        convert_a_string_timestamp_to_unix (bool, optional): Whether to convert a string timestamp to unix. Defaults to False.

    Returns:
        bool: Whether the timestamp is updated.
    """

    if not alerts:
        siemplify.LOGGER.info(
            'Timestamp is not updated since no alerts fetched'
        )
        return False

    if convert_a_string_timestamp_to_unix:
        alerts = sorted(
            alerts,
            key=lambda alert: convert_string_to_unix_time(
                getattr(alert, timestamp_key)
            )
        )
        last_timestamp = convert_string_to_unix_time(
            getattr(alerts[-1], timestamp_key)
        ) + incrementation_value
    else:
        alerts = sorted(
            alerts,
            key=lambda alert: int(getattr(alert, timestamp_key))
        )
        last_timestamp = int(
            getattr(alerts[-1], timestamp_key)
        ) + incrementation_value

    last_timestamp = last_timestamp * NUM_OF_MILLI_IN_SEC if convert_timestamp_to_micro_time else last_timestamp
    if log_timestamp:
        siemplify.LOGGER.info('Last timestamp is :{}'.format(last_timestamp))

    siemplify.save_timestamp(new_timestamp=last_timestamp)
    return True


def get_last_success_time(
    siemplify,
    offset_with_metric,
    time_format=DATETIME_FORMAT,
    print_value=True,
    microtime=False
):
    """Get last success time datetime.

    Args:
        siemplify (obj): An instance of the SDK SiemplifyConnectorExecution class.
        offset_with_metric (dict): The metric and value. Ex: {'hours': 1}
        time_format (int): The format of the output time. Ex: DATETIME, UNIX
        print_value (bool, optional): Whether to print the value or not. Defaults to True.
        microtime (bool, optional): Whether to return unix time including microtime. Defaults to False.

    Returns:
        time: The last success time.
    """

    last_run_timestamp = siemplify.fetch_timestamp(datetime_format=True)
    offset = datetime.timedelta(**offset_with_metric)
    current_time = utc_now()
    # Check if first run
    datetime_result = current_time - offset if current_time - last_run_timestamp > offset else last_run_timestamp
    unix_result = convert_datetime_to_unix_time(datetime_result)
    unix_result = unix_result if not microtime else int(
        unix_result / NUM_OF_MILLI_IN_SEC
        )

    if print_value:
        siemplify.LOGGER.info(
            'Last success time. Date time:{}. Unix:{}'.format(
                datetime_result,
                unix_result
            )
        )
    return unix_result if time_format == UNIX_FORMAT else datetime_result


def siemplify_fetch_timestamp(siemplify, datetime_format=False, timezone=False):
    """Fetches timestamp from Siemplify.

    Args:
        siemplify (obj): An instance of the SDK `SiemplifyConnectorExecution` class.
        datetime_format (bool, optional): Whether to return the timestamp in datetime format. Defaults to False.
        timezone (bool, optional): Whether to return the timestamp in UTC timezone. Defaults to False.

    Returns:
        The timestamp.
    """
    last_time = siemplify.fetch_timestamp(
        datetime_format=datetime_format,
        timezone=timezone
    )
    if last_time == 0:
        siemplify.LOGGER.info(
            'Timestamp key does not exist in the database. Initiating with value: 0.'
        )
    return last_time


def siemplify_save_timestamp(
    siemplify,
    datetime_format=False,
    timezone=False,
    new_timestamp=unix_now()
):
    """Saves timestamp to Siemplify.

    Args:
        siemplify (obj): An instance of the SDK `SiemplifyConnectorExecution` class.
        datetime_format (bool, optional): Whether to save the timestamp in datetime format. Defaults to False.
        timezone (bool, optional): Whether to save the timestamp in UTC timezone. Defaults to False.
        new_timestamp (int): The new timestamp to save.

    Returns:
        None
 """
    siemplify.save_timestamp(
        datetime_format=datetime_format,
        timezone=timezone,
        new_timestamp=new_timestamp
    )


def is_approaching_timeout(
    connector_starting_time,
    python_process_timeout,
    timeout_threshold=TIMEOUT_THRESHOLD
):
    """Checks if a timeout is approaching.

    Args:
        connector_starting_time (int): The time the connector started.
        python_process_timeout (int): The maximum amount of time the connector is allowed to run.
        timeout_threshold (float): The threshold at which the connector is considered to be approaching a timeout. Defaults to `TIMEOUT_THRESHOLD`.

    Returns:
        `True` if the connector is approaching a timeout, `False` otherwise.
    """
    processing_time_ms = unix_now() - connector_starting_time
    return processing_time_ms > python_process_timeout * NUM_OF_MILLI_IN_SEC * timeout_threshold


def is_approaching_action_timeout(
    action_execution_deadline_in_unix,
    timeout_threshold_in_sec=ACTION_TIMEOUT_THRESHOLD_IN_SEC
):
    """Check if action script is approaching its dedicated script deadline.

    Each action script has a specific deadline dedicated to it.
    This function checks if the current time is less than the deadline
    by at least timeout_threshold_in_sec seconds.
    The default is 10 seconds, meaning that if the action is 10 or less seconds
    from its script deadline (at the time of the check) this will return True,
    else False.

    Args:
        action_execution_deadline_in_unix (int):
        timeout_threshold_in_sec (int):

    Returns:
        True - if timeout approaching, False - otherwise.
    """
    seconds_until_timeout = action_execution_deadline_in_unix - unix_now()
    return seconds_until_timeout <= timeout_threshold_in_sec


def datetime_to_rfc3339(datetime_obj):
    # type: (datetime.datetime) -> str
    """Convert datetime object to RFC 3999 representation.

    Args:
        datetime_obj (datetime.datetime): The datetime object to convert.

    Returns:
        str: The RFC 3339 representation of the datetime.
    """
    return datetime_obj.strftime(RFC_3339_TIME_FORMAT)


def convert_string_to_timestamp(datetime_string):
    # type: (str) -> int
    """Convert a datetime string to a timestamp.

    Args:
        datetime_string (str): Datetime string.

    Returns:
        int: The timestamp.
    """
    datetime_object = dateutil.parser.parse(datetime_string)
    return datetime.datetime.timestamp(datetime_object)


def get_timestamps_from_range(range_string, include_timezone=False):
    # type: (str, bool) -> tuple[datetime.datetime, datetime.datetime]
    """Get start and end time timestamps from range.

    Args:
        range_string (str): Time range string.
        include_timezone (bool, optional): Whether to include timezone
        information in timestamps.Defaults to False.

    Returns:
        tuple: Start and end time timestamps.
    """
    now = datetime.datetime.utcnow()
    today_datetime = datetime.datetime(
        year=now.year,
        month=now.month,
        day=now.day,
        hour=0,
        second=0
    )
    timeframe = _TIMEFRAME_MAPPING.get(range_string)

    if isinstance(timeframe, dict):
        start_time, end_time = now - datetime.timedelta(**timeframe), now
    elif timeframe == _TIMEFRAME_MAPPING.get("Last Week"):
        start_time = today_datetime + datetime.timedelta(
            -today_datetime.weekday(),
            weeks=-1
        )
        end_time = today_datetime + datetime.timedelta(
            -today_datetime.weekday()
        )

    elif timeframe == _TIMEFRAME_MAPPING.get("Last Month"):
        end_time = today_datetime.today().replace(
            day=1,
            hour=0,
            minute=0,
            second=0
        ) - datetime.timedelta(days=1)
        start_time = today_datetime.today().replace(
            day=1,
            hour=0,
            minute=0,
            second=0
        ) - datetime.timedelta(days=end_time.day)
        end_time = end_time + datetime.timedelta(days=1)
    else:
        return None, None

    if include_timezone:
        return start_time.replace(
            tzinfo=datetime.timezone.utc
        ).timestamp(), end_time.replace(
            tzinfo=datetime.timezone.utc
        ).timestamp()

    return start_time, end_time


def get_timestamps(
    range_string,
    start_time_string,
    end_time_string,
    error_message=None,
    time_in_milliseconds=False
):
    # type: (str, str, str, str, bool) -> tuple[int, int]
    """Get start and end time timestamps.

    Args:
        range_string: {str} Time range string
        start_time_string: {str} Start time
        end_time_string: {str} End time
        error_message: {str} Error message for raised exception
        time_in_milliseconds: {bool} Whether to return start_time and
        end_time in milliseconds.Defaults to False.

    Return:
        tuple: start and end time timestamps
    """
    start_time, end_time = get_timestamps_from_range(
        range_string,
        include_timezone=True
    )

    if not start_time and start_time_string:
        start_time = convert_string_to_timestamp(start_time_string)

    if not end_time and end_time_string:
        end_time = convert_string_to_timestamp(end_time_string)

    if not start_time:
        raise InvalidTimeException(error_message)

    if not end_time:
        end_time = time.time()

    if time_in_milliseconds:
        return int(start_time) * 1000, int(end_time) * 1000

    return start_time, end_time
