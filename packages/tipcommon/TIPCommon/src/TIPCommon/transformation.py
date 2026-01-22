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

from __future__ import annotations

import copy
import json
from typing import TYPE_CHECKING

from .exceptions import InternalJSONDecoderError


if TYPE_CHECKING:
    from typing import Any

    from collections.abc import Hashable, Sequence

    from .types import SingleJson


def to_string(value: Any) -> str:
    """Converts any value to a string, returning an empty string for None.
    This is a general-purpose utility to ensure a value is a string.

    Args:
        value: The value to convert.

    Returns:
        The string representation of the value.
    """
    if value is None:
        return ""

    return str(value)


def convert_dict_to_json_result_dict(
    json_result: str | SingleJson,
    title_key: str = "Entity",
    results_key: str = "EntityResult",
) -> list[SingleJson]:
    """Converts a key-value JSON result to a list of JSON result objects.

    Args:
        json_result: Key-value JSON result as a string or dictionary.
        title_key: The key for the original dictionary's keys.
        results_key: The key for the original dictionary's values.

    Returns:
        A list of JSON result objects.

    Raises:
        InternalJSONDecoderError: If json_result is a string that cannot be
        parsed.
        ValueError: If json_result is not a dictionary after parsing.
    """
    if isinstance(json_result, str):
        try:
            json_result = json.loads(json_result)

        except json.JSONDecodeError as e:
            raise InternalJSONDecoderError(
                "Could not parse the json result from str to dict"
            ) from e

    if not isinstance(json_result, dict):
        raise ValueError(
            f"Attempting to convert wrong type {type(json_result)} to"
            " list[dict]. The json_result param must be a dict or a string"
            " that can be parsed to a dict."
        )

    return [{title_key: k, results_key: v} for k, v in json_result.items()]


def construct_csv(list_of_dicts: Sequence[SingleJson]) -> list[str]:
    """Constructs a CSV from a list of dictionaries.
    This version fixes the column ordering issue while preserving the legacy
    comma-replacement logic for backward compatibility.

    Args:
        list_of_dicts: A list of dictionaries to be converted to CSV format.

    Returns:
        A list of strings, where each string is a row in the CSV file.
    """
    if not list_of_dicts:
        return []

    headers: list[str] = []
    seen_headers: set[str] = set()
    for dict_item in list_of_dicts:
        for key in dict_item.keys():
            if key not in seen_headers:
                seen_headers.add(key)
                headers.append(key)

    csv_output: list[str] = []
    unicode_headers: list[str] = [to_string(h) for h in headers]
    csv_output.append(",".join(unicode_headers))

    for result in list_of_dicts:
        csv_row: list[str] = []
        for header in headers:
            cell_value: Any = result.get(header)
            cell_value = to_string(cell_value)
            cell_value = cell_value.replace(",", " ")
            csv_row.append(cell_value)
        csv_output.append(",".join(csv_row))

    return csv_output


def dict_to_flat(target_dict: SingleJson) -> SingleJson:
    """Receives a nested dictionary and returns it as a flat dictionary.

    Args:
        target_dict: The dictionary to flatten.

    Returns:
        The flattened dictionary.
    """
    target_dict = copy.deepcopy(target_dict)

    def _expand(raw_key: str, raw_value: Any) -> list[tuple[str, str]]:
        """Private recursive function to expand a nested dictionary."""
        key: str = to_string(raw_key)
        value: Any = raw_value

        if value is None:
            return [(key, "")]

        elif isinstance(value, dict):
            return [
                (f"{key}_{to_string(sub_key)}", to_string(sub_value))
                for sub_key, sub_value in dict_to_flat(value).items()
            ]

        elif isinstance(value, list):
            items: list[tuple[str, str]] = []
            count: int = 1
            for item in value:
                new_key: str = f"{key}_{count}"
                if isinstance(item, (dict, list)):
                    items.extend(_expand(new_key, item))
                else:
                    items.append((new_key, to_string(item)))
                count += 1

            return items

        else:
            return [(key, to_string(value))]

    items: list[tuple[str, str]] = [
        item
        for sub_key, sub_value in target_dict.items()
        for item in _expand(sub_key, sub_value)
    ]

    return dict(items)


def flat_dict_to_csv(
    flat_dict: SingleJson,
    property_header: str = "Property",
    value_header: str = "Value",
) -> list[str]:
    """Turns a flat dictionary into a list of strings in CSV format.

    Args:
        flat_dict: The dictionary to convert to CSV format.
        property_header: The header for the property column.
        value_header: The header for the value column.

    Returns:
        The list of strings in CSV format.
    """
    csv_format: list[str] = [f"{property_header},{value_header}"]
    for key, value in flat_dict.items():
        safe_key: str = to_string(key)
        safe_value: str = to_string(value)
        csv_format.append(f"{safe_key},{safe_value}")

    return csv_format


def add_prefix_to_dict(given_dict: SingleJson, prefix: str) -> SingleJson:
    """Adds a prefix to the keys of a given dictionary.

    Args:
        given_dict: The dictionary to add the prefix to.
        prefix: The prefix to add.

    Returns:
        The dictionary with the prefix added to the keys.
    """
    return {
        f"{to_string(prefix)}_{to_string(key)}": value
        for key, value in given_dict.items()
    }


add_prefix_to_dict_keys = add_prefix_to_dict
"""An alias for `add_prefix_to_dict` for backward compatibility."""


def string_to_multi_value(
    string_value: str,
    delimiter: str = ",",
    only_unique: bool = False,
) -> list[str]:
    """Converts a delimited string to a list of values.

    Args:
        string_value: The string to convert.
        delimiter: The delimiter to split the string on.
        only_unique: If True, only include unique values.

    Returns:
        The list of values.
    """
    if not string_value:
        return []

    values: list[str] = [
        single_value.strip()
        for single_value in string_value.split(delimiter)
        if single_value.strip()
    ]
    if only_unique:
        return list(dict.fromkeys(values))

    return values


def convert_comma_separated_to_list(
    comma_separated: str,
    delimiter: str = ",",
) -> list[str]:
    """Converts a comma-separated string to a list of values.

    Args:
        comma_separated: The comma-separated string to convert.
        delimiter: The delimiter to parse the string with.

    Returns:
        The list of values.
    """
    return (
        [item.strip() for item in comma_separated.split(delimiter)]
        if comma_separated
        else []
    )


def convert_list_to_comma_string(values_list: list[Any], delimiter: str = ",") -> str:
    """Converts a list of values to a comma-separated string.

    Args:
        values_list: The list of values to convert.
        delimiter: The delimiter to be used in the string.

    Returns:
        The comma-separated string.
    """
    if not isinstance(values_list, list):
        return str(values_list)

    return delimiter.join(str(v) for v in values_list)


def removeprefix(string: str, prefix: str) -> str:
    """Removes a prefix from a string if it exists.

    .. deprecated::
        This standalone function is deprecated in favor of using the built-in
        `str.removeprefix()` method directly (available in Python 3.9+).

    This function provides backward compatibility for callers expecting a
    standalone function, while internally using the efficient built-in
    str.removeprefix() method available in Python 3.9+.

    Args:
        string: The string to remove the prefix from.
        prefix: The prefix to remove.

    Returns:
        The resulting string.
    """
    return string.removeprefix(prefix)


def removesuffix(string: str, suffix: str) -> str:
    """Removes a suffix from a string if it exists.

    .. deprecated::
        This standalone function is deprecated in favor of using the built-in
        `str.removesuffix()` method directly (available in Python 3.9+).

    This function provides backward compatibility for callers expecting a
    standalone function, while internally using the efficient built-in
    str.removesuffix() method available in Python 3.9+.

    Args:
        string: The string to remove the suffix from.
        suffix: The suffix to remove.

    Returns:
        The resulting string.
    """
    return string.removesuffix(suffix)


def rename_dict_key(
    a_dict: dict[Hashable, Any],
    current_key: Hashable,
    new_key: Hashable,
) -> None:
    """Renames a key in a dictionary in-place.

    Args:
        a_dict: The dictionary to modify.
        current_key: The key in a_dict to rename.
        new_key: The new key name.
    """
    if current_key in a_dict:
        a_dict[new_key] = a_dict.pop(current_key)
