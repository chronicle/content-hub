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

import json
from typing import Any

from tldextract import extract
from tldextract.tldextract import ExtractResult

from .constants import LABEL_REGEX

# CONSTS
OPEN_PH_PARENTHASIS = "{"
CLOSE_PH_PARENTHASIS = "}"
PIPE = "|"
DEBUG = True

# new comment


def print_debug(to_print: str, function: str = "") -> None:
    """Print debug messages if DEBUG is enabled."""
    if DEBUG:
        print(f"{function} DEBUG: {to_print}")


def evaluate_function(val: Any, func_name: str, func_values: list[str]) -> Any:
    """Evaluate a pipe function on a given value."""
    if func_name == "default":
        if not val:
            return func_values[0]
        return val
    if func_name == "str":
        return str(val)
    if func_name == "count":
        if not val:
            return "0"
        if isinstance(val, str):
            return "1"
        if isinstance(val, list):
            return len(val)
        if isinstance(val, dict):
            return len(val.keys())
        raise TypeError(f"unsupported object: {val}")
    if func_name == "to_str":
        if isinstance(val, list):
            return ", ".join([str(x) for x in val])
        if isinstance(val, dict):
            return json.dumps(val)
        return str(val)
    if func_name == "join":
        try:
            delimeter = ",".join(func_values)
            return delimeter.join([str(x) for x in val])
        except Exception:
            raise ValueError(val)
    else:
        raise ValueError(f"Unknown pipe function: {func_name}")


def parse_placeholder(curr_json: Any, placeholder: str, pipe: str) -> Any | None:
    """Parse a single placeholder string and evaluates its content against curr_json."""
    pipes = [x.strip() for x in placeholder.split(pipe)]

    for i, function_str in enumerate(pipes):
        first_split = function_str.strip().split("(")
        if len(first_split) > 2:
            raise ValueError(f"Bad format for pipe function: {function_str}")
        if len(first_split) == 1:
            # Assuming key_path here
            if isinstance(curr_json, list) or isinstance(curr_json, dict):
                curr_json = find_key_path_in_json(function_str.split("."), curr_json)
            else:
                return None  # cant find "keys" in a string
        else:  # len is 2
            func_name = first_split[0]
            func_values_string = first_split[1].split(")")[0]
            func_values = [x for x in func_values_string.split(",")]
            curr_json = evaluate_function(curr_json, func_name, func_values)

    return curr_json


def parse_raw_message(
    curr_json: dict[str, Any],
    raw_message: str,
    pipe: str = PIPE,
    open_ph: str = OPEN_PH_PARENTHASIS,
    close_ph: str = CLOSE_PH_PARENTHASIS,
) -> str:
    """Parse a raw message string, replacing placeholders with values from curr_json."""
    new_message = ""
    first_break = raw_message.split(open_ph)
    new_message += first_break[0]
    i = 1
    while i < len(first_break):
        second_break = first_break[i].split(close_ph)
        if len(second_break) < 2:
            raise ValueError(
                f"Missing close PH: '{close_ph}'. Raw message {raw_message}",
            )
        message_shard = parse_placeholder(curr_json, second_break[0], pipe)
        new_message += str(message_shard) + close_ph.join(second_break[1:])
        i += 1

    return new_message


def find_key_path_in_json(key_path: list[str], json_data: Any) -> Any:
    """Find the relevant key_path in a json object.

    If list encountered, this function will return a list of values, one for each
    match in each of the list's elements (using the rest of the keys)
    """
    return find_key_path_recursive(key_path, json_data)


def find_key_path_recursive(
    key_list: list[str],
    current_json: Any,
    iteration: int = 0,
) -> list[Any]:
    """Recursively finds values based on a key path in a JSON-like structure.

    Handles nested dictionaries and lists.
    """
    if key_list:
        if isinstance(current_json, list):
            if key_list:
                ret_list = []
                for element in current_json:
                    ret_list.extend(
                        find_key_path_recursive(
                            key_list,
                            element,
                            iteration=iteration + 1,
                        ),
                    )
                return ret_list

            return current_json
        if isinstance(current_json, dict):
            if key_list[0] in current_json:
                return find_key_path_recursive(
                    key_list[1:],
                    current_json[key_list[0]],
                    iteration=iteration + 1,
                )
            return []
    else:
        if isinstance(current_json, dict):
            return [current_json]
        if isinstance(current_json, list):
            return current_json
        return [
            f"{current_json}",
        ]


def get_entity_by_string(identifier: str, entities: list[Any]) -> Any | None:
    """Find an entity by its identifier string (case-insensitive)."""
    for ent in entities:
        if identifier.lower() == ent.identifier.lower():
            return ent
    return None


def parse_version_string_to_tuple(version: str) -> tuple:
    """Parse version represented as string to tuple.

    :param version: {str} Version represented as string. For example "5.6.1"
    :return: {tuple} Tuple of the version. For example (5,6,1)
    """
    return tuple(map(int, (version.split("."))))


def is_supported_siemplify_version(version: tuple, min_version: tuple) -> bool:
    """Check if Siemplify version is supported.

    :param version: {tuple} Tuple representing siemplify version. Example (5,6,1)
    :param min_version: {Tuple} Tuple representing minimum supported siemplify version.
    Example (5,6,0)
    :return: {bool} True if siemplify version is supported, otherwise False
    """
    return version >= min_version


def get_domain_from_string(identifier: str, extract_subdomain: bool) -> str | None:
    """
    Extract the domain or full subdomain+domain+suffix from a given identifier string.

    Args:
        identifier: The input URL or identifier.
        extract_subdomain: If True, includes subdomain in the result.

    Returns:
        A valid domain string or None if the input is invalid.
    """
    result: ExtractResult = extract(identifier.strip().lower())

    if not (result.domain and is_valid_label(result.domain)):
        return None
    if not (
        result.suffix and all(is_valid_label(part) for part in result.suffix.split("."))
    ):
        return None

    if extract_subdomain:
        if result.subdomain:
            sub_parts = result.subdomain.split(".")
            if all(is_valid_label(part) for part in sub_parts):
                return ".".join(sub_parts + [result.domain, result.suffix])

        return f"{result.domain}.{result.suffix}"

    return f"{result.domain}.{result.suffix}"


def is_valid_label(label: str) -> bool:
    return bool(LABEL_REGEX.fullmatch(label))
