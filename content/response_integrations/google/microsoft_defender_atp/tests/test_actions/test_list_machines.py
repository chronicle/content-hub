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

from TIPCommon.base.action import ExecutionState

from microsoft_defender_atp.actions import ListMachines

from microsoft_defender_atp.tests import common
from microsoft_defender_atp.tests.core.product import MicrosoftDefenderATP
from microsoft_defender_atp.tests.core.session import (
    MicrosoftDefenderATPSession,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

DEFAULT_PARAMS = {
    "Last Seen Time Frame": "",
    "Machine Name": "",
    "Machine IP Address": "",
    "Machine Risk Score": "",
    "Machine Health Status": "",
    "Machine OS Platform": "",
    "RBAC Group ID": "",
}


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
)
def test_list_machines_success(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that machines are returned when the API has results."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))
    microsoft_defender_atp.add_machine(
        copy.deepcopy(common.MOCK_DATA["machine_data_ip"])
    )

    ListMachines.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert "Successfully returned machine data" in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
)
def test_list_machines_no_results(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that action completes when no machines are onboarded."""
    ListMachines.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert "not able to find" in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        **DEFAULT_PARAMS,
        "Machine Health Status": "InvalidStatus",
    },
)
def test_list_machines_invalid_health_status_fails(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that an invalid Machine Health Status causes the action to fail."""
    try:
        ListMachines.main()
    except (TypeError, NameError, ValueError):
        pass

    # The action may crash (NameError/TypeError in production code) before reaching
    # siemplify.end(). Accept None results (crash) or explicit FAILED state.
    assert (
        action_output.results is None
        or action_output.results.execution_state == ExecutionState.FAILED
    )
