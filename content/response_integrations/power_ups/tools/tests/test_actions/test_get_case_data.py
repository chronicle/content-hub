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

from typing import TYPE_CHECKING
from unittest.mock import ANY, MagicMock, patch

from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import GetCaseData

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput


@set_metadata(
    integration_config={},
    parameters={
        "Case Id": "123",
        "Fields to Return": "case_name, status, tags",
        "Nested Keys Delimiter": ".",
    },
)
@patch.object(GetCaseData, "get_insight_content")
@patch.object(GetCaseData, "get_all_case_overview_details")
@patch.object(GetCaseData, "get_case_insights")
def test_get_case_data_success(
    mock_get_case_insights: MagicMock,
    mock_get_case_details: MagicMock,
    mock_get_insight_content: MagicMock,
    action_output: MockActionOutput,
) -> None:
    mock_case_data = MagicMock()
    mock_case_data.to_json.return_value = {
        "case_name": "Test Case",
        "status": "Open",
        "priority": "High",
        "tags": [{"displayName": "Simulated Case", "priority": 0}],
    }
    mock_get_case_details.return_value = mock_case_data

    mock_get_case_insights.return_value = [{"title": "Test Insight", "content": "<% insight_url %>"}]

    mock_get_insight_content.return_value = {"key": "value"}

    GetCaseData.main()

    mock_get_case_details.assert_called_once_with(ANY, "123", case_expand=["tags"])

    assert action_output.results.json_output is not None
    result_args = action_output.results.json_output.json_result

    assert "case_name" in result_args
    assert result_args["case_name"] == "Test Case"
    assert "status" in result_args
    assert "insights" in result_args
    assert "priority" not in result_args

    assert "tags" in result_args
    assert result_args["tags"][0]["displayName"] == "Simulated Case"

    assert result_args["insights"][0]["key"] == "value"

    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
