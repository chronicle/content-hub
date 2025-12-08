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

    events = []
    for event in siemplify.current_alert.security_events:
        events.append(event.additional_properties)
    entities = {}
    for entity in siemplify.target_entities:
        if entity.additional_properties["Type"] != "ALERT":
            entities[entity.additional_properties["Identifier"]] = (
                entity.additional_properties
            )

    # INIT ACTION PARAMETERS:
    json_object = siemplify.extract_action_param(
        param_name="JSON Object",
        is_mandatory=False,
        print_value=False,
        default_value="{}",
    )
    template = siemplify.extract_action_param(
        param_name="Template",
        is_mandatory=False,
        print_value=False,
    )
    jinja = siemplify.extract_action_param(
        param_name="Jinja",
        is_mandatory=False,
        print_value=False,
    )
    include_case_data = (
        str(
            siemplify.extract_action_param(
                param_name="Include Case Data",
                is_mandatory=False,
                print_value=False,
                default_value="true",
            ),
        ).lower()
        == "true"
    )
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        status = EXECUTION_STATE_COMPLETED
        output_message = "output message :"
        result_value = None
        try:
            input_json = json.loads(json_object)

        except Exception as e:
            siemplify.LOGGER.error(f"Error parsing JSON Object: {json_object}")
            siemplify.LOGGER.exception(e)
            raise
            status = EXECUTION_STATE_FAILED
            result_value = "Failed"
            output_message += "\n failure parsing JSON object."
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

        if isinstance(input_json, list):
            result_value = ""
            if jinja:
                template = jinja_env.from_string(jinja)
            else:
                template = jinja_env.from_string(template)
            for entry in input_json:
                if include_case_data:
                    entry.update({"SiemplifyEvents": events})
                    entry.update({"SiemplifyEntities": entities})
                result_value += template.render(entry, input_json=entry)
                output_message = "Successfully rendered the template."
        elif isinstance(input_json, dict):
            if include_case_data:
                input_json.update({"SiemplifyEvents": events})
                input_json.update({"SiemplifyEntities": entities})
                print(input_json)
            if jinja:
                template = jinja_env.from_string(jinja)
            else:
                template = jinja_env.from_string(template)
            result_value = template.render(input_json=input_json)
            output_message = "Successfully rendered the template."
        else:
            siemplify.LOGGER.error("Incorrect type.  Needs to be a list or dict.")

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
