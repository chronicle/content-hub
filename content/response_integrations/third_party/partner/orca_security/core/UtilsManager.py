from __future__ import annotations

import csv
import os

import requests
from soar_sdk.SiemplifyUtils import unix_now

from .OrcaSecurityExceptions import (
    OrcaSecurityDuplicatedDataException,
    OrcaSecurityException,
    OrcaSecurityExistingProcessException,
)

GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1
TIMEOUT_THRESHOLD = 0.9


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {str} Default message to display on error
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        try:
            json_error = response.json().get("error") or response.json().get("errors")
        except Exception:
            raise Exception(f"{error_msg}: {error} {error.response.content}")

        if json_error:
            if json_error == "requested to set same configuration":
                raise OrcaSecurityDuplicatedDataException(json_error)
            elif json_error == "Scan is already running":
                raise OrcaSecurityExistingProcessException(response.json().get("scan_id"))
            else:
                raise OrcaSecurityException(json_error)

        raise Exception(f"{error_msg}: {error} {error.response.content}")

    return True


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


def is_async_action_global_timeout_approaching(siemplify, start_time):
    """
    Check if async action global timeout is approaching.
    :param siemplify: {siemplify} Siemplify object
    :param start_time: {int} Action start time
    :return: {bool} True if timeout is close, False otherwise
    """
    return (
        siemplify.execution_deadline_unix_time_ms - start_time
        < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60
    )


def is_approaching_process_timeout(action_starting_time, python_process_timeout):
    """
    Check if a timeout is approaching.
    :param action_starting_time: {int} Action start time
    :param python_process_timeout: {int} The python process timeout
    :return: {bool} True if timeout is close, False otherwise
    """
    processing_time_ms = unix_now() - action_starting_time
    return processing_time_ms > python_process_timeout * 1000 * TIMEOUT_THRESHOLD


def string_to_multi_value(string_value, delimiter=",", only_unique=False):
    """
    String to multi value.
    :param string_value: {str} String value to convert multi value.
    :param delimiter: {str} Delimiter to extract multi values from single value string.
    :param only_unique: {bool} include only unique values
    :return: {list} fixed list.
    """
    if not string_value:
        return []

    values = [
        single_value.strip()
        for single_value in string_value.split(delimiter)
        if single_value.strip()
    ]
    if only_unique:
        seen = set()
        return [value for value in values if not (value in seen or seen.add(value))]

    return values


def validate_positive_integer(number, err_msg="Limit parameter should be positive"):
    if number <= 0:
        raise Exception(err_msg)


def write_to_csv_file(siemplify, data, file_name="results.csv"):
    """
    Write data to csv file
    :param siemplify: {Siemplify} Siemplify object.
    :param data: {list} List of dicts to write to the file
    :param file_name: {str} The name of the csv file.
    :return: {str} File path
    """
    try:
        file_path = os.path.join(siemplify.run_folder, file_name)
        keys = set().union(*(d.keys() for d in data))
        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))

        with open(file_path, "w", newline="") as f:
            dict_writer = csv.DictWriter(f, keys, restval="-")
            dict_writer.writeheader()
            dict_writer.writerows(data)

        siemplify.LOGGER.info(f"Write assets. Total number of assets = {len(data)}")
        return file_path

    except Exception as e:
        siemplify.LOGGER.error(f"Failed writing data to CSV file. ERROR: {e}")
        siemplify.LOGGER.exception(e)
