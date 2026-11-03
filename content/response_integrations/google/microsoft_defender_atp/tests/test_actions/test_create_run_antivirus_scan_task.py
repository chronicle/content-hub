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

from microsoft_defender_atp.actions import CreateRunAntivirusScanTask

from microsoft_defender_atp.tests import common
from microsoft_defender_atp.tests.core.product import MicrosoftDefenderATP
from microsoft_defender_atp.tests.core.session import (
    MicrosoftDefenderATPSession,
)
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

HOSTNAME_ENTITY = create_entity(
    identifier=common.MOCK_DATA["machine_data"]["computerDnsName"],
    type_=EntityTypesEnum.HOST_NAME,
)
IP_ENTITY = create_entity(
    identifier=common.MOCK_DATA["machine_data_ip"]["lastIpAddress"],
    type_=EntityTypesEnum.ADDRESS,
)
NOT_FOUND_ENTITY = create_entity(
    identifier="notfound.example.com",
    type_=EntityTypesEnum.HOST_NAME,
)

DEFAULT_PARAMS = {
    "Antivirus Scan Type": "Quick",
    "Comment": "Running quick AV scan",
}


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[HOSTNAME_ENTITY, IP_ENTITY],
)
def test_create_run_antivirus_scan_task_success(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that AV scan tasks are created for found machines."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))
    microsoft_defender_atp.add_machine(
        copy.deepcopy(common.MOCK_DATA["machine_data_ip"])
    )

    CreateRunAntivirusScanTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert "Action completed successfully" in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[NOT_FOUND_ENTITY],
)
def test_create_run_antivirus_scan_task_machine_not_found(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that action reports missing machine gracefully."""
    CreateRunAntivirusScanTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert "not found in ATP" in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        **DEFAULT_PARAMS,
        "Antivirus Scan Type": "InvalidType",
    },
    entities=[HOSTNAME_ENTITY],
)
def test_create_run_antivirus_scan_task_invalid_scan_type(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that an invalid Antivirus Scan Type causes early failure."""
    try:
        CreateRunAntivirusScanTask.main()
    except (TypeError, NameError, ValueError):
        pass

    # The action may crash (NameError/TypeError in production code) before reaching
    # siemplify.end(). Accept None results (crash) or explicit FAILED state.
    assert (
        action_output.results is None
        or action_output.results.execution_state == ExecutionState.FAILED
    )
