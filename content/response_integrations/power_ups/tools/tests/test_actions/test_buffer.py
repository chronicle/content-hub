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

import pytest
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ...actions import Buffer

DEFAULT_OUTPUT_MESSAGE: str = "Input values 'transferred' to the output."


@pytest.mark.execution_scope("Case")
@set_metadata(
    parameters={
        "JSON": '{"key": "value"}',
        "ResultValue": "custom_success_value",
    },
    input_context={"case_id": "123", "alert_id": "alert_1"},
)
def test_buffer_success(
    action_output: MockActionOutput,
) -> None:
    """Test Buffer action when provided with valid JSON input."""
    Buffer.main()

    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
    assert action_output.results.result_value == "custom_success_value"
    assert action_output.results.output_message == DEFAULT_OUTPUT_MESSAGE
    assert action_output.results.json_output.json_result == {"key": "value"}


@pytest.mark.execution_scope("Case")
@set_metadata(
    parameters={
        "JSON": "invalid_json",
        "ResultValue": "custom_value",
    },
    input_context={"case_id": "123", "alert_id": "alert_1"},
)
def test_buffer_invalid_json(
    action_output: MockActionOutput,
) -> None:
    """Test Buffer action when provided with invalid JSON input."""
    Buffer.main()

    assert action_output.results.execution_state.value == EXECUTION_STATE_FAILED
    assert action_output.results.result_value == "failed"
    assert "Failed to load JSON with error:" in action_output.results.output_message


@pytest.mark.execution_scope("Case")
@set_metadata(
    parameters={
        "JSON": "",
        "ResultValue": "some_value",
    },
    input_context={"case_id": "123", "alert_id": "alert_1"},
)
def test_buffer_no_json(
    action_output: MockActionOutput,
) -> None:
    """Test Buffer action when no JSON is provided."""
    Buffer.main()

    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
    assert action_output.results.result_value == "some_value"
    assert action_output.results.output_message == DEFAULT_OUTPUT_MESSAGE
