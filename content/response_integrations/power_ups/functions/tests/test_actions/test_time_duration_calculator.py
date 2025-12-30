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

from ...actions import TimeDurationCalculator


@set_metadata(
    integration_config={},
    parameters={
        "Input DateTime 1": "2025-01-01T00:00:00Z",
        "Input DateTime 1 Format": "%Y-%m-%dT%H:%M:%S%z",
        "Input DateTime 2": "2025-02-01T00:00:00Z",
        "Input DateTime 2 Format": "%Y-%m-%dT%H:%M:%S%z",
    },
)
def test_time_duration_calculator_json_result(action_output: MockActionOutput) -> None:
    TimeDurationCalculator.main()

    assert action_output.report.json_output.json_result == {
        "years": 0,
        "days": 31,
        "hours": 744,
        "minutes": 44640,
        "seconds": 2678400,
        "duration": "Time between dates: 0 years, 31 days, 0 hours, 0 minutes and 0 seconds",
    }
    assert action_output.report.execution_state == ExecutionState.COMPLETED
