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
import io
import json
import re
from collections.abc import Iterable

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED
from ..core.SiemplifyUtilitiesManager import SiemplifyUtilitiesManager
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_action_param

ACTION_NAME = "Siemplify_Filter JSON"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    result_value = ""
    output_message = ""

    # Parameters.
    escape_json_data_strings = extract_action_param(
        siemplify,
        param_name="Escape JSON Data Input",
        input_type=bool
    )
    json_data = extract_action_param(
        siemplify,
        param_name="JSON Data",
        default_value="{}"
    )

    try:
        json_dict = json.loads(json_data)

    except json.JSONDecodeError as e:
        try:
            if not escape_json_data_strings:
                raise e

            json_dict = json.loads(escape_unescaped_quotes(json_data))

        except json.JSONDecodeError as err:
            siemplify.LOGGER.error(err)
            output_message = (
                "Invalid JSON format detected. Please verify the structure and "
                "content of the JSON."
            )
            siemplify.end(output_message, result_value, EXECUTION_STATE_FAILED)
            return

    root_path = siemplify.parameters.get("Root Key Path", "")
    condition_path = siemplify.parameters["Condition Path"]
    condition_operator = siemplify.parameters["Condition Operator"]
    condition_value = siemplify.parameters["Condition Value"]
    output_path = siemplify.parameters.get("Output Path", "")
    delimiter = siemplify.parameters.get("Delimeter", ",")

    if root_path:
        condition_path = ".".join([root_path, condition_path])

        if output_path:
            output_path = ".".join([root_path, output_path])

    filtered_json = SiemplifyUtilitiesManager.filter_json(
        json_dict, condition_path, condition_operator, condition_value
    )
    result_json = SiemplifyUtilitiesManager.find_values_in_dict(
        filtered_json, root_path
    )

    if output_path:
        result_json = SiemplifyUtilitiesManager.get_result_from_output_path(
            filtered_json, output_path
        )

        result_values = SiemplifyUtilitiesManager.find_values_in_dict(
            filtered_json, output_path
        )

        is_json = False

        for result in result_values:
            if not isinstance(result, str):
                is_json = True
                break

        if is_json:
            result_value = json.dumps(result_values)

        else:
            result_value = delimiter.join(result_values)

    else:
        result_value = json.dumps(result_json)

    siemplify.result.add_result_json(result_json)
    output_message = "Successfully filtered JSON."

    siemplify.end(output_message, result_value)


def escape_unescaped_quotes(json_like_str: str) -> str:
    """
    Escapes unescaped double quotes and backslashes within JSON string values
    in a given string.

    Args:
        json_like_str: The string containing JSON-like data.

    Returns:
        The string with properly escaped JSON string values.
    """
    value_ranges: list[tuple[int, int]] = find_json_string_value_ranges(json_like_str)
    escaped_json_string: io.StringIO = io.StringIO()
    last_end: int = 0

    for start, end in value_ranges:
        escaped_json_string.write(json_like_str[last_end:start])
        escaped_value: str = escape_string_value(json_like_str[start:end])
        escaped_json_string.write(escaped_value)
        last_end = end

    escaped_json_string.write(json_like_str[last_end:])

    return escaped_json_string.getvalue()


def find_json_string_value_ranges(json_like_str: str) -> list[tuple[int, int]]:
    """Finds the start and end indices of JSON string values within a string.

    Args:
        json_like_str: The string to search within.

    Returns:
        A list of tuples, where each tuple contains the start and end index
        of a JSON string value.
    """
    match_json_value_string_start: str = r':\s*"'
    match_json_value_string_end: str = r'"\s*(?=,|$)'

    matches_start: Iterable[re.Match] = re.finditer(
        match_json_value_string_start, json_like_str
    )
    matches_end: Iterable[re.Match] = re.finditer(
        match_json_value_string_end, json_like_str
    )

    return [
        (match_start.end(), match_end.start())
        for match_start, match_end in zip(matches_start, matches_end)
    ]


def escape_string_value(value: str) -> str:
    """Escapes unescaped backslashes and double quotes within a string.

    Args:
        value: The string value to escape.

    Returns:
        The escaped string value.
    """
    unescaped_escape_characters: str = r'\\(?![nt"\\])'
    escape_unescaped: str = r"\\\\"

    modified: str = re.sub(unescaped_escape_characters, escape_unescaped, value)
    modified = re.sub(r'(?<!\\)"', r"\"", modified)
    return modified


if __name__ == "__main__":
    main()
