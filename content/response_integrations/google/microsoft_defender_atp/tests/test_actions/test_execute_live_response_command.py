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
import datetime

from TIPCommon.base.action import ExecutionState, EntityTypesEnum
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC

from microsoft_defender_atp.actions import ExecuteLiveResponseCommand
from microsoft_defender_atp.tests import common
from microsoft_defender_atp.tests.core.product import MicrosoftDefenderATP
from microsoft_defender_atp.tests.core.session import (
    MicrosoftDefenderATPSession,
)
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

SCRIPT_DEADLINE_TIME: datetime.datetime = datetime.datetime.now() + datetime.timedelta(
    minutes=10
)

HOSTNAME_ENTITY = create_entity(
    identifier=common.MOCK_DATA["machine_data"]["computerDnsName"],
    type_=EntityTypesEnum.HOST_NAME,
)
IP_ENTITY = create_entity(
    identifier=common.MOCK_DATA["machine_data_ip"]["lastIpAddress"],
    type_=EntityTypesEnum.ADDRESS,
)

DEFAULT_PARAMS = {
    "Command": """
    {
        "type": "GetFile",
        "params": [
            { "key": "Path", "value": "C:\\\\Users\\\\desktop.ini" }
        ]
    }
    """,
    "Comment": "Test command",
}

HOSTNAME = common.MOCK_DATA["machine_data"]["computerDnsName"]
IP_ADDRESS = common.MOCK_DATA["machine_data_ip"]["lastIpAddress"]

NOT_FOUND_ENTITY_IDENTIFIER = "not.found.com"
NOT_FOUND_ENTITY = create_entity(
    identifier=NOT_FOUND_ENTITY_IDENTIFIER, type_=EntityTypesEnum.HOST_NAME
)
NOT_FOUND_OUTPUT_MESSAGE = ("The following entities were not found in Microsoft "
                            "Defender for Endpoint: not.found.com.")


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[HOSTNAME_ENTITY, IP_ENTITY],
    input_context={
        "async_total_duration_deadline": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_execute_live_response_command_success(
    microsoft_defender_atp: MicrosoftDefenderATP,
    script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """
    Test for successful execution of the ExecuteLiveResponseCommand action (async).
    """
    machine_data = copy.deepcopy(common.MOCK_DATA["machine_data"])
    machine_data_ip = copy.deepcopy(common.MOCK_DATA["machine_data_ip"])
    microsoft_defender_atp.add_machine(machine_data)
    microsoft_defender_atp.add_machine(machine_data_ip)

    ExecuteLiveResponseCommand.main()

    assert len(script_session.request_history) == 9
    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[NOT_FOUND_ENTITY],
    input_context={
        "async_total_duration_deadline": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_execute_live_response_command_not_found(
    microsoft_defender_atp: MicrosoftDefenderATP,
    script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """
    Test for ExecuteLiveResponseCommand action when an endpoint is not found.
    """
    microsoft_defender_atp.cleanup_machines()
    ExecuteLiveResponseCommand.main()

    assert len(script_session.request_history) == 2
    assert NOT_FOUND_OUTPUT_MESSAGE in action_output.results.output_message
    assert action_output.results.result_value in (False, "false")
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[HOSTNAME_ENTITY],
    input_context={
        "async_total_duration_deadline": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_execute_live_response_command_waiting(
    microsoft_defender_atp: MicrosoftDefenderATP,
    script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """
    Test for ExecuteLiveResponseCommand action when a conflicting action is already running.
    """
    machine_data = copy.deepcopy(common.MOCK_DATA["machine_data"])
    microsoft_defender_atp.add_machine(machine_data)
    conflicting_task = {
        "id": "conflicting-action-id",
        "type": "RunLiveResponse",
        "requestor": "test@contoso.com",
        "status": "InProgress",
        "machineId": machine_data["id"],
        "commands": [{"index": 0, "command": "{\"type\": \"PutFile\", \"params\": []}"}],
    }
    microsoft_defender_atp.add_task(conflicting_task)

    ExecuteLiveResponseCommand.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    assert "Waiting for command to finish" in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[HOSTNAME_ENTITY],
    input_context={
        "async_total_duration_deadline": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_execute_live_response_command_adopt_existing(
    microsoft_defender_atp: MicrosoftDefenderATP,
    script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """
    Test for ExecuteLiveResponseCommand action when an identical action is already running.
    """
    machine_data = copy.deepcopy(common.MOCK_DATA["machine_data"])
    microsoft_defender_atp.add_machine(machine_data)
    matching_task = {
        "id": "matching-action-id",
        "type": "RunLiveResponse",
        "requestor": "test@contoso.com",
        "status": "InProgress",
        "machineId": machine_data["id"],
        "commands": [{"index": 0, "command": DEFAULT_PARAMS["Command"].strip()}],
    }
    microsoft_defender_atp.add_task(matching_task)

    ExecuteLiveResponseCommand.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS

