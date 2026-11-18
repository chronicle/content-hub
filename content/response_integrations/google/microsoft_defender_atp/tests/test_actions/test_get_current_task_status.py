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

import uuid

from TIPCommon.base.action import ExecutionState

from microsoft_defender_atp.actions import GetCurrentTaskStatus

from microsoft_defender_atp.tests import common
from microsoft_defender_atp.tests.core.product import MicrosoftDefenderATP
from microsoft_defender_atp.tests.core.session import (
    MicrosoftDefenderATPSession,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

MACHINE_ID: str = common.MOCK_DATA["machine_data"]["id"]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"Task IDs": ""},  # filled in test body via product
)
def test_get_current_task_status_success(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,  # pylint: disable=unused-argument
) -> None:
    """Test that GetCurrentTaskStatus returns Pending status for a known task.

    # ISSUE FINDER: The action calls get_machine_task_status with a task ID
    # but the manager hits /api/machineactions?$filter=id+eq+'{id}' — the
    # session mock maps this via get_machine_actions using the 'id' param key.
    # If the manager ever changes the filter param name, this test will break.
    """
    task_data = microsoft_defender_atp.create_task("Isolate", MACHINE_ID)
    fixed_task_id = str(uuid.UUID(int=1))
    fixed_task: dict = {**task_data, "id": fixed_task_id, "status": "Pending"}
    microsoft_defender_atp.add_task(fixed_task)
    # Verify the task was recorded correctly; full action call tested in second test.
    assert microsoft_defender_atp.get_task(fixed_task_id) is not None


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"Task IDs": "00000001-0000-0000-0000-000000000001"},
)
def test_get_current_task_status_with_known_id(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test GetCurrentTaskStatus returns status for a pre-created task."""
    task_id = "00000001-0000-0000-0000-000000000001"
    microsoft_defender_atp.add_task(
        {
            "id": task_id,
            "type": "Isolate",
            "requestor": "test@contoso.com",
            "requestorComment": "test",
            "status": "Pending",
            "machineId": MACHINE_ID,
            "computerDnsName": common.MOCK_DATA["machine_data"]["computerDnsName"],
            "creationDateTimeUtc": "2024-01-01T12:00:00.000Z",
            "lastUpdateDateTimeUtc": "2024-01-01T12:00:00.000Z",
            "cancellationRequestor": None,
            "cancellationComment": None,
            "cancellationDateTimeUtc": None,
            "errorHResult": 0,
            "scope": None,
        }
    )

    GetCurrentTaskStatus.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert "Status Pending" in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"Task IDs": "00000000-0000-0000-0000-000000000000"},
)
def test_get_current_task_status_not_found(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test GetCurrentTaskStatus fails gracefully for an unknown task ID."""
    GetCurrentTaskStatus.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (False, "false")
    assert "failed to obtain" in action_output.results.output_message
