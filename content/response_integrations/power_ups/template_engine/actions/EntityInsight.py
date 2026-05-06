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

import contextlib
import json
import time
from inspect import getmembers, isfunction

import dateutil
from jinja2 import Environment
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler

from ..core import JinjaFilters

# Example Consts:
INTEGRATION_NAME = "TemplateEngine"
SCRIPT_NAME = "Entity Insight"


@output_handler
def filter_datetime(date, fmt=None):
    date = dateutil.parser.parse(date)
    native = date.replace(tzinfo=None)
    format = "%Y/%m/%d %H:%M:%S"
    return native.strftime(format)


def map_priority(p):
    priority = {
        "-1": "info",
        "40": "low",
        "60": "medium",
        "80": "high",
        "100": "critical",
    }
    return priority.get(p)


def timectime(s):
    return time.ctime(s)  # datetime.datetime.fromtimestamp(s)


def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")
    # INIT ACTION PARAMETERS:
    json_object = siemplify.extract_action_param(
        param_name="JSON Object",
        is_mandatory=True,
        print_value=False,
    )
    template = siemplify.extract_action_param(
        param_name="Template",
        is_mandatory=True,
        print_value=False,
    )
    identifier = siemplify.extract_action_param(
        param_name="Triggered By",
        is_mandatory=True,
        print_value=False,
    )

    remove_br = (
        str(
            siemplify.extract_action_param(
                param_name="Remove BRs",
                is_mandatory=False,
                print_value=False,
                default_value="false",
            ),
        ).lower()
        == "true"
    )
    create_insight = (
        str(
            siemplify.extract_action_param(
                param_name="Create Insight",
                is_mandatory=False,
                print_value=False,
                default_value="true",
            ),
        ).lower()
        == "true"
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    entities = {}
    json_result = {}
    for entity in siemplify.target_entities:
        if entity.additional_properties["Type"] != "ALERT":
            entities[entity.additional_properties["Identifier"]] = entity.additional_properties

    try:
        status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
        output_message = "output message :"  # human readable message, showed in UI as the action result
        result_value = None  # Set a simple result value, used for playbook if\else and placeholders.

        if siemplify.target_entities:
            try:
                input_json = json.loads(json_object)
            except Exception as e:
                siemplify.LOGGER.exception(f"Error parsing JSON Object: {json_object}")
                siemplify.LOGGER.exception(e)
                raise
                status = EXECUTION_STATE_FAILED
                result_value = "Failed"
                output_message += "\n failure parsing JSON object."
            jinja_env = Environment(autoescape=True)
            jinja_env = Environment(
                autoescape=True,
                extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols"],
                trim_blocks=True,
                lstrip_blocks=True,
            )
            filters = {name: function for name, function in getmembers(JinjaFilters) if isfunction(function)}

            jinja_env.filters.update(filters)
            try:
                import CustomFilters

                custom_filters = {
                    name: function for name, function in getmembers(CustomFilters) if isfunction(function)
                }
                jinja_env.filters.update(custom_filters)
            except Exception as e:
                siemplify.LOGGER.info("Unable to load CustomFilters")
                siemplify.LOGGER.info(e)

            if remove_br:
                template = template.replace("<br>", "")
            pre_temp = template
            template = jinja_env.from_string(template)
            for entity in siemplify.target_entities:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                result_value = ""
                for entry in input_json:
                    if entry["Entity"].lower() == entity.identifier.lower():
                        update_json = {}
                        with contextlib.suppress(BaseException):
                            update_json = entry["EntityResult"].copy()
                        if isinstance(update_json, dict):
                            update_json["entity"] = entities[entity.identifier].copy()
                        elif isinstance(update_json, list):
                            update_json = {
                                "entity": entities[entity.identifier].copy(),
                                "results": entry["EntityResult"].copy(),
                            }
                        else:
                            msg = f"Unsupported Entity Results type: {type(update_json)}"
                            raise Exception(
                                msg,
                            )
                        result_value += template.render(update_json)
                        res = {"entity_insight": result_value, "template": pre_temp}
                        json_result[entity.identifier] = res
                        siemplify.result.add_entity_json(entity.identifier, res)
                        if create_insight and result_value != "":
                            siemplify.LOGGER.info(
                                f"Creating Insight for entity: {entity.identifier}",
                            )
                            siemplify.add_entity_insight(
                                entity,
                                result_value,
                                triggered_by=identifier,
                            )
                        output_message = "Successfully rendered the template."
    except Exception as e:
        siemplify.LOGGER.exception(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise  # used to return entire error details - including stacktrace back to client UI. Best for most usecases
        # in case you want to handle the error yourself, don't raise, and handle error result ouputs:
        status = EXECUTION_STATE_FAILED
        result_value = "Failed"
        output_message += "\n unknown failure"
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, "", status)


if __name__ == "__main__":
    main()
