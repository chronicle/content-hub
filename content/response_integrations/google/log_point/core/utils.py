from __future__ import annotations
import re
from . import consts
import datetime
from . import datamodels
from .exceptions import LogPointInvalidParametersException
from soar_sdk.SiemplifyUtils import convert_string_to_datetime
from TIPCommon import unix_now, convert_datetime_to_unix_time
from typing import List, Union


def remove_empty_kwargs(**kwargs) -> dict:
    """
    Remove keys from dictionary that has the value None
    :param kwargs: key value arguments
    :return: {dict} dictionary without keys that have the value None
    """
    return {k: v for k, v in kwargs.items() if v is not None}


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
        raise LogPointInvalidParametersException(
            f"Failed to parse parameter {param_name}"
        ) from error


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
            return int(convert_string_to_datetime(time_to_format).timestamp())
        except Exception as error:
            raise LogPointInvalidParametersException(
                f"Invalid {time_name} was provided."
            ) from error


def get_time_frame(start_time: str, end_time: str = None) -> list:
    """
    Get Timeframe
    :param start_time: {str} The start of the timeframe
    :param end_time: {str} The end of the timeframe
    :return: {list} List as time frame [start_time (timestamp), end_time (timestamp)]
    """
    formatted_start_time = format_time(start_time, "Start Time")
    formatted_end_time = (
        format_time(end_time, "End Time") if end_time else int(unix_now() / 1000)
    )

    validate_unix_timestamp_in_seconds(formatted_start_time)
    validate_unix_timestamp_in_seconds(formatted_end_time)

    validate_time_range([formatted_start_time, formatted_end_time])

    return [formatted_start_time, formatted_end_time]


def get_missing_repos(repos: List[str], found_repos: List[datamodels.Repo]):
    """
    Return missing repos from found repos
    :param repos: {[str]} List of repos to search if missing
    :param found_repos:  {[datamodels.Repo]} List of found repos represented as data models
    :return: {[str]} List of missing repos
    """
    return [
        repo
        for repo in repos
        if repo not in [found_repo.repo for found_repo in found_repos]
    ]


def unix_now_seconds() -> int:
    """
    Return Unix now time in seconds
    :return: {int} Unix now timestamp in seconds
    """
    return int(unix_now() / 1000)


def convert_datetime_str_to_timestamp_seconds(
    datetime_str: str,
) -> (Union[int, str], bool):
    """
    Convert datetime string represented in format "YYYY-MM-DDThh:mm:ssZ" to unix timestamp in seconds
    :param datetime_str: {str} Datetime to convert to unix timestamp
    :return: {({int or str},{bool}) Tuple of unix timestamp in seconds representing the datetime if succeeded to convert, and status
    if succeeded to convert to timestamp in seconds or not. If failed to convert, original parameter will be returned
        raise Exception if failed to validate datetime of format "YYYY-MM-DDThh:mm:ssZ"
    """
    try:
        timestamp_seconds = int(
            convert_datetime_to_unix_time(
                datetime.datetime.strptime(datetime_str, consts.TIME_FORMAT)
            )
            / 1000
        )
        return timestamp_seconds, True
    except Exception:
        return datetime_str, False


def is_valid_email(user_name: str) -> bool:
    """
    Check if the user_name is valid email.
    :param user_name: {str} User name
    :return: {bool} True if valid email, else False
    """
    return bool(re.search(consts.VALID_EMAIL_REGEXP, user_name))


def convert_string_timestamp_to_integer(timestamp: str) -> (Union[int, str], bool):
    """
    Convert string unix timestamp in seconds to integer. Note - unix timestamp must be provided in seconds.
    :param timestamp: {str} Unix timestamp to be converted to integer
    :return: {({int or str},{bool})} Tuple of unix timestamp as integer if succeeded to convert and status if conversion succeeded. If
    conversion failed, original parameter will be returned
    """
    try:
        int_timestamp = int(timestamp)
        return int_timestamp, True
    except Exception:
        return timestamp, False


def validate_date_parameter(date_parameter: str, parameter_name: str) -> int:
    """
    Check if date parameter is of format "YYYY-MM-DDThh:mm:ssZ" or unix timestamp "1611938799" and convert to unix timestamp of type integer
    :param date_parameter: {str} Date parameter of format "YYYY-MM-DDThh:mm:ssZ" or "1611938799"
    :param parameter_name: {str} Parameter name
    :return: {int} Converted unix time
        raise LogPointInvalidParametersException if failed to validate date parameter
    """
    # Check if start time is of format "YYYY-MM-DDThh:mm:ssZ"
    date_parameter, conversion_succeeded = convert_datetime_str_to_timestamp_seconds(
        date_parameter
    )
    if not conversion_succeeded:
        # Check if start time is of unix timestamp
        date_parameter, conversion_succeeded = convert_string_timestamp_to_integer(
            date_parameter
        )
        if not conversion_succeeded:
            raise LogPointInvalidParametersException(
                f'Failed to validate "{parameter_name}" parameter'
            )

    return date_parameter


def validate_time_range(time_range: List[int] = None) -> List[int]:
    """
    Validate time range
    :param time_range: {[int,int]} List of 2 unix timestamps in seconds. First value is start time, seconds value is end time
    :return: {[int,int]} Time range provided
        raise LogPointInvalidParametersException if failed to validate time range parameter
    """
    validate_unix_timestamp_in_seconds(time_range[0])
    validate_unix_timestamp_in_seconds(time_range[1])
    if time_range[0] > time_range[1]:
        raise LogPointInvalidParametersException(
            'Failed to validate "Start Time" and "End Time" parameters.'
        )
    return time_range


def validate_unix_timestamp_in_seconds(timestamp: int) -> int:
    """
    Validate that unix timestamp is provided in seconds
    :param timestamp: {int} Unix timestamp
    :return: {int} provided timestamp.
        raise LogPointInvalidParametersException if failed to validate timestamp parameter
    """
    if timestamp < 0 or timestamp > 1999999999:
        raise LogPointInvalidParametersException(
            f"Failed to validate unix timestamp of {timestamp} as timestamp in seconds"
        )
    return timestamp


def join_queries(queries: List[str], join_operand=consts.OR) -> str:
    """
    Join queries with a given join operand. Default operand is 'or'
    :param queries: {[str]} List of queries to join
    :param join_operand: {str} The operand to join queries with. Can be 'or' or 'and'
    :return: {str} Joined queries
    """
    return f" {join_operand} ".join(queries)


def build_sub_query(operator: str, key: str, values: List[str]) -> str:
    """
    Build sub query. Sub query is built as sequence of key with each of the values, joined by the operator.
    For example if operator='or' and key='ip_address' and values=['10.0.0.1','10.0.0.2'] then the sub query
    that will be returned is ("ip_address"="10.0.0.1" or "ip_address"="10.0.0.2")
    :param operator: {str} Operator to join clauses
    :param key: {str} The key of the query
    :param values: {[str]} List of values
    :return: {str} Build sub query
    """
    sub_query = f" {operator} ".join(f'"{key}"="{value}"' for value in values)
    return f"({sub_query})"
