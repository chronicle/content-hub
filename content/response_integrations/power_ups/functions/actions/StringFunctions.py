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

import base64
import json
import re

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

PLACEHOLDER_MAP = {"_SPACE_": " "}


def replace_placeholders(text_input: str) -> str:
    """Substitutes predefined placeholders in a string with their
    corresponding literal values from the PLACEHOLDER_MAP.
    """
    # Make a mutable copy to modify
    normalized_text = text_input
    # Loop through the placeholder dictionary and replace each occurrence
    for placeholder, replacement_value in PLACEHOLDER_MAP.items():
        normalized_text = normalized_text.replace(placeholder, replacement_value)
    return normalized_text


@output_handler
def main():
    siemplify = SiemplifyAction()

    input = siemplify.parameters.get("Input")
    function = siemplify.parameters.get("Function")
    param_1 = siemplify.parameters.get("Param 1")
    param_2 = siemplify.parameters.get("Param 2")

    output_message = ""
    result = input

    if function == "Lower":
        result = input.lower()
        output_message = f"{input} successfully converted to {result} with lower function"

    elif function == "Upper":
        result = input.upper()
        output_message = f"{input} successfully converted to {result} with upper function"

    elif function == "Strip":
        result = input.strip()
        output_message = f"{input} successfully converted to {result} with strip function"

    elif function == "Title":
        result = input.title()
        output_message = f"{input} successfully converted to {result} with title function"

    elif function == "Count":
        result = input.count(param_1)
        output_message = f"'{param_1}' was found {result} times in '{input}'"

    elif function == "Replace":
        result = input.replace(replace_placeholders(param_1), replace_placeholders(param_2))
        output_message = f"{input} successfully converted to {result} with replace function"

    elif function == "Find":
        result = input.find(param_1)
        output_message = f"'{param_1}' was found at index {result} in '{input}'"

    elif function == "Upper":
        result = input.upper()
        output_message = f"{input} successfully converted to {result} with upper function"

    elif function == "IsAlpha":
        result = input.isalpha()
        if result:
            output_message = f"All characters in {input} are alphanumeric"
        else:
            output_message = f"Not all characters in {input} are alphanumeric"

    elif function == "IsDigit":
        result = input.isdigit()
        if result:
            output_message = f"All characters in {input} are digits"
        else:
            output_message = f"Not all characters in {input} are digits"

    elif function == "Regex Replace":
        result = re.sub(replace_placeholders(param_1), replace_placeholders(param_2), input)
        output_message = f"{input} successfully converted to {result} with regex replace function"

    elif function == "JSON Serialize":
        result = json.dumps(input)
        output_message = f"{input} successfully serialized to JSON format"

    elif function == "Regex":
        if not param_2:
            param_2 = ", "
        result = param_2.join(re.findall(param_1, input))
        output_message = f"Found following values:\n{result}"

    elif function == "DecodeBase64":
        if not re.match(r"^UTF-8$", param_1) and not re.match(r"^ASCII$", param_1):
            param_1 = "UTF-8"
        result = (base64.b64decode(input)).decode(param_1)
        output_message = f"Decoded base64 string to: {result}"

    elif function == "EncodeBase64":
        if not re.match(r"^UTF-8$", param_1) and not re.match(r"^ASCII$", param_1):
            param_1 = "UTF-8"
        result = (base64.b64encode(input.encode("utf-8"))).decode(param_1)
        output_message = f"Successfully base64 encoded {input}."

    elif function == "RemoveNewLines":
        result = " ".join(input.splitlines())
        output_message = f"{input} successfully removed new lines: {result}"

    elif function == "LogicOperators":
        split_op = ","
        if param_2:
            split_op = param_2
        input_split = [x.strip() for x in input.split(split_op)]
        join_op = f" {param_1} "
        result = join_op.join(input_split)
        output_message = f"{input} successfully converted to: {result}"

    elif function == "Split":
        if param_1:
            split = input.split(f"{param_1}")
            siemplify.result.add_result_json(json.dumps(split))
            result = str(split)
            output_message = f'Successfully split string {input} with delimiter "{param_1}"'

        else:
            split = input.split(",")
            siemplify.result.add_result_json(json.dumps(split))
            result = str(split)
            output_message = f'Successfully split string {input} with delimiter ","'
    siemplify.end(output_message, result, EXECUTION_STATE_COMPLETED)


if __name__ == "__main__":
    main()
