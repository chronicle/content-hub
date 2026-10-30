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

import codecs
import itertools
import json
import math
import os
from types import NoneType
from typing import Any, Iterator

from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time, convert_string_to_datetime

from csv_integration.core.constants import DEFAULT_PATH
from EnvironmentCommon.EnvironmentHandle import GetEnvironmentCommonFactory
from csv_integration.core.exceptions import (
    CSVAbsolutePathNotFoundError,
    CSVDirectoryFoundError,
    CSVEncodingException,
)


def string_to_multi_value(string_value, delimiter=",", only_unique=False):
    """
    String to multi value.
    :param string_value: {str} String value to convert multi value.
    :param delimiter: {str} Delimiter to extract multi values from single value string.
    :param only_unique: {bool} include only uniq values
    :return: {dict} fixed dictionary.
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


def get_value_for_search(column_name):
    if isinstance(column_name, str):
        return column_name.lower()

    return column_name


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def replace_spaces_with_underscore(value):
    """
    Remove spaces from string
    :param value: {str}
    :return: {str} string with underscores instead of spaces
    """
    return value.replace(" ", "_")


def get_existing_column_names(df_item_info, columns_to_check):
    return list(filter(lambda field: field in df_item_info.columns, columns_to_check))


def get_encodings_or_raise(siemplify, encodings):
    """
    Validate given encodings.
    :param siemplify: {Siemplify}
    :param encodings: {list} List of file encoding types
    :return valid_encodings: {list} List of only valid encoding types from the list given by user
    """
    valid_encodings = []
    for encoding in encodings:
        try:
            codecs.lookup(encoding)
            valid_encodings.append(encoding)
        except LookupError as e:
            siemplify.LOGGER.error(
                f"Given encoding type {encoding} doesn't exist, this type won't be used for "
                "decoding your CSV files."
            )
            siemplify.LOGGER.exception(e)
    if not valid_encodings:
        raise CSVEncodingException(
            "Provided encodings are invalid. Please check the spelling."
        )
    return valid_encodings


# Move to TIPCommon
def get_environment_common(
    siemplify, environment_field_name, environment_regex_pattern, map_file="map.json"
):
    """
    Get environment common
    :param siemplify: {siemplify} Siemplify object
    :param environment_field_name: {string} The environment field name
    :param environment_regex_pattern: {string} The environment regex pattern
    :param map_file: {string} The map file
    :return: {EnvironmentHandle}
    """
    return GetEnvironmentCommonFactory.create_environment_manager(
        siemplify,
        environment_field_name,
        environment_regex_pattern,
        map_file
    )


# Move to TIPCommon
def is_overflowed(siemplify, alert_info, is_test_run):
    """
    Check if overflowed
    :param siemplify: {Siemplify} Siemplify object.
    :param alert_info: {AlertInfo}
    :param is_test_run: {bool} Whether test run or not.
    :return: {bool}
    """
    try:
        return siemplify.is_overflowed_alert(
            environment=alert_info.environment,
            alert_identifier=alert_info.ticket_id,
            alert_name=alert_info.rule_generator,
            product=alert_info.device_product,
        )

    except Exception as err:
        siemplify.LOGGER.error(f"Error validation connector overflow, ERROR: {err}")
        siemplify.LOGGER.exception(err)
        if is_test_run:
            raise

    return False


def calculate_row_time(
    siemplify, *, row, csv_path, time_field_name, time_field_timezone
):
    """
    Calculate record time in unix time
    :param siemplify: siemplify connector instance
    :param row: {dict} csv record data
    :param csv_path: {str} csv file path
    :param time_field_name: {str} field name - from where to fetch the time
    :param time_field_timezone: {str} Timezone in which the time field is
    :return: {long} record time
    """

    # Get file time
    file_time = (
        int(os.path.getctime(csv_path)) * 1000
    )  # The function return seconds(milliseconds required).
    record_time = row.get(time_field_name, int(file_time))

    try:
        # Check if time is in unix time
        time = int(record_time)
    except:
        try:
            # Check if time is time format
            time = convert_datetime_to_unix_time(
                convert_string_to_datetime(
                    record_time, timezone_str=time_field_timezone
                )
            )
            siemplify.LOGGER.info(
                f"Convert time to unix time. Before: {record_time}. After: {time}"
            )
        except Exception as e:
            siemplify.LOGGER.error(
                f"Failed to convert time: {record_time} to unix time."
            )
            siemplify.LOGGER.exception(e)
            time = 1

    return time


CUSTOM_CONFIGURATION_FILE_NAME = "severity_map_config.json"
DEFAULT_SEVERITY_VALUE = 50
CUSTOM_MAPPING_CONFIGURATION = {}
CONFIGURATION_DATA = {}


def load_custom_severity_configuration(
    severity_field_name, file_path=CUSTOM_CONFIGURATION_FILE_NAME
):
    global DEFAULT_SEVERITY_VALUE
    global CUSTOM_MAPPING_CONFIGURATION
    global CONFIGURATION_DATA

    conf_data = {}
    if os.path.isfile(file_path):
        with open(file_path, "r") as f:
            try:
                conf_data = json.load(f)
            except:
                pass

    DEFAULT_SEVERITY_VALUE = conf_data.get("Default", DEFAULT_SEVERITY_VALUE)
    CUSTOM_MAPPING_CONFIGURATION = conf_data.get(
        severity_field_name, CUSTOM_MAPPING_CONFIGURATION
    )

    with open(file_path, "w") as f:
        conf_data = {"Default": DEFAULT_SEVERITY_VALUE}
        if severity_field_name:
            conf_data[severity_field_name] = CUSTOM_MAPPING_CONFIGURATION
        CONFIGURATION_DATA = conf_data
        f.write(json.dumps(conf_data, indent=4))


def map_severity_value(severity_field_name, alert_data):
    """
    The function calculates case priority by the Priority Map.
    :param severity_field_name: {str} severity field name
    :param alert_data: {dict} flat event data
    :return: {int} calculated Siemplify alarm priority
    """
    default_severity = severity_field_name or DEFAULT_SEVERITY_VALUE

    if not severity_field_name:
        return default_severity

    severity_value = alert_data.get(severity_field_name, DEFAULT_SEVERITY_VALUE)
    severity_score = DEFAULT_SEVERITY_VALUE
    try:
        severity_score = math.ceil(float(severity_value))
    except:
        severity_dict = CONFIGURATION_DATA.get(severity_field_name)
        if severity_dict:
            severity_score = severity_dict.get(severity_value) or DEFAULT_SEVERITY_VALUE

    return min(100, max(-1, severity_score))


def list_of_dict_to_single_dict(list_of_dict, join_str=","):
    """
    Convert list of dict to single dict with multiple values joined by join_str.
    :param list_of_dict: {list} list of dicts
    :param join_str: {str} the string to join multiple values, if None value will be list
    :return: {dict} result dict
    """
    result_dict = {}
    for single_dict in list_of_dict:
        for key, value in single_dict.items():
            previous_value = result_dict.get(key, set())
            previous_value.add(value)
            result_dict[key] = previous_value
    if join_str:
        return {key: join_str.join(value) for key, value in result_dict.items()}
    return result_dict


def get_file_path(file_path: str, overwrite: bool = False) -> str:
    """Adding validation to the file_path file and returning with updated path.

    Args:
        file_path (str): File path provided in parameter "File Path
        overwrite (bool, optional): File overwrite flag. Defaults to False.

    Raises:
        CSVDirectoryFoundError: Expected filename but found directory in system
            with same name.
        FileExistsError: File found but action param "Overwrite" disabled.

    Returns:
        str: Returns file name.
    """
    if os.path.isdir(file_path):
        raise CSVDirectoryFoundError(
            'Directory already exists with value provided in "File Path" ' "parameter."
        )

    file_path = (
        file_path
        if os.path.dirname(file_path)
        else os.path.join(DEFAULT_PATH, file_path)
    )

    if not os.path.isabs(file_path):
        raise CSVAbsolutePathNotFoundError(
            "Action only works with absolute file paths."
        )

    if not overwrite and os.path.isfile(file_path):
        raise FileExistsError(
            "file with the same file path already exists. Please delete it or "
            'set "Overwrite" action parameter to true.'
        )

    return file_path


def flatten_json_vertically(
    data: Any, max_rows: int = 500_000, sep: str = "_"
) -> list[dict[str, Any]]:
    """Flattens a JSON-like Python object into a list of flat dictionaries.

    This function unnests dictionaries and expands lists to create a table-like
    structure (a list of flat dictionaries), where each dictionary represents a row.

    - Nested dictionary keys are concatenated with the parent key using `sep`.
    - Lists are expanded vertically, creating a new row for each item.
    - If a dictionary contains multiple lists, a Cartesian product of their
      elements is generated, creating a row for each possible combination.

    Args:
        data (Any): The JSON-like object (dict, list, scalar) to flatten.
        max_rows (int, optional): The maximum number of rows to generate to
            prevent memory issues with large Cartesian products.
            Defaults to 500_000.
        sep (str, optional): The separator to use when joining nested keys.
            Defaults to "_".

    Returns:
        list[dict[str, Any]]: A list of flattened dictionaries. Returns an
            empty list if the input data is empty.

    Complexity: Output-Sensitive. O(min(R, M) * W).
        R: max_rows, M: number of rows generated by Cartesian product, W: work per row.

    Example:
        >>> data = {
        ...     "id": "p1",
        ...     "colors": ["red", "blue"],
        ...     "details": {"material": "cotton", "sizes": ["S", "M"]}
        ... }
        >>> flatten_json_vertically(data, sep='_')
        [
            {'id': 'p1', 'colors': 'red', 'details_material': 'cotton',
             'details_sizes': 'S'},
            {'id': 'p1', 'colors': 'red', 'details_material': 'cotton',
             'details_sizes': 'M'},
            {'id': 'p1', 'colors': 'blue', 'details_material': 'cotton',
             'details_sizes': 'S'},
            {'id': 'p1', 'colors': 'blue', 'details_material': 'cotton',
             'details_sizes': 'M'}
        ]
    """
    if not data:
        return []

    iterator = _flatten_json_generator(data, sep=sep)

    results = []
    count = 0

    for row in iterator:
        results.append(row)
        count += 1
        if count >= max_rows:
            break

    return results


def _flatten_leaf(item: Any, key: str) -> Iterator[dict[str, Any]]:
    if isinstance(item, (str, int, float, bool, NoneType)):
        yield {key: str(item) if item is not None else ""}


def _flatten_list(
    items: list, key: str, sep: str
) -> Iterator[dict[str, Any]]:
    if not items:
        yield {}  # Outer Join behavior
        return

    for item in items:
        yield from _flatten_json_generator(item, key, sep)


def _flatten_dict(
    item: dict, key: str, sep: str
) -> Iterator[dict[str, Any]]:
    if not item:
        yield {key: ""} if key else {}
        return

    scalars = {}
    iterables = []

    for k, v in item.items():
        new_key = f"{key}{sep}{k}" if key else k

        if isinstance(v, (dict, list)):
            branch_rows = list(_flatten_json_generator(v, new_key, sep))
            if not branch_rows:
                iterables.append([{}])
            else:
                iterables.append(branch_rows)
        else:
            scalars[new_key] = str(v) if v is not None else ""

    if not iterables:
        yield scalars
        return

    if len(iterables) == 1:
        for row in iterables[0]:
            yield scalars | row
        return

    for combination in itertools.product(*iterables):
        merged_row = scalars.copy()
        for part in combination:
            merged_row.update(part)
        yield merged_row


def _flatten_json_generator(
    item: Any, parent_key: str = "", sep: str = "_"
) -> Iterator[dict[str, Any]]:
    if isinstance(item, (str, int, float, bool, NoneType)):
        yield from _flatten_leaf(item, parent_key)
    elif isinstance(item, list):
        yield from _flatten_list(item, parent_key, sep)
    elif isinstance(item, dict):
        yield from _flatten_dict(item, parent_key, sep)
