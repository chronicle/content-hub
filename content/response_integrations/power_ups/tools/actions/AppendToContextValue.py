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
from soar_sdk.SiemplifyUtils import output_handler

GLOBAL_CONTEXT = 0
IDENTIFIER = "GLOBAL"


def get_global_context(smp, key):
    """Get a global context property.

    :param smp: The SMP object.
    :param key: The key of the property to get.
    :return: The value of the property.
    """
    return smp.get_context_property(GLOBAL_CONTEXT, IDENTIFIER, key)


def set_global_context(smp, key, value):
    """Sets a global context property.

    :param smp: The SMP object.
    :param key: The key of the property.
    :param value: The value of the property.
    """
    smp.set_context_property(GLOBAL_CONTEXT, IDENTIFIER, key, value)


@output_handler
def main():
    siemplify = SiemplifyAction()
    output_message = (
        "output message :"  # human readable message, showed in UI as the action result
    )

    scope = siemplify.extract_action_param(
        param_name="Scope",
        is_mandatory=True,
        print_value=True,
        default_value="Alert",
    )
    key = siemplify.extract_action_param(
        param_name="Key",
        is_mandatory=True,
        print_value=True,
    )
    value = siemplify.extract_action_param(
        param_name="Value",
        is_mandatory=True,
        print_value=True,
    )
    delim = siemplify.extract_action_param(
        param_name="Delimiter",
        is_mandatory=True,
        print_value=True,
        default_value=",",
    )

    result_value = None
    try:
        if scope == "Alert":
            result_value = siemplify.get_alert_context_property(key)
            if result_value:
                siemplify.set_alert_context_property(key, result_value + delim + value)
                result_value = result_value + delim + value
            else:
                siemplify.set_alert_context_property(key, value)
                result_value = value

        elif scope == "Case":
            result_value = siemplify.get_case_context_property(key)
            if result_value:
                siemplify.set_case_context_property(key, result_value + delim + value)
                result_value = result_value + delim + value
            else:
                siemplify.set_case_context_property(key, value)
                result_value = value

        elif scope == "Global":
            result_value = get_global_context(siemplify, key)
            if result_value:
                set_global_context(siemplify, key, result_value + delim + value)
                result_value = result_value + delim + value
            else:
                set_global_context(siemplify, key, value)
                result_value = value

        if result_value:
            result_value = result_value.strip('"')
            output_message = f"Successfully appended field {key} with value '{value}' in scope {scope}."
        else:
            output_message = (
                f"Key: {key} in scope {scope} didn't exist, it's now created"
            )
    except Exception as e:
        output_message = f"Error: {e}"
        result_value = False

    siemplify.end(output_message, result_value, EXECUTION_STATE_COMPLETED)


if __name__ == "__main__":
    main()
