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

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import CalculateTimestamp

Failed_message = ('Error executing action "Calculate Timestamp"\n'
                  'Reason: input provided in “Custom Timestamp” and '
                  '“Custom Timestamp Format” is not aligned. Please check '
                  'the spelling.')


@set_metadata(
    integration_config={},
    parameters={
        "Input Type": "Current Time",
        "Timestamp Delta": "+1d,-1H",
        "Output Timestamp Format": "%Y-%m-%d %H:%M:%S",
    },
)
def test_calculate_timestamp_current_time_with_deltas(
    action_output: MockActionOutput,
) -> None:
    """Test calculating timestamp from current time with deltas and epoch output."""
    CalculateTimestamp.main()

    assert action_output.results.output_message
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config={},
    parameters={
        "Input Type": "Custom Timestamp",
        "Custom Timestamp": "2024-01-15 12:00:00",
        "Custom Timestamp Format": "%Y-%m-%d %H:%M:%S",
        "Timestamp Delta": "+1m",  # 1 month
        "Output Timestamp Format": "%Y-%m-%d",
    },
)
def test_calculate_timestamp_custom_with_format(
    action_output: MockActionOutput,
) -> None:
    """Test using a custom timestamp with a specific format and string output."""
    CalculateTimestamp.main()

    assert action_output.results.output_message
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    
    integration_config={},
    parameters={
        "Input Type": "Custom Timestamp",
        "Custom Timestamp": "2024/01/15",
        "Custom Timestamp Format": "%Y-%m-%d",
    },
)
def test_calculate_timestamp_misaligned_format_fails(
    action_output: MockActionOutput,
) -> None:
    """Test that validation fails for misaligned custom timestamp and format."""
    CalculateTimestamp.main()
    assert action_output.results.output_message == Failed_message
    assert action_output.results.execution_state == ExecutionState.FAILED
