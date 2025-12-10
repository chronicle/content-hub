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
from inspect import getmembers, isfunction

from jinja2 import Environment
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core import JinjaFilters

# Example Consts:
INTEGRATION_NAME = "TemplateEngine"

SCRIPT_NAME = "RenderTemplate"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT ACTION PARAMETERS:
    arrayInput = siemplify.extract_action_param(
        param_name="Array input",
        is_mandatory=False,
        print_value=False,
        default_value="{}",
    )
    jinja = siemplify.extract_action_param(
        param_name="Jinja",
        is_mandatory=False,
        print_value=False,
    )
    join = siemplify.extract_action_param(
        param_name="join",
        is_mandatory=False,
        print_value=False,
        default_value="",
    )
    prefix = siemplify.extract_action_param(
        param_name="prefix",
        is_mandatory=False,
        print_value=False,
        default_value="",
    )
    suffix = siemplify.extract_action_param(
        param_name="suffix",
        is_mandatory=False,
        print_value=False,
        default_value="",
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        status = EXECUTION_STATE_COMPLETED  # Action final status.
        output_message = "output message :"  # Human-readable message for the UI.
        result_value = None  # Simple result value for playbook logic.
        try:
            input_json = json.loads(arrayInput)

        except Exception as e:
            siemplify.LOGGER.error(f"Error parsing JSON Object: {arrayInput}")
            siemplify.LOGGER.exception(e)
            raise
            status = EXECUTION_STATE_FAILED
            result_value = "Failed"
            output_message += "\n failure parsing JSON object."

        # if JSON, make a 1 element array
        if not isinstance(input_json, list):
            input_json = [input_json]

        jinja_env = Environment(
            autoescape=True,
            extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols"],
            trim_blocks=True,
            lstrip_blocks=True,
        )
        filters = {
            name: function
            for name, function in getmembers(JinjaFilters)
            if isfunction(function)
        }

        jinja_env.filters.update(filters)
        try:
            import CustomFilters

            custom_filters = {
                name: function
                for name, function in getmembers(CustomFilters)
                if isfunction(function)
            }
            jinja_env.filters.update(custom_filters)
        except Exception as e:
            siemplify.LOGGER.info("Unable to load CustomFilters")
            siemplify.LOGGER.info(e)

        result_value = ""

        template = jinja_env.from_string(jinja)

        outputArray = []

        for entry in input_json:
            siemplify.LOGGER.info(entry)
            outputArray.append(template.render(entry, row=entry))

        result_value = prefix + join.join(outputArray) + suffix

        output_message = "Successfully rendered the template."

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise  # Return full error details to the client UI. Best for most use cases.
        # For manual error handling, comment out raise and use the lines below:
        status = EXECUTION_STATE_FAILED
        result_value = "Failed"
        output_message += "\n unknown failure"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.result.add_result_json({"html_output": result_value})
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
