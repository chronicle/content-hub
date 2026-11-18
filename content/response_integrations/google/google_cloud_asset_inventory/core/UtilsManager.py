# Copyright 2026 Google LLC
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

from __future__ import annotations

from collections import deque
import copy
import json

from bs4 import BeautifulSoup

from soar_sdk.SiemplifyLogger import SiemplifyLogger
from TIPCommon.rest.gcp import validate_impersonation

from .constants import NOT_FOUND_STATUS, FORBIDDEN_STATUS, RATE_LIMIT_STATUS
from .exceptions import (
    InsufficientResourcePermissionError,
    ProjectOrOrganizationNotFoundError,
    GoogleCloudAssetInventoryError,
    MaximumRequestLimitError,
)


def validate_response(status_code: int, content: str | bytes) -> None:
    """Validate response.

    Args:
        status_code: The response status code from the request API
        content: The response content

    Raises:
        InsufficientResourcePermissionError: No resources permissions
        ProjectOrOrganizationNotFoundError: Org / Project not found
        MaximumRequestLimitError: Rate limit reached
        GoogleCloudAssetInventoryError: Generic Integration Exception
        ImpersonationUnauthorizedError: Service Account Impersonation Unauthorized
    """

    if 200 <= status_code < 400:
        return

    try:
        content = json.loads(content)
    except json.decoder.JSONDecodeError:
        pass

    message = get_error_message_from_response(status_code, content)
    validate_impersonation(content, message)

    if status_code == FORBIDDEN_STATUS:
        raise InsufficientResourcePermissionError(f"{message}")

    if status_code == NOT_FOUND_STATUS:
        raise ProjectOrOrganizationNotFoundError(f"{message}")

    if status_code == RATE_LIMIT_STATUS:
        raise MaximumRequestLimitError(f"{message}")

    raise GoogleCloudAssetInventoryError(f"{message}")


def get_error_message_from_response(
    status_code: int, content: bytes | dict, error_msg: str = "An error occurred"
) -> str:
    """Gets the error message from the response content.

    Args:
        status_code: Response status code
        content: Response content
        error_msg: Generic error message to be applied at the beginning of each
            error message

    Returns:
        An error message
    """

    if isinstance(content, dict):
        message = content.get("error", {}).get("message")
        error_text = message
    else:
        error_text = BeautifulSoup(content, "html.parser").p.text
    return f"{error_msg}: {error_text}\nResponse Status Code: {status_code}"


def merge_dicts(target_dict: dict, update_dict: dict) -> None:
    """Merges update_dict data to the target_dict recursively.

    Note: If path fully matches this WILL OVERRIDE target_dict data with
        value from update_dict for that path.

    Args:
        target_dict: Target dictionary that will be updated
        update_dict: Dictionary that will serve as a data source for update
    """
    for key, value in update_dict.items():
        if isinstance(value, dict) and key in target_dict:
            merge_dicts(target_dict[key], value)
            continue

        if isinstance(value, list) and key in target_dict:
            if all(isinstance(el, dict) for el in value):
                for target_el, source_el in zip(target_dict[key], value):
                    merge_dicts(target_el, source_el)
                continue

        target_dict[key] = value


def exclude_fields_from_dict(
    logger: SiemplifyLogger, json_data: dict, fields_to_exclude: list[list[str]]
) -> dict:
    """Excludes fields from the json_data.

    The provided dict will be updated in place, nothing returned.

    Args:
        logger: Logger object
        json_data: dict to adjust
        fields_to_exclude: List of field paths to be excluded

    Raises:
        KeyError: if any of the field paths is not present in the json_data

    Returns:
        An updated dictionary with fields excluded
    """
    resulting_json_data = copy.deepcopy(json_data)

    for field in fields_to_exclude:
        try:
            _field = deque(field)
            exclude_path_from_dict(resulting_json_data, _field)

        except KeyError:
            logger.warn(
                f'Key with path {".".join(field)} was not found in' f"json data."
            )

    return resulting_json_data


def exclude_path_from_dict(json_data: dict | list[dict], field_path: deque[str]):
    """Recursively traverse a dict by path and remove specified path.

    Args:
        json_data: Initial json data to extract from
        field_path: Field path of what to exclude from the dict

    Raises:
        KeyError: if any of the paths is not present in json_data
    """

    current_field = field_path.popleft()

    if isinstance(json_data, dict):
        if not field_path:
            del json_data[current_field]
            return

        exclude_path_from_dict(json_data[current_field], field_path)

    elif isinstance(json_data, list):
        for _temp_json_el in json_data:
            if not field_path:
                del _temp_json_el[current_field]
                return

            exclude_path_from_dict(_temp_json_el[current_field], field_path)


def extract_fields_from_dict(
    logger: SiemplifyLogger, initial_json_data: dict, fields_to_return: list[list[str]]
) -> dict:
    """Extracts only specified fields from the json_data.

    The new dict will be returned built based on the provided one.

    Args:
        logger: Logger object
        initial_json_data: dict to use as a base
        fields_to_return: List of field paths to be returned

    Raises:
        KeyError: if any of the field paths is not present in the json_data

    Returns:
        The resulting dictionary
    """
    resulting_json_data = {}

    for field in fields_to_return:

        try:
            _field = deque(field)
            _update_dict = extract_path_from_dict(initial_json_data, _field)
            merge_dicts(resulting_json_data, _update_dict)

        except KeyError:
            logger.warn(
                f'Key with path {".".join(field)} was not found in '
                f"json data. Please recheck if the path is present in full "
                f"JSON and all of its keys are NOT excluded."
            )

    return resulting_json_data


def extract_path_from_dict(
    json_data: dict | list[dict], field_path: deque[str]
) -> dict:
    """Recursively build a dictionary that will include only specified path.

    Args:
        json_data: Initial json data to extract from
        field_path: Field path of what to include in the result

    Raises:
        KeyError: if any of the paths is not present in json_data

    Returns:
        A dictionary with only specified path present
    """
    __temp_json = {}

    if not field_path:
        return json_data

    current_field = field_path.popleft()

    if isinstance(json_data, dict):
        __temp_json[current_field] = extract_path_from_dict(
            json_data[current_field], field_path=field_path
        )

    elif isinstance(json_data, list):
        __temp_json = [
            {
                current_field: extract_path_from_dict(
                    _temp_json_el[current_field], field_path=field_path
                )
            }
            for _temp_json_el in json_data
        ]

    else:
        raise KeyError(current_field)

    return __temp_json
