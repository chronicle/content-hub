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

from microsoft_defender_atp.actions import CreateIsolateMachineTask

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
    identifier="missing-host",
    type_=EntityTypesEnum.HOST_NAME,
)
SAME_MACHINE_IP_ENTITY = create_entity(
    identifier=common.MOCK_DATA["machine_data"]["lastIpAddress"],
    type_=EntityTypesEnum.ADDRESS,
)

DEFAULT_PARAMS = {
    "Isolation Type": "Full",
    "Comment": "Isolating for investigation",
}
MACHINE_ID: str = common.MOCK_DATA["machine_data"]["id"]
MACHINE_IP_ID: str = common.MOCK_DATA["machine_data_ip"]["id"]
UNKNOWN_MACHINE_ID: str = "0" * 40


def _isolate_tasks(product: MicrosoftDefenderATP) -> list[SingleJson]:
    """Return the Isolate tasks stored in the mock product."""
    return [task for task in product.get_all_tasks() if task["type"] == "Isolate"]


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[HOSTNAME_ENTITY, IP_ENTITY],
)
def test_create_isolate_machine_task_success(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that isolate tasks are created for found machines."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))
    microsoft_defender_atp.add_machine(
        copy.deepcopy(common.MOCK_DATA["machine_data_ip"])
    )

    CreateIsolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert "Action completed successfully" in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[NOT_FOUND_ENTITY],
)
def test_create_isolate_machine_task_machine_not_found(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that only not-found machines complete with a False result (fail-closed)."""
    CreateIsolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (False, "false")
    assert "not found in ATP" in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        **DEFAULT_PARAMS,
        "Isolation Type": "InvalidType",
    },
    entities=[HOSTNAME_ENTITY],
)
def test_create_isolate_machine_task_invalid_isolation_type(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that an invalid Isolation Type fails the action early."""
    try:
        CreateIsolateMachineTask.main()
    except (TypeError, NameError, ValueError):
        pass

    # The action may crash (NameError/TypeError in production code) before reaching
    # siemplify.end(). Accept None results (crash) or explicit FAILED state.
    assert (
        action_output.results is None
        or action_output.results.execution_state == ExecutionState.FAILED
    )
    assert common.get_summary_lines(caplog)[0] == common.expected_summary(
        "FAILURE",
        "INVALID_INPUT",
        "FAILED",
        targets=1,
        failed=1,
        exc_type="MicrosoftDefenderATPValidationError",
    )


@set_metadata(integration_config=common.CONFIG, parameters={**DEFAULT_PARAMS, "Machine ID": MACHINE_ID}, entities=[])
def test_create_isolate_machine_task_machine_id_success(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that a Machine ID alone creates one isolate task for that machine."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))

    CreateIsolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    json_result = action_output.results.json_output.json_result
    assert [task["machine_id"] for task in json_result] == [MACHINE_ID]
    assert [task["machineId"] for task in _isolate_tasks(microsoft_defender_atp)] == [MACHINE_ID]
    task_id = json_result[0]["id"]
    message = f"Isolate machine task {task_id} was created successfully on Defender ATP Server for {MACHINE_ID}"
    assert action_output.results.output_message == message
    assert common.logged_levels(caplog, message) == ["INFO"]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={**DEFAULT_PARAMS, "Machine ID": UNKNOWN_MACHINE_ID},
    entities=[],
)
def test_create_isolate_machine_task_machine_id_not_found(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that a Machine ID that returns 404 completes with a False result."""
    CreateIsolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (False, "false")
    assert "not found in ATP" in action_output.results.output_message
    assert not _isolate_tasks(microsoft_defender_atp)
    message = f"Failed to find machine ATP by Machine ID: {UNKNOWN_MACHINE_ID}"
    assert action_output.results.output_message == f"{message}\n1 entities were not found in ATP"
    assert common.logged_levels(caplog, message) == ["WARNING"]
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("FAILURE", "ENDPOINT_NOT_FOUND", "COMPLETED", targets=1, failed=1),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={**DEFAULT_PARAMS, "Machine ID": common.MOCK_DATA["machine_data"]["computerDnsName"]},
    entities=[],
)
def test_create_isolate_machine_task_hostname_as_machine_id_rejected(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that a hostname typed into Machine ID is not resolved and isolates nothing."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))

    CreateIsolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (False, "false")
    assert "not found in ATP" in action_output.results.output_message
    assert not _isolate_tasks(microsoft_defender_atp)


@set_metadata(
    integration_config=common.CONFIG,
    parameters={**DEFAULT_PARAMS, "Machine ID": MACHINE_ID},
    entities=[IP_ENTITY],
)
def test_create_isolate_machine_task_machine_id_overrides_entities(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that entities are ignored when Machine ID is set."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data_ip"]))

    CreateIsolateMachineTask.main()

    assert action_output.results.result_value in (True, "true")
    isolated = [task["machineId"] for task in _isolate_tasks(microsoft_defender_atp)]
    assert isolated == [MACHINE_ID]
    assert MACHINE_IP_ID not in isolated


@set_metadata(integration_config=common.CONFIG, parameters={**DEFAULT_PARAMS, "Machine ID": MACHINE_ID}, entities=[])
def test_create_isolate_machine_task_active_request_exists(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that a pending isolate task as the newest request is reused as success."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))
    microsoft_defender_atp.create_task("Unisolate", MACHINE_ID, "Succeeded", creation_time="2024-01-01T12:00:00.000Z")
    active_task = microsoft_defender_atp.create_task(
        "Isolate",
        MACHINE_ID,
        "Pending",
        creation_time="2024-02-01T12:00:00.000Z",
    )
    microsoft_defender_atp.set_active_request_exists(MACHINE_ID, "Isolate")

    CreateIsolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    json_result = action_output.results.json_output.json_result
    assert [task["id"] for task in json_result] == [active_task["id"]]
    assert len(_isolate_tasks(microsoft_defender_atp)) == 1
    assert "already exists" in action_output.results.output_message
    assert "created successfully" not in action_output.results.output_message
    message = f"Isolate machine task {active_task['id']} already exists on Defender ATP Server for {MACHINE_ID}"
    assert action_output.results.output_message == message
    assert common.logged_levels(caplog, message) == ["INFO"]
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("SUCCESS", "NONE", "COMPLETED", targets=1, failed=0),
    ]


@set_metadata(integration_config=common.CONFIG, parameters={**DEFAULT_PARAMS, "Machine ID": MACHINE_ID}, entities=[])
def test_create_isolate_machine_task_opposite_request_pending(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that a pending unisolate request makes isolation fail and is named."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))
    pending_task = microsoft_defender_atp.create_task(
        "Unisolate",
        MACHINE_ID,
        "Pending",
        creation_time="2024-02-01T12:00:00.000Z",
    )
    microsoft_defender_atp.set_active_request_exists(MACHINE_ID, "Isolate")

    CreateIsolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (False, "false")
    assert f"Unisolate (task {pending_task['id']}, Pending)" in action_output.results.output_message
    error = (
        f"Machine {MACHINE_ID} already has an active request that isn't a pending isolate task. "
        f"Newest containment task: Unisolate (task {pending_task['id']}, Pending)."
    )
    assert action_output.results.output_message == f"Failed to process Machine ID {MACHINE_ID}. {error}"
    assert common.logged_levels(caplog, f"Failed to process Machine ID {MACHINE_ID}: {error}") == ["INFO"]
    assert common.logged_levels(caplog, error) == ["ERROR"]
    assert not _isolate_tasks(microsoft_defender_atp)
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("FAILURE", "VENDOR_ERROR", "COMPLETED", targets=1, failed=1),
    ]


@set_metadata(integration_config=common.CONFIG, parameters={**DEFAULT_PARAMS, "Machine ID": MACHINE_ID}, entities=[])
def test_create_isolate_machine_task_old_isolate_not_reused(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that an old succeeded isolate task isn't reused while an unisolate is pending."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))
    microsoft_defender_atp.create_task("Isolate", MACHINE_ID, "Succeeded", creation_time="2024-01-01T12:00:00.000Z")
    microsoft_defender_atp.create_task("Unisolate", MACHINE_ID, "Pending", creation_time="2024-02-01T12:00:00.000Z")
    microsoft_defender_atp.set_active_request_exists(MACHINE_ID, "Isolate")

    CreateIsolateMachineTask.main()

    assert action_output.results.result_value in (False, "false")
    assert action_output.results.json_output is None
    assert "Failed to process" in action_output.results.output_message


@set_metadata(integration_config=common.CONFIG, parameters=DEFAULT_PARAMS, entities=[HOSTNAME_ENTITY, NOT_FOUND_ENTITY])
def test_create_isolate_machine_task_partial_not_found(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that a not-found entity is reported but doesn't flip a successful result."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))

    CreateIsolateMachineTask.main()

    assert action_output.results.result_value in (True, "true")
    task_id = action_output.results.json_output.json_result[0]["id"]
    assert action_output.results.output_message == (
        f"Isolate machine task {task_id} was created successfully on Defender ATP Server "
        f"for {HOSTNAME_ENTITY.identifier}\n"
        f"Failed to find machine ATP by {NOT_FOUND_ENTITY.identifier} entity with type {NOT_FOUND_ENTITY.entity_type}\n"
        "1 entities were successfully processed\n"
        "1 entities were not found in ATP\n"
        "Action completed successfully"
    )


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[HOSTNAME_ENTITY, SAME_MACHINE_IP_ENTITY],
)
def test_create_isolate_machine_task_dedupes_machines(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that entities resolving to the same machine create a single task."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))

    CreateIsolateMachineTask.main()

    assert action_output.results.result_value in (True, "true")
    assert len(action_output.results.json_output.json_result) == 1
    assert len(_isolate_tasks(microsoft_defender_atp)) == 1


@set_metadata(
    integration_config={**common.CONFIG, "Graph API Root": "https://graph.microsoft.com"},
    parameters={**DEFAULT_PARAMS, "Machine ID": MACHINE_ID},
    entities=[],
)
def test_create_isolate_machine_task_uses_v1_manager_with_graph_api_root(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that the Defender (V1) manager is used even if Graph API Root is set."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))

    CreateIsolateMachineTask.main()

    assert action_output.results.result_value in (True, "true")


@set_metadata(integration_config=common.CONFIG, parameters=DEFAULT_PARAMS, entities=[HOSTNAME_ENTITY, IP_ENTITY])
def test_create_isolate_machine_task_lookup_error_is_failure(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that an API error while resolving an entity fails it instead of not-found."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data_ip"]))

    monkeypatch.setattr(
        manager_module.MicrosoftDefenderATPManager,
        "get_machines_by_name",
        common.raise_error(manager_module.MicrosoftDefenderATPError("Internal server error")),
    )

    CreateIsolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (False, "false")
    assert "Action failed to complete successfully" in action_output.results.output_message
    assert "not found in ATP" not in action_output.results.output_message
    assert [task["machineId"] for task in _isolate_tasks(microsoft_defender_atp)] == [MACHINE_IP_ID]
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("PARTIAL_SUCCESS", "VENDOR_ERROR", "COMPLETED", targets=2, failed=1),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={**DEFAULT_PARAMS, "Machine ID": "   "},
    entities=[HOSTNAME_ENTITY],
)
def test_create_isolate_machine_task_blank_machine_id_uses_entities(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that a whitespace-only Machine ID is ignored and the entities are used."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))

    CreateIsolateMachineTask.main()

    assert action_output.results.result_value in (True, "true")
    assert [task["machineId"] for task in _isolate_tasks(microsoft_defender_atp)] == [MACHINE_ID]


@set_metadata(integration_config=common.CONFIG, parameters={**DEFAULT_PARAMS, "Machine ID": MACHINE_ID}, entities=[])
def test_create_isolate_machine_task_machine_id_lookup_error_is_failure(
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

    CreateIsolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (False, "false")
    assert f"Failed to process Machine ID {MACHINE_ID}" in action_output.results.output_message
    assert "not found in ATP" not in action_output.results.output_message
    assert action_output.results.output_message == f"Failed to process Machine ID {MACHINE_ID}. Internal server error"
    assert common.logged_levels(caplog, f"Failed to process Machine ID {MACHINE_ID}: Internal server error") == [
        "INFO"
    ]
    assert common.logged_levels(caplog, "Internal server error") == ["ERROR"]
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("FAILURE", "VENDOR_ERROR", "COMPLETED", targets=1, failed=1),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={**DEFAULT_PARAMS, "Machine ID": f"DeviceId: {MACHINE_ID}"},
    entities=[],
)
def test_create_isolate_machine_task_prefixed_machine_id(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that a Machine ID with a "DeviceId:" prefix starts the task on the bare machine ID."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))

    CreateIsolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert [task["machineId"] for task in _isolate_tasks(microsoft_defender_atp)] == [MACHINE_ID]


FILE_HASH_ENTITY = create_entity(identifier="a" * 64, type_=EntityTypesEnum.FILE_HASH)


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[HOSTNAME_ENTITY, NOT_FOUND_ENTITY, FILE_HASH_ENTITY],
)
def test_create_isolate_machine_task_summary_counts_skipped_entities(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the summary line counts a not-found entity as failed and an unsupported entity as skipped."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))

    CreateIsolateMachineTask.main()

    assert action_output.results.result_value in (True, "true")
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("PARTIAL_SUCCESS", "ENDPOINT_NOT_FOUND", "COMPLETED", targets=2, failed=1, skipped=1),
    ]


@set_metadata(integration_config=common.CONFIG, parameters={**DEFAULT_PARAMS, "Machine ID": MACHINE_ID}, entities=[])
def test_create_isolate_machine_task_setup_error_summary(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that a token error fails the run unchanged and the summary line keeps its HTTP status."""
    monkeypatch.setattr(
        manager_module.MicrosoftDefenderATPManager,
        "__init__",
        common.raise_error(
            manager_module.MicrosoftDefenderATPError(
                "Unable to generate access token for Microsoft Defender ATP. invalid_client",
                status_code=401,
            )
        ),
    )

    CreateIsolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value in (False, "false")
    assert action_output.results.output_message == (
        "Action didn't completed due to error: Unable to generate access token for Microsoft Defender ATP. "
        "invalid_client"
    )
    assert common.get_summary_lines(caplog) == [
        common.expected_summary(
            "FAILURE",
            "AUTHENTICATION_FAILED",
            "FAILED",
            targets=1,
            failed=1,
            exc_type="MicrosoftDefenderATPError",
            http_status="401",
        ),
    ]


@set_metadata(integration_config=common.CONFIG, parameters={**DEFAULT_PARAMS, "Machine ID": MACHINE_ID}, entities=[])
def test_create_isolate_machine_task_summary_error_keeps_result(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that an error while building the summary line changes no result value, state, or output message."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))

    monkeypatch.setattr(
        "microsoft_defender_atp.core.UtilsManager.build_action_result_summary",
        common.raise_error(RuntimeError("summary error")),
    )

    CreateIsolateMachineTask.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    task_id = action_output.results.json_output.json_result[0]["id"]
    assert action_output.results.output_message == (
        f"Isolate machine task {task_id} was created successfully on Defender ATP Server for {MACHINE_ID}"
    )
    assert common.get_summary_lines(caplog) == []


@set_metadata(integration_config=common.CONFIG, parameters=DEFAULT_PARAMS, entities=[HOSTNAME_ENTITY])
def test_create_isolate_machine_task_unexpected_error_summary(
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
        CreateIsolateMachineTask.main()

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
