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
from typing import TYPE_CHECKING

import pytest
import requests
from integration_testing.common import create_entity
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import EntityTypesEnum, ExecutionState

from microsoft_defender_atp.actions import CreateUnisolateMachineTask

# The action scripts import the manager from the core package; patch that module.
from microsoft_defender_atp.core import MicrosoftDefenderATPManager as manager_module
from microsoft_defender_atp.tests import common

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput
    from TIPCommon.types import SingleJson

    from microsoft_defender_atp.tests.core.product import MicrosoftDefenderATP
    from microsoft_defender_atp.tests.core.session import MicrosoftDefenderATPSession

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
    "Comment": "Unisolating after investigation",
}
MACHINE_ID: str = common.MOCK_DATA["machine_data"]["id"]
MACHINE_IP_ID: str = common.MOCK_DATA["machine_data_ip"]["id"]
UNKNOWN_MACHINE_ID: str = "0" * 40


def _unisolate_tasks(product: MicrosoftDefenderATP) -> list[SingleJson]:
    """Return the Unisolate tasks stored in the mock product."""
    return [task for task in product.get_all_tasks() if task["type"] == "Unisolate"]


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[HOSTNAME_ENTITY, IP_ENTITY],
)
def test_create_unisolate_machine_task_success(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that unisolate tasks are created for found machines."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))
    microsoft_defender_atp.add_machine(
        copy.deepcopy(common.MOCK_DATA["machine_data_ip"])
    )

    CreateUnisolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert "Action completed successfully" in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[NOT_FOUND_ENTITY],
)
def test_create_unisolate_machine_task_machine_not_found(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that only not-found machines complete with a False result (fail-closed)."""
    CreateUnisolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (False, "false")
    assert "not found in ATP" in action_output.results.output_message


@set_metadata(integration_config=common.CONFIG, parameters={**DEFAULT_PARAMS, "Machine ID": MACHINE_ID}, entities=[])
def test_create_unisolate_machine_task_machine_id_success(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that a Machine ID alone creates one unisolate task for that machine."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))

    CreateUnisolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    json_result = action_output.results.json_output.json_result
    assert [task["machine_id"] for task in json_result] == [MACHINE_ID]
    assert [task["machineId"] for task in _unisolate_tasks(microsoft_defender_atp)] == [MACHINE_ID]
    task_id = json_result[0]["id"]
    message = f"Unisolate machine task {task_id} was created successfully on Defender ATP Server for {MACHINE_ID}"
    assert action_output.results.output_message == message
    assert common.logged_levels(caplog, message) == ["INFO"]
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("SUCCESS", "NONE", "COMPLETED", targets=1, failed=0),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={**DEFAULT_PARAMS, "Machine ID": UNKNOWN_MACHINE_ID},
    entities=[],
)
def test_create_unisolate_machine_task_machine_id_not_found(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that a Machine ID that returns 404 completes with a False result."""
    CreateUnisolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (False, "false")
    assert "not found in ATP" in action_output.results.output_message
    assert not _unisolate_tasks(microsoft_defender_atp)
    message = f"Failed to find machine ATP by Machine ID: {UNKNOWN_MACHINE_ID}"
    assert action_output.results.output_message == f"{message}\n1 entities were not found in ATP"
    assert common.logged_levels(caplog, message) == ["WARNING"]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={**DEFAULT_PARAMS, "Machine ID": common.MOCK_DATA["machine_data"]["computerDnsName"]},
    entities=[],
)
def test_create_unisolate_machine_task_hostname_as_machine_id_rejected(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that a hostname typed into Machine ID is not resolved and unisolates nothing."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))

    CreateUnisolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (False, "false")
    assert "not found in ATP" in action_output.results.output_message
    assert not _unisolate_tasks(microsoft_defender_atp)


@set_metadata(
    integration_config=common.CONFIG,
    parameters={**DEFAULT_PARAMS, "Machine ID": MACHINE_ID},
    entities=[IP_ENTITY],
)
def test_create_unisolate_machine_task_machine_id_overrides_entities(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that entities are ignored when Machine ID is set."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data_ip"]))

    CreateUnisolateMachineTask.main()

    assert action_output.results.result_value in (True, "true")
    unisolated = [task["machineId"] for task in _unisolate_tasks(microsoft_defender_atp)]
    assert unisolated == [MACHINE_ID]
    assert MACHINE_IP_ID not in unisolated


@set_metadata(integration_config=common.CONFIG, parameters={**DEFAULT_PARAMS, "Machine ID": MACHINE_ID}, entities=[])
def test_create_unisolate_machine_task_active_request_exists(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that a pending unisolate task as the newest request is reused as success."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))
    microsoft_defender_atp.create_task("Isolate", MACHINE_ID, "Succeeded", creation_time="2024-01-01T12:00:00.000Z")
    active_task = microsoft_defender_atp.create_task(
        "Unisolate",
        MACHINE_ID,
        "InProgress",
        creation_time="2024-02-01T12:00:00.000Z",
    )
    microsoft_defender_atp.set_active_request_exists(MACHINE_ID, "Unisolate")

    CreateUnisolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    json_result = action_output.results.json_output.json_result
    assert [task["id"] for task in json_result] == [active_task["id"]]
    assert len(_unisolate_tasks(microsoft_defender_atp)) == 1
    assert "already exists" in action_output.results.output_message
    assert "created successfully" not in action_output.results.output_message
    message = f"Unisolate machine task {active_task['id']} already exists on Defender ATP Server for {MACHINE_ID}"
    assert action_output.results.output_message == message
    assert common.logged_levels(caplog, message) == ["INFO"]
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("SUCCESS", "NONE", "COMPLETED", targets=1, failed=0),
    ]


@set_metadata(integration_config=common.CONFIG, parameters={**DEFAULT_PARAMS, "Machine ID": MACHINE_ID}, entities=[])
def test_create_unisolate_machine_task_opposite_request_pending(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that an old unisolate task isn't reused while an isolate is pending."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))
    microsoft_defender_atp.create_task("Unisolate", MACHINE_ID, "Succeeded", creation_time="2024-01-01T12:00:00.000Z")
    pending_task = microsoft_defender_atp.create_task(
        "Isolate",
        MACHINE_ID,
        "Pending",
        creation_time="2024-02-01T12:00:00.000Z",
    )
    microsoft_defender_atp.set_active_request_exists(MACHINE_ID, "Unisolate")

    CreateUnisolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (False, "false")
    assert f"Isolate (task {pending_task['id']}, Pending)" in action_output.results.output_message
    error = (
        f"Machine {MACHINE_ID} already has an active request that isn't a pending unisolate task. "
        f"Newest containment task: Isolate (task {pending_task['id']}, Pending)."
    )
    assert action_output.results.output_message == f"Failed to process Machine ID {MACHINE_ID}. {error}"
    assert common.logged_levels(caplog, f"Failed to process Machine ID {MACHINE_ID}: {error}") == ["ERROR"]
    assert action_output.results.json_output is None


@set_metadata(
    integration_config={**common.CONFIG, "Graph API Root": "https://graph.microsoft.com"},
    parameters={**DEFAULT_PARAMS, "Machine ID": MACHINE_ID},
    entities=[],
)
def test_create_unisolate_machine_task_uses_v1_manager_with_graph_api_root(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that the Defender (V1) manager is used even if Graph API Root is set."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))

    CreateUnisolateMachineTask.main()

    assert action_output.results.result_value in (True, "true")


@set_metadata(integration_config=common.CONFIG, parameters={**DEFAULT_PARAMS, "Machine ID": MACHINE_ID}, entities=[])
def test_create_unisolate_machine_task_machine_id_lookup_error_is_failure(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that an API error while looking up the Machine ID fails instead of not-found."""
    monkeypatch.setattr(
        manager_module.MicrosoftDefenderATPManager,
        "get_machine_by_id",
        common.raise_error(manager_module.MicrosoftDefenderATPError("Internal server error")),
    )

    CreateUnisolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (False, "false")
    assert f"Failed to process Machine ID {MACHINE_ID}" in action_output.results.output_message
    assert "not found in ATP" not in action_output.results.output_message
    assert action_output.results.output_message == f"Failed to process Machine ID {MACHINE_ID}. Internal server error"
    assert common.logged_levels(caplog, f"Failed to process Machine ID {MACHINE_ID}: Internal server error") == [
        "ERROR"
    ]
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("FAILURE", "VENDOR_ERROR", "COMPLETED", targets=1, failed=1),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={**DEFAULT_PARAMS, "Machine ID": f"DeviceId: {MACHINE_ID}"},
    entities=[],
)
def test_create_unisolate_machine_task_prefixed_machine_id(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that a Machine ID with a "DeviceId:" prefix starts the task on the bare machine ID."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))

    CreateUnisolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert [task["machineId"] for task in _unisolate_tasks(microsoft_defender_atp)] == [MACHINE_ID]


@set_metadata(integration_config=common.CONFIG, parameters=DEFAULT_PARAMS, entities=[HOSTNAME_ENTITY])
def test_create_unisolate_machine_task_unexpected_error_summary(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that a non-Defender error still propagates and logs one FAILED summary line first."""
    monkeypatch.setattr(
        manager_module.MicrosoftDefenderATPManager,
        "__init__",
        common.raise_error(requests.ConnectionError("Connection refused")),
    )

    with pytest.raises(requests.ConnectionError):
        CreateUnisolateMachineTask.main()

    assert common.get_summary_lines(caplog) == [
        common.expected_summary(
            "FAILURE",
            "CONNECTION_ERROR",
            "FAILED",
            targets=1,
            failed=1,
            exc_type="ConnectionError",
        ),
    ]
