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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction


def try_parse_float(s, val=None):
    try:
        return float(s)
    except ValueError:
        return val


def try_parse_int(s, val=None):
    try:
        return int(s, 10)
        # print(number)
    except ValueError:
        return val


def _get_int_elements(items):
    numbers = []
    for item in items:
        int_val_after_parse = try_parse_int(item)
        if int_val_after_parse:
            numbers.append(int_val_after_parse)
    return numbers


def main():
    siemplify = SiemplifyAction()

    numbers_csv_str = siemplify.parameters.get("Numbers", "")
    function = siemplify.parameters.get("Function")

    items = numbers_csv_str.split(",")
    numbers = []
    updated_numbers = []
    for item in items:
        float_val_after_parse = try_parse_float(item)
        int_val_after_parse = try_parse_int(item)

        if float_val_after_parse:
            numbers.append(float_val_after_parse)
        elif int_val_after_parse:
            numbers.append(int_val_after_parse)

    output_message = ""
    result = True

    if function == "Abs":
        for number in numbers:
            updated_number = abs(number)
            updated_numbers.append(updated_number)
        output_message = f"{numbers} successfully converted to {updated_numbers} with abs function"

    elif function == "Float":
        for number in numbers:
            updated_number = abs(number)
            updated_numbers.append(updated_number)
        output_message = f"{numbers} successfully converted to {updated_numbers} with float function"

    elif function == "Display":
        for number in numbers:
            updated_number = f"{number:,}"
            updated_numbers.append(updated_number)
        output_message = f"Successfully converted {numbers} to {updated_numbers}"

    elif function == "Hex":
        int_array = _get_int_elements(items)
        for int_item in int_array:
            updated_number = hex(int_item)
            updated_numbers.append(updated_number)
        output_message = f"{numbers} successfully converted to {updated_numbers} with hex function"

    elif function == "Int":
        for number in numbers:
            updated_number = int(number)
            updated_numbers.append(updated_number)
        output_message = f"{numbers} successfully converted to {updated_numbers} with int function"

    elif function == "Max":
        max_number = max(numbers)
        output_message = f"Max number in {numbers} is {max_number}."
        result = max_number

    elif function == "Min":
        min_number = min(numbers)
        output_message = f"Min number in {numbers} is {min_number}."
        result = min_number

    elif function == "Round":
        for number in numbers:
            updated_number = round(number)
            updated_numbers.append(updated_number)
        output_message = f"{numbers} successfully converted to {updated_numbers} with round function"

    elif function == "Sort":
        updated_numbers = sorted(numbers)
        output_message = f"{numbers} successfully converted to {updated_numbers} with sorted function"

    elif function == "Sum":
        sum_array = sum(numbers)
        output_message = f"Sum of array {numbers} is {sum_array}."
        result = sum_array

    siemplify.result.add_result_json(json.dumps(updated_numbers))
    siemplify.result.add_json(f"Input after {function}", json.dumps(updated_numbers))

    if len(updated_numbers) == 1:
        result = updated_numbers[0]
    siemplify.end(output_message, result, EXECUTION_STATE_COMPLETED)


if __name__ == "__main__":
    main()
