from __future__ import annotations
import base64
import hashlib
import os
from typing import List
from urllib.parse import urlencode

from .consts import ASYNC_ACTION_TIMEOUT_THRESHOLD_MS
from .exceptions import (
    TrendMicroApexCentralValidationError,
    TrendMicroApexCentralPathError,
)


def get_params_to_url(params):
    """
    Convert request params to GET url string params
    :param params: {dict} Dictionary of parameters
    :return: {str} GET encoded url params
    """
    if isinstance(params, dict):
        return "?" + urlencode({k.strip(): v.strip() for k, v in params.items()})
    return ""


def load_csv_to_list(csv: str, param_name: str) -> List[str]:
    """
    Load comma separated values represented as string to a list. Remove duplicates if exist
    :param csv: {str} of comma separated values with delimiter ','
    :param param_name: {str} the name of the parameter we are loading csv to list
    :return: {[str]} List of separated string values
            raise TrendMicroApexCentralValidationError if failed to parse csv string
    """
    try:
        return list(set([t.strip() for t in csv.split(",")]))
    except Exception:
        raise TrendMicroApexCentralValidationError(
            f'Failed to parse parameter "{param_name}"'
        )


def get_base64_string_of_file(file_path):
    """
    Get encoded base64 string of a file
    :param file_path: {str} File path to encode
    :return: {str} Encoded base 64 string
    """
    if not os.path.exists(file_path):
        raise TrendMicroApexCentralPathError(
            f'File path "{file_path}" was not found or not accessible due to restricted '
            f"permissions."
        )
    with open(file_path, "rb") as file:
        encoded_string = base64.b64encode(file.read()).decode("utf-8")
    return encoded_string


def get_sha1_of_file(file_path):
    """
    Get SHA-1 hash of a file.
    :param file_path: {str} File path to hash
    :return: {str} SHA-1 has of the file
    """
    if not os.path.exists(file_path):
        raise TrendMicroApexCentralPathError(
            f'File path "{file_path}" was not found or not accessible due to restricted '
            f"permissions."
        )
    with open(file_path, "rb") as file:
        sha1 = hashlib.sha1(file.read()).hexdigest()
    return sha1


def is_approaching_timeout(action_start_time, python_process_timeout):
    """
    Check if a timeout is approaching.
    :param action_start_time: {int} Action start time
    :param python_process_timeout: {int} The python process timeout
    :return: {bool} True if timeout is close, False otherwise
    """
    return (
        action_start_time > python_process_timeout - ASYNC_ACTION_TIMEOUT_THRESHOLD_MS
    )
