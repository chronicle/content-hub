from __future__ import annotations
from soar_sdk.SiemplifyUtils import from_unix_time, convert_string_to_datetime, unix_now
from .exceptions import (
    AWSCloudWatchValidationException,
    AWSCloudWatchInvalidParameterException,
)
from typing import List


def from_timestamp_to_iso_8601(timestamp: int) -> str:
    """
    Convert time as timestamp to ISO-8601 time format.
    :param timestamp: {int} timestamp (1611581795766)
    :return: {str} ISO-8601 time format (2021-01-25T15:36:35Z)
    """
    timestamp_as_datetime = from_unix_time(timestamp)
    return timestamp_as_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")


def load_csv_to_list(csv, param_name):
    """
    Load comma separated values represented as string to a list
    :param csv: {str} of comma separated values with delimiter ','
    :param param_name: {str} the name of the variable we are validation
    :return: {list} of values
            raise AWSGuardDutyValidationException if failed to parse csv
    """
    try:
        return [t.strip() for t in csv.split(",")]
    except Exception as error:
        raise AWSCloudWatchValidationException(
            f"Failed to parse parameter {param_name}"
        ) from error


def remove_empty_kwargs(**kwargs) -> dict:
    """
    Remove keys from dictionary that has the value None
    :param kwargs: key value arguments
    :return: {dict} dictionary without keys that have the value None
    """
    return {k: v for k, v in kwargs.items() if v is not None}


def get_time_frame(start_time: str, end_time: str = None) -> list:
    """
    Get Timeframe
    :param start_time: {str} The start of the timeframe
    :param end_time: {str} The end of the timeframe
    :return: {list} List as time frame [start_time (timestamp), end_time (timestamp)]
    """
    formatted_start_time = format_time(start_time, "Start Time")
    formatted_end_time = (
        format_time(end_time, "End Time") if end_time else int(unix_now())
    )

    validate_unix_timestamp_in_seconds(formatted_start_time)
    validate_unix_timestamp_in_seconds(formatted_end_time)

    validate_time_range([formatted_start_time, formatted_end_time])

    return [formatted_start_time, formatted_end_time]


def format_time(time_to_format, time_name: str):
    """
    Convert time from string to timestamp
    :param time_to_format: {str} Time as string YYYY-MM-DDThh:mm:ssZ
    :param time_name: {str} Name of the time to format. Start Time / End Time
    :return: Time as timestamp. If the time is not time stamp and not of requested format, exception will be raised
    """
    try:
        return int(time_to_format)

    except Exception as error:
        try:
            return int(convert_string_to_datetime(time_to_format).timestamp()) * 1000
        except Exception as error:
            raise AWSCloudWatchInvalidParameterException(
                f"Invalid {time_name} was provided."
            ) from error


def validate_unix_timestamp_in_seconds(timestamp: int) -> int:
    """
    Validate that unix timestamp is provided in seconds
    :param timestamp: {int} Unix timestamp
    :return: {int} provided timestamp.
        raise AWSCloudWatchInvalidParameterException if failed to validate timestamp parameter
    """
    if timestamp < 0 or timestamp > 1999999999 * 1000:
        raise AWSCloudWatchInvalidParameterException(
            f"Failed to validate unix timestamp of {timestamp} as timestamp "
            f"in milliseconds"
        )
    return timestamp


def validate_time_range(time_range: List[int] = None) -> List[int]:
    """
    Validate time range
    :param time_range: {[int,int]} List of 2 unix timestamps in seconds. First value is start time, seconds value is end time
    :return: {[int,int]} Time range provided
        raise AWSCloudWatchInvalidParameterException if failed to validate time range parameter
    """
    validate_unix_timestamp_in_seconds(time_range[0])
    validate_unix_timestamp_in_seconds(time_range[1])
    if time_range[0] > time_range[1]:
        raise AWSCloudWatchInvalidParameterException(
            'Failed to validate "Start Time" and "End Time" parameters.'
        )
    return time_range
