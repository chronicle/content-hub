from __future__ import annotations
import datetime

from TIPCommon.smp_time import convert_datetime_to_unix_time
from . import consts
from .exceptions import AzureSecurityCenterValidationException


def load_csv_to_list(csv: str, param_name: str) -> list:
    """
    Load comma separated values represented as string to a list
    :param csv: {str} of comma seperated values with delimiter ','
    :param param_name: {str} the name of the variable we are validation
    :return: {list} of values
            raise AzureSecurityCenterValidationException if failed to parse csv
    """
    try:
        return [t.strip() for t in csv.split(",")]
    except Exception:
        raise AzureSecurityCenterValidationException(
            f"Failed to parse parameter {param_name}"
        )


def get_mapped_value(mappings, key):
    """
    Returns mapped value of 'key' parameter. if key does not exist in mappings -
    an AzureSecurityCenterValidationException will be thrown.

    :param mappings: {dict} of mapped keys to values
    :param key: {str} key to check if there is mapped value in mappings.
    :return: {str} value of key in mappings if key exists in mappings dictionary.
             otherwise raise AzureSecurityCenterValidationException
    """
    if key not in mappings:
        raise AzureSecurityCenterValidationException(
            f"Failed to validate parameter {key}"
        )
    return mappings.get(key)


def datetime_to_string(
    datetime_obj: datetime.datetime, time_format=consts.TIME_FORMAT
) -> str:
    """
    Convert datetime object to date string representation
    :param datetime_obj: {datetime.datetime} The datetime object to convert
    :param time_format: {str} The time format to convert the datetime object to. For example - "%Y-%m-%dT%H:%M:%SZ"
    :return: {str} The string representation of the datetime
    """
    return datetime_obj.strftime(time_format)


def get_valid_time(time_str: str):
    """
    Validates time string has 6 milliseconds precision at most.
    :param time_str: {str} time in format '2020-03-15T04:24:55.4284961Z'
    :return: time_str: {str} time in format '2020-03-15T04:24:55.428496Z' ("%Y-%m-%dT%H:%M:%S.%fZ")
    """
    try:
        time_str_parts = time_str.rsplit("Z")[0].rsplit(".")
        milli_seconds = time_str_parts[1] if len(time_str_parts) > 1 else "000"
        milli_seconds = milli_seconds[:6]
        return time_str[:19] + "." + milli_seconds + "Z"
    except Exception as e:
        return time_str[:19] + ".000Z"


def convert_string_to_unix_time(time_str: str):
    """
    Convert string time of format 2020-03-15T04:24:55.4284961Z or 2020-03-15T04:24:55Z to unix time in ms.
    Some time formats contain nano second granularity, which cannot be parsed with datetime object, therefore it's trimmed
    to 5 digits precision.
    :param time_str: {str} time in format '2020-03-15T04:24:55.4284961Z'
    :return: {int} unix time in ms
    """
    try:
        dt = datetime.datetime.strptime(get_valid_time(time_str), consts.TIME_FORMAT)
        return convert_datetime_to_unix_time(dt)
    except Exception as e:
        return 1


def slice_list_to_max_sublists(data: list, max_size_sublist: int):
    """
    Slice list into sublists. Each sublist will have max size of <max_size_sublist>
    :param data: {[]} list of values to split to sublists
    :param max_size_sublist: {int} max size of sublist
    :return: {[[]]} list of sublists of max size <max_size_sublist>
    """
    return [
        data[x : x + max_size_sublist] for x in range(0, len(data), max_size_sublist)
    ]


def trim_keys_spaces(d: dict) -> dict:
    """
    Trim dictionary keys from spaces. {'ke y ': 'value'} will be returned as {'key':'value'}
    :param d: {dict} dictionary to trim keys spaces from
    :return: {dict} dictionary without any spaces in keys
    """
    try:
        return {k.replace(" ", ""): v for k, v in d.items()}
    except Exception:
        return d
