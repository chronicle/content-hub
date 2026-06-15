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
from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.rest.soar_api import import_simulator_custom_case
from TIPCommon.types import SingleJson

from ..core import constants
from ..core.ToolsCommon import (
    ExecutionScope,
    get_execution_scope,
)


# The output_handler decorator manages output for Siemplify actions.
@output_handler
def main():
    try:
        siemplify = SiemplifyAction(get_source_file=True)

    except TypeError:
        siemplify = SiemplifyAction()

    raw_scope = getattr(siemplify, "execution_scope", ExecutionScope.Alert.value)
    execution_scope = get_execution_scope(raw_scope, logger=siemplify.LOGGER)

    if execution_scope.value == ExecutionScope.Case.value:
        output_message = "This action doesn't support case playbook feature."
        siemplify.LOGGER.error(output_message)
        siemplify.end(output_message, False, EXECUTION_STATE_FAILED)
        return

    pushToSimulated = siemplify.extract_action_param(
        "Push to Simulated Cases",
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    saveToCaseWall = siemplify.extract_action_param(
        "Save JSON as Case Wall File",
        input_type=bool,
        default_value=False,
        print_value=True,
    )

    overrideName = siemplify.extract_action_param(
        "Override Alert Name",
        default_value="",
        print_value=True,
    )
    fullPathName = siemplify.extract_action_param(
        "Full path name",
        default_value="",
        print_value=True,
    )

    output_message = "Action result: "

    # Check if the 'SourceFileContent' property exists in the alert data before
    # trying to load it.
    if "SourceFileContent" in siemplify.current_alert.entities[0].additional_properties:
        # Load the alert data from the 'SourceFileContent' property.
        case_data = json.loads(
            siemplify.current_alert.entities[0].additional_properties[
                "SourceFileContent"
            ],
        )
    else:
        siemplify.LOGGER.error("Alert data is missing 'SourceFileContent' property")
        return

    # Modify the 'Event Name' fields in the alert data.
    for i, event in enumerate(case_data["Events"]):
        if "DeviceEventClassId" in case_data["Events"][i]["_fields"]:
            case_data["Events"][i]["_rawDataFields"]["DeviceEventClassId"] = case_data[
                "Events"
            ][i]["_fields"]["DeviceEventClassId"]
            case_data["Events"][i]["_rawDataFields"]["Name"] = case_data["Events"][i][
                "_fields"
            ]["DeviceEventClassId"]
        if "deviceEventClassId" in case_data["Events"][i]["_fields"]:
            case_data["Events"][i]["_rawDataFields"]["DeviceEventClassId"] = case_data[
                "Events"
            ][i]["_fields"]["deviceEventClassId"]
            case_data["Events"][i]["_rawDataFields"]["Name"] = case_data["Events"][i][
                "_fields"
            ]["deviceEventClassId"]

    # Optionally modify the 'Name' field in the alert data.
    if fullPathName:
        case_data["Name"] = (
            case_data["SourceSystemName"]
            + "_"
            + case_data["DeviceProduct"]
            + "_"
            + case_data["Name"]
        )
    if overrideName:
        case_data["Name"] = overrideName

    # Prepare the data to be pushed or saved.
    aligned_case_data = align_case_data(case_data)
    myJson = {"cases": [aligned_case_data]}

    # Push the data to the simulator or save it as a JSON file, depending on
    # the parameters.
    if pushToSimulated:
        import_simulator_custom_case(siemplify, myJson)
        output_message += " Pushed to Simulated "

    if saveToCaseWall:
        s = json.dumps(myJson)
        t = base64.b64encode(s.encode("utf-8")).decode("ascii")
        # Add the JSON data as an attachment to the case wall.
        siemplify.result.add_attachment(
            title="<<file in here>>",
            filename=case_data["Name"] + ".case",
            file_contents=t,
        )
        output_message += " Saved to Casewall "
    # The action is complete.
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    # Add the JSON data to the action result and end the action.
    siemplify.result.add_result_json(myJson)
    siemplify.end(output_message, result_value, status)


def align_case_data(case_data: SingleJson) -> SingleJson:
    """Align case data format with custom case import endpoints.
    Args:
        case_data: The dictionary containing the raw case data.

    Returns:
        The aligned case data dictionary.
    """
    case_data_copy = dict(case_data)
    align_case_enum_fields(case_data_copy)

    new_case: SingleJson = {}

    for k, v in case_data_copy.items():
        if k.startswith("__") or v == constants.UNDEFINED_VALUE:
            continue

        camel_k: str = to_camel_case(k)

        if camel_k == "events" and isinstance(v, list):
            new_case[camel_k] = transform_events_list(v)
        else:
            new_case[camel_k] = v

    return new_case


def align_case_enum_fields(case_data: SingleJson) -> None:
    """Align the enum integer fields of a case.
    Args:
        case_data: The dictionary containing the raw case data.
    """
    align_enum_field(case_data, constants.CASE_TYPE_KEYS, constants.CASE_TYPE_MAP)
    align_enum_field(
        case_data,
        constants.DATA_TYPE_KEYS,
        constants.DATA_TYPE_MAP,
    )
    align_enum_field(
        case_data,
        constants.SOURCE_TYPE_KEYS,
        constants.SOURCE_TYPE_MAP,
    )


def align_enum_field(
    data: SingleJson,
    keys: list[str],
    value_map: dict[int, str],
) -> None:
    """Align a single enum field inside a data dictionary.
    Args:
        data: The dictionary containing the raw data.
        keys: The list of keys that represent the enum field.
        value_map: The mapping dictionary for the enum values.
    """
    for key in keys:
        if key in data:
            val: Any = data[key]
            if isinstance(val, int) and not isinstance(val, bool):
                if val in value_map:
                    data[key] = value_map[val]
                else:
                    data.pop(key, None)


def transform_events_list(events: list[Any]) -> list[Any]:
    """Transform a list of events.
    Args:
        events: The list of raw events.

    Returns:
        The list of aligned events.
    """
    new_events: list[Any] = []
    for event in events:
        if isinstance(event, dict):
            new_events.append(transform_event(event))
        else:
            new_events.append(event)
    return new_events


def transform_event(event: SingleJson) -> SingleJson:
    """Transform an event dictionary to align its property names.
    Args:
        event: The raw event dictionary.

    Returns:
        The aligned event dictionary.
    """
    new_event: SingleJson = {}
    for ek, ev in event.items():
        if ek.startswith("__") or ev == constants.UNDEFINED_VALUE:
            continue
        camel_ek: str = to_camel_case(ek)

        if camel_ek in (constants.FIELDS_KEY, constants.DATA_FIELDS_KEY) and isinstance(ev, dict):
            new_event[camel_ek] = {
                k2: v2 for k2, v2 in ev.items() if not k2.startswith("__")
            }
        else:
            new_event[camel_ek] = ev
    return new_event


def to_camel_case(key_name: str) -> str:
    """Convert PascalCase property names to camelCase.
    Args:
        key_name: The string to convert.

    Returns:
        The camelCase converted string.
    """
    if not key_name:
        return key_name
    if key_name == constants.RAW_FIELDS_KEY:
        return constants.FIELDS_KEY
    if key_name == constants.RAW_DATA_FIELDS_KEY:
        return constants.DATA_FIELDS_KEY
    return key_name[0].lower() + key_name[1:]


if __name__ == "__main__":
    main()
