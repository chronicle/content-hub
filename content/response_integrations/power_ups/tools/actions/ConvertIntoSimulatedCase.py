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
def main() -> None:
    try:
        siemplify = SiemplifyAction(get_source_file=True)
    except TypeError:
        siemplify = SiemplifyAction()

    raw_scope = getattr(siemplify, "execution_scope", ExecutionScope.Alert.value)
    if get_execution_scope(raw_scope, logger=siemplify.LOGGER).value == ExecutionScope.Case.value:
        output_message = "This action doesn't support case playbook feature."
        siemplify.LOGGER.error(output_message)
        siemplify.end(output_message, False, EXECUTION_STATE_FAILED)
        return

    pushToSimulated = siemplify.extract_action_param(
        "Push to Simulated Cases", input_type=bool, default_value=False, print_value=True
    )
    saveToCaseWall = siemplify.extract_action_param(
        "Save JSON as Case Wall File", input_type=bool, default_value=False, print_value=True
    )
    overrideName = siemplify.extract_action_param("Override Alert Name", default_value="", print_value=True)
    fullPathName = siemplify.extract_action_param("Full path name", default_value="", print_value=True)

    additional_props = siemplify.current_alert.entities[0].additional_properties
    if "SourceFileContent" not in additional_props:
        siemplify.LOGGER.error("Alert data is missing 'SourceFileContent' property")
        return

    case_data = json.loads(additional_props["SourceFileContent"])
    _enrich_case_metadata(case_data, full_path_name=fullPathName, override_name=overrideName)

    aligned_case_data = align_case_data(case_data)
    myJson = {"cases": [aligned_case_data]}
    output_message = "Action result: "
    if pushToSimulated:
        import_simulator_custom_case(siemplify, myJson)
        output_message += " Pushed to Simulated "
    if saveToCaseWall:
        encoded = base64.b64encode(json.dumps(myJson).encode("utf-8")).decode("ascii")
        siemplify.result.add_attachment(
            title="<<file in here>>",
            filename=sanitize_case_filename(case_data.get("Name") or aligned_case_data.get("name", "")),
            file_contents=encoded,
        )
        output_message += " Saved to Casewall "

    siemplify.result.add_result_json(myJson)
    siemplify.end(output_message, True, EXECUTION_STATE_COMPLETED)


def _enrich_case_metadata(
    case_data: SingleJson,
    full_path_name: str,
    override_name: str,
) -> None:
    """Enrich event class identifiers and update the top-level case name.

    Args:
        case_data: The raw case dictionary to update in place.
        full_path_name: Truthy flag indicating whether to prefix system and product names.
        override_name: Explicit alert name override if provided.
    """
    for event in case_data.get("Events", []):
        if not isinstance(event, dict):
            continue
        fields = event.get("_fields")
        if not isinstance(fields, dict):
            continue
        device_event_class_id = fields.get("DeviceEventClassId") or fields.get("deviceEventClassId")
        if device_event_class_id is not None:
            raw_data_fields = event.setdefault("_rawDataFields", {})
            if isinstance(raw_data_fields, dict):
                raw_data_fields["DeviceEventClassId"] = device_event_class_id
                raw_data_fields["Name"] = device_event_class_id

    if full_path_name:
        source_system = case_data.get("SourceSystemName", "")
        device_product = case_data.get("DeviceProduct", "")
        current_name = case_data.get("Name", "")
        case_data["Name"] = f"{source_system}_{device_product}_{current_name}"
    if override_name:
        case_data["Name"] = override_name


def sanitize_case_filename(name: str) -> str:
    """Sanitize case name to construct a clean .case attachment filename.

    Args:
        name: The raw case or alert name.

    Returns:
        The sanitized filename ending with '.case'.

    """
    if not name:
        return "case.case"
    clean_name = re.sub(r"(\.(case|json|txt))+$", "", name.strip(), flags=re.IGNORECASE)
    clean_name = re.sub(r'[\\/*?:"<>|\n\r\t]', "_", clean_name).strip(" ._")
    return f"{clean_name or 'case'}.case"


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

    if "caseType" in new_case:
        new_case["type"] = new_case["caseType"]

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
        if key not in data:
            continue
        val: Any = data[key]
        mapped_val: str | None = None
        if isinstance(val, int) and not isinstance(val, bool):
            mapped_val = value_map.get(val)
        elif isinstance(val, str):
            stripped = val.strip()
            if stripped.isdigit() and int(stripped) in value_map:
                mapped_val = value_map[int(stripped)]
            elif stripped.upper() in value_map.values():
                mapped_val = stripped.upper()
        if mapped_val is not None:
            data[key] = mapped_val
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
            new_event[camel_ek] = {k2: v2 for k2, v2 in ev.items() if not k2.startswith("__")}
        else:
            new_event[camel_ek] = ev
    return new_event


def to_camel_case(key_name: str) -> str:
    """Convert PascalCase or snake_case property names to camelCase.

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
    canonical_compound_keys = {
        "casetype": "caseType",
        "datatype": "dataType",
        "sourcetype": "sourceType",
    }
    if key_name.lower() in canonical_compound_keys:
        return canonical_compound_keys[key_name.lower()]
    if "_" in key_name and not key_name.startswith("_"):
        parts = [p for p in key_name.split("_") if p]
        return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])
    return key_name[0].lower() + key_name[1:]


if __name__ == "__main__":
    main()
