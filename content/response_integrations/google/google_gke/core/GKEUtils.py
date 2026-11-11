from __future__ import annotations

import json
from typing import Any

from soar_sdk.SiemplifyUtils import unix_now

from google_gke.core.GKEConsts import ASYNC_ACTION_TIMEOUT_THRESHOLD_MS, COMMA_SPACE
from google_gke.core.GKEDatamodels import FilterLogicParam
from google_gke.core.GKEExceptions import GoogleGKEValidationError, InvalidJSONFormatException


def get_filtered_objects(
    objs: list[Any], attribute: str, filter_logic: str, filter_value: str
) -> list[Any]:
    """Get filtered objects.

    Args:
        objs: [{obj}] List of objects to filter
        attribute: {str} Objects attribute to filter
        filter_logic: {str} Enum value of Filter logic parameter
        filter_value: {str} Value to use in the filter

    Returns:
        {[obj]} List of filtered objects
    """
    if filter_logic == FilterLogicParam.EQUAL.value:
        return list(filter(lambda x: getattr(x, attribute) == filter_value, objs))

    if filter_logic == FilterLogicParam.CONTAINS.value:
        return list(filter(lambda x: filter_value in getattr(x, attribute), objs))

    raise GoogleGKEValidationError(
        f'Invalid "Filter Logic" parameter was provided. Possible values are: '
        f"{COMMA_SPACE.join([f.value for f in FilterLogicParam])}"
    )


def is_action_approaching_timeout(python_process_timeout):
    """
    Check if a action script timeout is approaching.
    :param python_process_timeout: {int} The python process timeout
    :return: {bool} True if timeout is approaching, otherwise False
    """
    return unix_now() >= python_process_timeout - ASYNC_ACTION_TIMEOUT_THRESHOLD_MS


def remove_none_values(origin_dict):
    """
    Remove keys from dictionary that has the value None
    :param origin_dict: {dict} Dictionary to process
    :return: {dict} Dictionary without keys that have the value None
    """
    return {k: v for k, v in origin_dict.items() if v is not None}


def parse_string_to_dict(string):
    """
    Parse json string to dict
    :param string: string to parse
    :return: {dict} parsed dict
    """
    try:
        return json.loads(string)
    except Exception as err:
        raise InvalidJSONFormatException(
            f"Unable to parse provided json. Error is: {err}"
        ) from err
