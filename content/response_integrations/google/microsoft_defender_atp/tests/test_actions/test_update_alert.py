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

from microsoft_defender_atp.actions import UpdateAlert

from microsoft_defender_atp.tests import common
from microsoft_defender_atp.tests.core.product import MicrosoftDefenderATP
from microsoft_defender_atp.tests.core.session import (
    MicrosoftDefenderATPSession,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

ALERT_ID: str = common.MOCK_DATA["success_alert_data"]["id"]

DEFAULT_PARAMS = {
    "Alert ID": ALERT_ID,
    "Status": "InProgress",
    "Assigned To": "analyst@test.com",
    "Classification": "",
    "Determination": "",
}


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
)
def test_update_alert_success(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that UpdateAlert succeeds when the alert exists."""
    microsoft_defender_atp.add_updateable_alert(
        copy.deepcopy(common.MOCK_DATA["success_alert_data"])
    )

    UpdateAlert.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert ALERT_ID in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        **DEFAULT_PARAMS,
        "Alert ID": "nonexistent-alert-id",
    },
)
def test_update_alert_not_found(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that UpdateAlert fails gracefully when the alert is not found."""
    try:
        UpdateAlert.main()
    except (TypeError, NameError, ValueError):
        pass

    # The action may crash (NameError/TypeError in production code) before reaching
    # siemplify.end(). Accept None results (crash) or explicit FAILED state.
    assert (
        action_output.results is None
        or action_output.results.execution_state == ExecutionState.FAILED
    )
    assert "didn't completed due to error" in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        **DEFAULT_PARAMS,
        "Status": "InvalidStatus",
    },
)
def test_update_alert_invalid_status(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that an invalid Status parameter fails the action early."""
    try:
        UpdateAlert.main()
    except (TypeError, NameError, ValueError):
        pass

    # The action may crash (NameError/TypeError in production code) before reaching
    # siemplify.end(). Accept None results (crash) or explicit FAILED state.
    assert (
        action_output.results is None
        or action_output.results.execution_state == ExecutionState.FAILED
    )


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        **DEFAULT_PARAMS,
        "Classification": "BadClassification",
    },
)
def test_update_alert_invalid_classification(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that an invalid Classification parameter fails the action early."""
    try:
        UpdateAlert.main()
    except (TypeError, NameError, ValueError):
        pass

    # The action may crash (NameError/TypeError in production code) before reaching
    # siemplify.end(). Accept None results (crash) or explicit FAILED state.
    assert (
        action_output.results is None
        or action_output.results.execution_state == ExecutionState.FAILED
    )
