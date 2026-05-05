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
from enum import Enum
from inspect import getmembers, isfunction
from typing import Any

from jinja2 import Environment
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.types import SingleJson

from ..core import JinjaFilters


class ExecutionScope(Enum):
    ExecutionScopeUnspecified = 0
    Alert = 1
    Case = 2


INTEGRATION_NAME = "TemplateEngine"

SCRIPT_NAME = "RenderTemplate"


def get_execution_scope(siemplify: SiemplifyAction) -> ExecutionScope:
    """Parse the execution scope from the siemplify action context.

    Args:
        siemplify: The SiemplifyAction orchestration instance.

    Returns:
        The determined ExecutionScope enum value (defaults to Alert).
    """
    raw_scope = getattr(siemplify, "execution_scope", ExecutionScope.Alert.value)
    execution_scope_value = ExecutionScope.Alert.value
    try:
        if hasattr(raw_scope, "value"):
            raw_scope = raw_scope.value

        str_scope = str(raw_scope).strip().title()
        if str_scope.isdigit():
            execution_scope_value = ExecutionScope(int(str_scope)).value
        else:
            execution_scope_value = ExecutionScope[str_scope].value
    except Exception as e:
        siemplify.LOGGER.error(f"Failed to parse execution scope: {e}.")

    return ExecutionScope(execution_scope_value)


def _extract_alert_data(
    alert: Any,
    entities_source: list[Any],
    events: list[SingleJson],
    entities: dict[str, SingleJson],
) -> None:
    """Extract security events and entities from a single alert context.

    Args:
        alert: The target alert SDK object instance.
        entities_source: List of entity object contexts (alert entities or target entities).
        events: List container to accumulate events additional properties dictionaries.
        entities: Dictionary container to accumulate unique filename/address/etc. entities properties.
    """
    events.extend(
        event.additional_properties
        for event in getattr(alert, "security_events", [])
    )
    entities.update({
        entity.additional_properties.get("Identifier")
        or entity.identifier: entity.additional_properties
        for entity in entities_source
        if entity.additional_properties.get("Type") != "ALERT"
    })


def extract_context_data(
    execution_scope: ExecutionScope,
    current_alert: Any = None,
    target_entities: list[Any] | None = None,
    case_alerts: list[Any] | None = None,
    logger: Any = None,
) -> dict[str, list[SingleJson] | dict[str, SingleJson]]:
    """Extract security events and entities based on execution scope.

    Args:
        execution_scope: The determined ExecutionScope for playbook run (Alert or Case).
        current_alert: The current alert SDK instance (optional).
        target_entities: List of target entities from Siemplify (optional).
        case_alerts: List of alerts associated with the case (optional).

    Returns:
        A single dictionary containing lists of security events and
        dictionaries of entities.
    """
    events: list[SingleJson] = []
    entities: dict[str, SingleJson] = {}

    if execution_scope == ExecutionScope.Alert:
        if current_alert:
            _extract_alert_data(
                current_alert,
                target_entities or [],
                events,
                entities,
            )
    else:
        for alert in case_alerts or []:
            try:
                _extract_alert_data(
                    alert,
                    getattr(alert, "entities", []),
                    events,
                    entities,
                )
            except Exception as e:
                if logger:
                    identifier = getattr(alert, "identifier", "unknown")
                    logger.warning(
                        "Skipping alert %s extraction in case scope "
                        "due to error: %s.",
                        identifier,
                        e,
                    )

    return {
        "SiemplifyEvents": events,
        "SiemplifyEntities": entities,
    }


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    execution_scope = get_execution_scope(siemplify)
    case_data = extract_context_data(
        execution_scope=execution_scope,
        current_alert=siemplify.current_alert,
        target_entities=siemplify.target_entities,
        case_alerts=getattr(siemplify.case, "alerts", []),
        logger=siemplify.LOGGER,
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
                    entry.update(case_data)
                result_value += template.render(entry, input_json=entry)
                output_message = "Successfully rendered the template."
        elif isinstance(input_json, dict):
            if include_case_data:
                input_json.update(case_data)
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
