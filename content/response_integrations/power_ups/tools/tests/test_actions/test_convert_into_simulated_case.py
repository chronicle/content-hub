# Copyright 2026 Google LLC
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

import copy
import json
from typing import TYPE_CHECKING

import pytest
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED

from ...actions import ConvertIntoSimulatedCase
from ..common import (
    CONVERT_INTO_SIMULATED_CASE_ALERT_DETAILS_KEY,
    CONVERT_INTO_SIMULATED_CASE_CONTEXT,
    CONVERT_INTO_SIMULATED_CASE_EXPECTED_DATA_KEY,
)
from ..core.product import Tools
from ..core.session import ToolsSession

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


OUTPUT_MESSAGE: str = "Action result:  Pushed to Simulated "
IMPORT_CUSTOM_CASE: str = "importCustomCase"


@pytest.mark.execution_scope("Alert")
@set_metadata(
    parameters={
        "Push to Simulated Cases": True,
        "Save JSON as Case Wall File": False,
        "Override Alert Name": "",
        "Full path name": "",
    },
    input_context=copy.deepcopy(CONVERT_INTO_SIMULATED_CASE_CONTEXT),
)
def test_convert_into_simulated_case_success(
    tools: Tools,
    script_session: ToolsSession,
    load_mock_data: SingleJson,
    action_output: MockActionOutput,
) -> None:
    """Test ConvertIntoSimulatedCase action success."""
    tools.set_alerts_full_details(load_mock_data[CONVERT_INTO_SIMULATED_CASE_ALERT_DETAILS_KEY])

    ConvertIntoSimulatedCase.main()

    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
    assert OUTPUT_MESSAGE in action_output.results.output_message

    assert len(script_session.request_history) == 2
    import_request = script_session.request_history[-1]
    assert import_request.request.method.value == "POST"
    assert IMPORT_CUSTOM_CASE.lower() in import_request.request.url.path.lower()

    payload = import_request.request.kwargs.get("json") or {}
    expected_json = load_mock_data[CONVERT_INTO_SIMULATED_CASE_EXPECTED_DATA_KEY]

    assert payload == expected_json


@pytest.mark.execution_scope("Alert")
@set_metadata(
    parameters={
        "Push to Simulated Cases": True,
        "Save JSON as Case Wall File": False,
        "Override Alert Name": "",
        "Full path name": "",
    },
    input_context=copy.deepcopy(CONVERT_INTO_SIMULATED_CASE_CONTEXT),
)
def test_convert_into_simulated_case_with_casetype(
    tools: Tools,
    script_session: ToolsSession,
    load_mock_data: SingleJson,
    action_output: MockActionOutput,
) -> None:
    """Test ConvertIntoSimulatedCase action converts CaseType integer to string."""
    alert_details = copy.deepcopy(load_mock_data[CONVERT_INTO_SIMULATED_CASE_ALERT_DETAILS_KEY])
    alert_details[0]["domain_entities"][0]["additional_properties"]["SourceFileContent"] = json.dumps({
        "Name": "Simulated Alert",
        "CaseType": 1,
        "DataType": 1,
        "SourceType": 1,
        "Events": [],
    })
    tools.set_alerts_full_details(alert_details)

    ConvertIntoSimulatedCase.main()

    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
    assert OUTPUT_MESSAGE in action_output.results.output_message

    import_request = script_session.request_history[-1]
    payload = import_request.request.kwargs.get("json") or {}
    case = payload["cases"][0]
    assert case["caseType"] == "EXTERNAL"
    assert case["type"] == "EXTERNAL"
    assert isinstance(case["caseType"], str)
    assert isinstance(case["type"], str)


@pytest.mark.execution_scope("Alert")
@set_metadata(
    parameters={
        "Push to Simulated Cases": False,
        "Save JSON as Case Wall File": True,
        "Override Alert Name": "Exported_Alert.json",
        "Full path name": "",
    },
    input_context=copy.deepcopy(CONVERT_INTO_SIMULATED_CASE_CONTEXT),
)
def test_convert_into_simulated_case_save_to_casewall(
    tools: Tools,
    load_mock_data: SingleJson,
    action_output: MockActionOutput,
) -> None:
    """Test ConvertIntoSimulatedCase saves to Casewall with sanitized .case filename."""
    tools.set_alerts_full_details(load_mock_data[CONVERT_INTO_SIMULATED_CASE_ALERT_DETAILS_KEY])

    ConvertIntoSimulatedCase.main()

    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
    assert "Saved to Casewall" in action_output.results.output_message
    raw_output = json.loads(action_output.get_out_io().getvalue())
    result_object = json.loads(raw_output["ResultObjectJson"])
    assert "Exported_Alert.case" in result_object["<<file in here>>_None"]["Attachments"]


@pytest.mark.execution_scope("Alert")
@set_metadata(
    parameters={
        "Push to Simulated Cases": False,
        "Save JSON as Case Wall File": True,
        "Override Alert Name": "",
        "Full path name": "",
    },
    input_context=copy.deepcopy(CONVERT_INTO_SIMULATED_CASE_CONTEXT),
)
def test_convert_into_simulated_case_save_to_casewall_camelcase_name(
    tools: Tools,
    load_mock_data: SingleJson,
    action_output: MockActionOutput,
) -> None:
    """Test ConvertIntoSimulatedCase falls back to camelCase 'name' for attachment filename."""
    alert_details = copy.deepcopy(load_mock_data[CONVERT_INTO_SIMULATED_CASE_ALERT_DETAILS_KEY])
    alert_details[0]["domain_entities"][0]["additional_properties"]["SourceFileContent"] = json.dumps({
        "name": "CamelCaseAlert.json",
        "Events": [],
    })
    tools.set_alerts_full_details(alert_details)

    ConvertIntoSimulatedCase.main()

    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
    assert "Saved to Casewall" in action_output.results.output_message
    raw_output = json.loads(action_output.get_out_io().getvalue())
    result_object = json.loads(raw_output["ResultObjectJson"])
    assert "CamelCaseAlert.case" in result_object["<<file in here>>_None"]["Attachments"]


@pytest.mark.parametrize(
    ("input_case_type", "expected_type"),
    [
        (0, "SIMULATED"),
        (1, "EXTERNAL"),
        (2, "TEST"),
        (3, "REQUEST"),
        ("1", "EXTERNAL"),
        (" 1 ", "EXTERNAL"),
        ("external", "EXTERNAL"),
        (" external ", "EXTERNAL"),
    ],
)
def test_align_case_data_case_type_values(
    input_case_type: int | str,
    expected_type: str,
) -> None:
    """Test align_case_data correctly converts various CaseType values to string tokens."""
    raw_case: SingleJson = {
        "Name": "Test Case",
        "CaseType": input_case_type,
        "Events": [],
    }
    aligned = ConvertIntoSimulatedCase.align_case_data(raw_case)
    assert aligned["caseType"] == expected_type
    assert aligned["type"] == expected_type


@pytest.mark.parametrize(
    "invalid_val",
    [99, "99", "-1", "", "UNKNOWN", True, False, None],
)
def test_align_case_data_drops_invalid_values(
    invalid_val: int | str | bool | None,
) -> None:
    """Test align_case_data drops unmapped ints, strings, bools, and None to avoid backend enum errors."""
    raw_case: SingleJson = {
        "Name": "Test Case",
        "CaseType": invalid_val,
        "Events": [],
    }
    aligned = ConvertIntoSimulatedCase.align_case_data(raw_case)
    assert "caseType" not in aligned
    assert "type" not in aligned


def test_align_case_data_casetype_overrides_unmapped_type() -> None:
    """Test align_case_data synchronizes 'type' with 'caseType' even when an unmapped 'Type' is present."""
    raw_case: SingleJson = {
        "Name": "Test Case",
        "CaseType": 1,
        "Type": "Alert",
        "Events": [],
    }
    aligned = ConvertIntoSimulatedCase.align_case_data(raw_case)
    assert aligned["caseType"] == "EXTERNAL"
    assert aligned["type"] == "EXTERNAL"


def test_align_case_data_snake_case_fields() -> None:
    """Test align_case_data handles snake_case keys correctly."""
    raw_case: SingleJson = {
        "Name": "Test Case",
        "case_type": 1,
        "data_type": 1,
        "source_type": 1,
        "Events": [],
    }
    aligned = ConvertIntoSimulatedCase.align_case_data(raw_case)
    assert aligned["caseType"] == "EXTERNAL"
    assert aligned["type"] == "EXTERNAL"
    assert aligned["dataType"] == "1"
    assert aligned["sourceType"] == "CONNECTOR"


def test_align_case_data_compound_lowercase_fields() -> None:
    """Test align_case_data handles lowercase compound keys (casetype, datatype, sourcetype)."""
    raw_case: SingleJson = {
        "Name": "Test Case",
        "casetype": 1,
        "Datatype": 1,
        "sourcetype": 1,
        "Events": [],
    }
    aligned = ConvertIntoSimulatedCase.align_case_data(raw_case)
    assert aligned["caseType"] == "EXTERNAL"
    assert aligned["type"] == "EXTERNAL"
    assert aligned["dataType"] == "1"
    assert aligned["sourceType"] == "CONNECTOR"


@pytest.mark.parametrize(
    ("raw_key", "expected_camel"),
    [
        ("casetype", "caseType"),
        ("CaseType", "caseType"),
        ("Datatype", "dataType"),
        ("datatype", "dataType"),
        ("sourcetype", "sourceType"),
        ("case_type", "caseType"),
        ("case__type", "caseType"),
        ("", ""),
    ],
)
def test_to_camel_case_variants(raw_key: str, expected_camel: str) -> None:
    """Test to_camel_case normalizes compound lowercase and snake_case keys."""
    assert ConvertIntoSimulatedCase.to_camel_case(raw_key) == expected_camel


@pytest.mark.parametrize(
    ("raw_name", "expected_filename"),
    [
        ("NormalCase", "NormalCase.case"),
        ("Alert.json", "Alert.case"),
        ("Alert.txt", "Alert.case"),
        ("Alert.case", "Alert.case"),
        ("Alert.json.txt", "Alert.case"),
        ("Alert:Special/Chars*", "Alert_Special_Chars.case"),
        ("", "case.case"),
    ],
)
def test_sanitize_case_filename(raw_name: str, expected_filename: str) -> None:
    """Test sanitize_case_filename properly strips extensions and bad chars."""
    result = ConvertIntoSimulatedCase.sanitize_case_filename(raw_name)
    assert result == expected_filename


def test_enrich_case_metadata_events_and_names() -> None:
    """Test _enrich_case_metadata enriches event fields and resolves case names safely."""
    case_data: SingleJson = {
        "Name": "OrigAlert",
        "SourceSystemName": "ArcSight",
        "DeviceProduct": "ESM",
        "Events": [
            {"_fields": {"DeviceEventClassId": "class_1"}},
            {"_fields": {"deviceEventClassId": "class_2"}, "_rawDataFields": {}},
            {"_fields": {}},
            "invalid_event_entry",
        ],
    }
    ConvertIntoSimulatedCase._enrich_case_metadata(
        case_data,
        full_path_name="true",
        override_name="",
    )
    assert case_data["Name"] == "ArcSight_ESM_OrigAlert"
    assert case_data["Events"][0]["_rawDataFields"]["DeviceEventClassId"] == "class_1"
    assert case_data["Events"][0]["_rawDataFields"]["Name"] == "class_1"
    assert case_data["Events"][1]["_rawDataFields"]["DeviceEventClassId"] == "class_2"
    assert case_data["Events"][1]["_rawDataFields"]["Name"] == "class_2"

    # Test override name takes precedence
    ConvertIntoSimulatedCase._enrich_case_metadata(
        case_data,
        full_path_name="true",
        override_name="ExplicitOverride",
    )
    assert case_data["Name"] == "ExplicitOverride"
