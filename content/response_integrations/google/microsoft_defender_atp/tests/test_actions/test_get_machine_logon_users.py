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

from microsoft_defender_atp.actions import GetMachineLogonUsers

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

MACHINE_ID: str = common.MOCK_DATA["machine_data"]["id"]
MACHINE_ID_IP: str = common.MOCK_DATA["machine_data_ip"]["id"]

SAMPLE_USER = {
    "id": "user1@test.com",
    "accountName": "user1",
    "accountDomain": "test.com",
    "lastSeen": "2024-01-01T10:00:00Z",
    "logonTypes": "Interactive",
}


@set_metadata(
    integration_config=common.CONFIG,
    parameters={},
    entities=[HOSTNAME_ENTITY, IP_ENTITY],
)
def test_get_machine_logon_users_success(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that logon users are returned for found machines."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))
    microsoft_defender_atp.add_machine(
        copy.deepcopy(common.MOCK_DATA["machine_data_ip"])
    )
    microsoft_defender_atp.add_logon_user(MACHINE_ID, copy.deepcopy(SAMPLE_USER))
    microsoft_defender_atp.add_logon_user(MACHINE_ID_IP, copy.deepcopy(SAMPLE_USER))

    GetMachineLogonUsers.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert "Action completed successfully" in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters={},
    entities=[HOSTNAME_ENTITY],
)
def test_get_machine_logon_users_no_users(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that action completes when a machine has no logon users."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))

    GetMachineLogonUsers.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert "0 users fetched" in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters={},
    entities=[NOT_FOUND_ENTITY],
)
def test_get_machine_logon_users_machine_not_found(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that action gracefully handles missing machines."""
    GetMachineLogonUsers.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert "not found in ATP" in action_output.results.output_message
