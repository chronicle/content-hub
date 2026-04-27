from __future__ import annotations
from datetime import datetime, timedelta, timezone
from .constants import (
    TIME_FRAME_LAST_HOUR,
    TIME_FRAME_LAST_6HOURS,
    TIME_FRAME_LAST_WEEK,
    TIME_FRAME_LAST_24HOURS,
    TIME_FRAME_LAST_MONTH,
)


def prepare_timestamp_statement(time_frame):
    """
    Get start and end time timestamps from range
    :param time_frame: {str} Time range string
    :return: {tuple} start and end time timestamps
    """

    start_time = None
    end_time = None

    if time_frame == TIME_FRAME_LAST_HOUR:
        start_time = datetime.utcnow() - timedelta(hours=1)
    if time_frame == TIME_FRAME_LAST_6HOURS:
        start_time = datetime.utcnow() - timedelta(hours=6)
    if time_frame == TIME_FRAME_LAST_24HOURS:
        start_time = datetime.utcnow() - timedelta(hours=24)
    if time_frame == TIME_FRAME_LAST_WEEK:
        now = datetime.utcnow()
        today_datetime = datetime(
            year=now.year, month=now.month, day=now.day, hour=0, second=0
        )
        start_time = today_datetime + timedelta(-today_datetime.weekday(), weeks=-1)
        end_time = today_datetime + timedelta(-today_datetime.weekday())

    if time_frame == TIME_FRAME_LAST_MONTH:
        now = datetime.utcnow()
        today_datetime = datetime(
            year=now.year, month=now.month, day=now.day, hour=0, second=0
        )
        end_time = today_datetime.today().replace(
            day=1, hour=0, minute=0, second=0
        ) - timedelta(days=1)
        start_time = today_datetime.today().replace(
            day=1, hour=0, minute=0, second=0
        ) - timedelta(days=end_time.day)
        end_time = end_time + timedelta(days=1)

    if start_time is not None:
        start_time = start_time.replace(tzinfo=timezone.utc).isoformat()

    if end_time is not None:
        end_time = end_time.replace(tzinfo=timezone.utc).isoformat()

    return start_time, end_time


def validate_integer_param(param_to_validate, param_name):
    """
    Validating if the parameter is an integer or not.
    :param param_to_validate: {any} The parameter value to check.
    :param param_name: {str} The parameter name to check.
    :return:
    """
    if type(param_to_validate) != int:
        raise Exception(f"'{param_name}' is not of type integer")
