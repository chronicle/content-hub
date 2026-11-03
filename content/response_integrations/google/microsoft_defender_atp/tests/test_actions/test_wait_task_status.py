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

import json as _json

from TIPCommon.base.action import ExecutionState

from microsoft_defender_atp.actions import WaitTaskStatus

from microsoft_defender_atp.tests import common
from microsoft_defender_atp.tests.core.product import MicrosoftDefenderATP
from microsoft_defender_atp.tests.core.session import (
    MicrosoftDefenderATPSession,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

MACHINE_ID: str = common.MOCK_DATA["machine_data"]["id"]
SUCCEEDED_TASK_ID: str = "00000001-0000-0000-0000-000000000001"
PENDING_TASK_ID: str = "00000002-0000-0000-0000-000000000002"
FAILED_TASK_ID: str = "00000003-0000-0000-0000-000000000003"


def _make_task(task_id: str, status: str) -> dict:
    return {
        "id": task_id,
        "type": "Isolate",
        "requestor": "test@contoso.com",
        "requestorComment": "test",
        "status": status,
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


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"Task IDs": SUCCEEDED_TASK_ID},
)
def test_wait_task_status_succeeded(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test WaitTaskStatus returns COMPLETED when task has Succeeded."""
    microsoft_defender_atp.add_task(_make_task(SUCCEEDED_TASK_ID, "Succeeded"))

    WaitTaskStatus.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert "Tasks were awaited" in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"Task IDs": PENDING_TASK_ID},
)
def test_wait_task_status_pending(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test WaitTaskStatus returns IN_PROGRESS when task is still Pending."""
    microsoft_defender_atp.add_task(_make_task(PENDING_TASK_ID, "Pending"))

    WaitTaskStatus.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"Task IDs": FAILED_TASK_ID},
)
def test_wait_task_status_failed_task(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test WaitTaskStatus returns COMPLETED with result_value False when task failed.

    Note: The production WaitTaskStatus code calls siemplify.end() inside the
    loop for failed tasks (setting result_value=false), then continues and
    calls end() again. The mock sys.exit is a no-op so both writes happen.
    We parse the first JSON object to verify the task-failed path.
    """
    microsoft_defender_atp.add_task(_make_task(FAILED_TASK_ID, "Failed"))

    WaitTaskStatus.main()

    # Two JSON objects are written; decode only the first one.
    raw = action_output.get_out_io().getvalue()
    first_obj, _ = _json.JSONDecoder().raw_decode(raw)
    # The first end() call reports failed task with result_value=false and status=COMPLETED.
    assert first_obj.get("ResultValue") in ("false",)
    assert first_obj.get("ExecutionState") == 0  # EXECUTION_STATE_COMPLETED
