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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction


def try_parse_float_or_int(s):
    try:
        return int(s, 10)
    except ValueError:
        return float(s)


def main():
    siemplify = SiemplifyAction()

    function = siemplify.parameters.get("Function")

    arg_1_str = siemplify.parameters.get("Arg 1")
    arg_2_str = siemplify.parameters.get("Arg 2")

    arg_1 = try_parse_float_or_int(arg_1_str)
    arg_2 = try_parse_float_or_int(arg_2_str)

    result_value = False
    output_message = f"No function {function} found."
    if function == "Plus":
        result_value = arg_1 + arg_2
        output_message = f"{arg_1} + {arg_2} = {result_value}"

    elif function == "Sub":
        result_value = arg_1 - arg_2
        output_message = f"{arg_1} - {arg_2} = {result_value}"

    elif function == "Multi":
        result_value = arg_1 * arg_2
        output_message = f"{arg_1} * {arg_2} = {result_value}"

    elif function == "Div":
        result_value = arg_1 / arg_2
        output_message = f"{arg_1} / {arg_2} = {result_value}"

    elif function == "Mod":
        result_value = arg_1 % arg_2
        output_message = f"{arg_1} % {arg_2} = {result_value}"

    siemplify.end(output_message, result_value, EXECUTION_STATE_COMPLETED)


if __name__ == "__main__":
    main()
