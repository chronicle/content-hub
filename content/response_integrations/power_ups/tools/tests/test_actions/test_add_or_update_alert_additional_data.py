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
from typing import TYPE_CHECKING

import pytest
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import AddOrUpdateAlertAdditionalData
from ..common import (
    ADD_ALERT_SCOPE_CONTEXT,
    ADD_ALERT_SCOPE_PARAMS,
    ADD_CASE_SCOPE_CONTEXT,
    ADD_CASE_SCOPE_PARAMS,
    ALERTS_ALERT_SCOPE_KEY,
    ALERTS_CASE_SCOPE_KEY,
    CASE_METADATA_KEY,
)
from ..core.product import Tools
from ..core.session import ToolsSession

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


@pytest.mark.execution_scope("Alert")
@set_metadata(
    parameters=ADD_ALERT_SCOPE_PARAMS,
    input_context=ADD_ALERT_SCOPE_CONTEXT,
)
def test_add_or_update_alert_additional_data_alert_scope(
    tools: Tools,
    script_session: ToolsSession,
    load_mock_data: SingleJson,
    action_output: MockActionOutput,
) -> None:
    """Test AddOrUpdateAlertAdditionalData action under Alert scope."""
    tools.set_case_metadata(load_mock_data[CASE_METADATA_KEY])
    tools.set_alerts_full_details(load_mock_data[ALERTS_ALERT_SCOPE_KEY])

    AddOrUpdateAlertAdditionalData.main()

    assert action_output.results.execution_state.value == ExecutionState.COMPLETED.value
    assert action_output.results.json_output is not None
    assert action_output.results.result_value == 1

    result_json = action_output.results.json_output.json_result
    assert "dict" in result_json
    assert result_json["dict"]["dict_key"] == "dict_val"

    assert len(script_session.request_history) == 2

    payload = script_session.request_history[-1].request.kwargs.get("json") or {}
    alert_1_data = json.loads(
        payload.get("alerts_additional_data", {}).get("alert_1", "{}")
    )
    assert alert_1_data.get("dict", {}).get("dict_key") == "dict_val"


@pytest.mark.execution_scope("Case")
@set_metadata(
    parameters=ADD_CASE_SCOPE_PARAMS,
    input_context=ADD_CASE_SCOPE_CONTEXT,
)
def test_add_or_update_alert_additional_data_case_scope(
    tools: Tools,
    script_session: ToolsSession,
    load_mock_data: SingleJson,
    action_output: MockActionOutput,
) -> None:
    """Test AddOrUpdateAlertAdditionalData action under Case scope."""
    tools.set_case_metadata(load_mock_data[CASE_METADATA_KEY])
    tools.set_alerts_full_details(load_mock_data[ALERTS_CASE_SCOPE_KEY])

    AddOrUpdateAlertAdditionalData.main()

    assert action_output.results.execution_state.value == ExecutionState.COMPLETED.value
    assert action_output.results.json_output is not None
    assert action_output.results.result_value == 2

    result_json = action_output.results.json_output.json_result
    assert "list" in result_json
    assert "list_item" in result_json["list"]

    assert len(script_session.request_history) == 3

    payload = script_session.request_history[-1].request.kwargs.get("json") or {}
    alert_1_data = json.loads(
        payload.get("alerts_additional_data", {}).get("alert_1", "{}")
    )
    alert_2_data = json.loads(
        payload.get("alerts_additional_data", {}).get("alert_2", "{}")
    )
    assert "list_item" in alert_1_data.get("list", [])
    assert "list_item" in alert_2_data.get("list", [])
