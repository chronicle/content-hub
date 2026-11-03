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

from TIPCommon.base.action import ExecutionState

from microsoft_defender_atp.actions import RunAdvancedHuntingQuery

from microsoft_defender_atp.tests import common
from microsoft_defender_atp.tests.core.product import MicrosoftDefenderATP
from microsoft_defender_atp.tests.core.session import (
    MicrosoftDefenderATPSession,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

DEFAULT_PARAMS = {
    "Query": "DeviceInfo | take 10",
}


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
)
def test_run_advanced_hunting_query_with_results(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that query results are returned and added to JSON output."""
    microsoft_defender_atp.set_hunting_query_result(
        {
            "Results": [
                {"DeviceName": "test-vm", "OSPlatform": "Windows10"},
                {"DeviceName": "another-vm", "OSPlatform": "WindowsServer2019"},
            ]
        }
    )

    RunAdvancedHuntingQuery.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert "Query executed successfully" in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
)
def test_run_advanced_hunting_query_no_results(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that empty query results are handled gracefully."""
    microsoft_defender_atp.set_hunting_query_result({"Results": []})

    RunAdvancedHuntingQuery.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert "did not return any results" in action_output.results.output_message
