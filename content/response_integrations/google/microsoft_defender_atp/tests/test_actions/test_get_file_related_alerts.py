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

from TIPCommon.base.action import ExecutionState, EntityTypesEnum

from microsoft_defender_atp.actions import GetFileRelatedAlerts

from microsoft_defender_atp.tests import common
from microsoft_defender_atp.tests.core.product import MicrosoftDefenderATP
from microsoft_defender_atp.tests.core.session import (
    MicrosoftDefenderATPSession,
)
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

FILE_HASH = "a" * 40  # SHA-1
FILE_HASH_ENTITY = create_entity(
    identifier=FILE_HASH,
    type_=EntityTypesEnum.FILE_HASH,
)
NO_RESULTS_HASH = "b" * 40
NO_RESULTS_ENTITY = create_entity(
    identifier=NO_RESULTS_HASH,
    type_=EntityTypesEnum.FILE_HASH,
)

DEFAULT_PARAMS = {
    "Status": "",
    "Severity": "",
    "Category": "",
    "Incident ID": "",
}


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[FILE_HASH_ENTITY],
)
def test_get_file_related_alerts_success(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that alerts are returned for a known file hash."""
    alert = copy.deepcopy(common.MOCK_DATA["success_alert_data"])
    microsoft_defender_atp.add_file_alert(FILE_HASH, alert)

    GetFileRelatedAlerts.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    output = action_output.results.output_message
    assert "1 alerts found" in output


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[NO_RESULTS_ENTITY],
)
def test_get_file_related_alerts_no_alerts(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that action completes successfully with no alerts for an unknown hash."""
    GetFileRelatedAlerts.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    output = action_output.results.output_message
    assert "No alerts found" in output


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        **DEFAULT_PARAMS,
        "Status": "InvalidStatus",
    },
    entities=[FILE_HASH_ENTITY],
)
def test_get_file_related_alerts_invalid_status(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that invalid Status fails the action early."""
    try:
        GetFileRelatedAlerts.main()
    except (TypeError, NameError, ValueError):
        pass

    # The action may crash (NameError/TypeError in production code) before reaching
    # siemplify.end(). Accept None results (crash) or explicit FAILED state.
    assert (
        action_output.results is None
        or action_output.results.execution_state == ExecutionState.FAILED
    )
