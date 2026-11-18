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
import functools
import hashlib
import json
import pathlib
import sys
import tempfile
import unittest.mock
from typing import TYPE_CHECKING

import pytest
from integration_testing.common import create_entity
from integration_testing.platform.input_context import get_mock_input_context
from integration_testing.set_meta import set_metadata
from soar_sdk.SiemplifyBase import SiemplifyBase
from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC

from microsoft_defender_atp.actions import AcquireFile
from microsoft_defender_atp.core.MicrosoftDefenderATPManager import MicrosoftDefenderATPError
from microsoft_defender_atp.tests import common
from microsoft_defender_atp.tests.core.product import DEFAULT_ACQUIRED_CONTENT, MicrosoftDefenderATP

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput
    from TIPCommon.types import SingleJson

    from microsoft_defender_atp.tests.core.session import MicrosoftDefenderATPSession

MACHINE: SingleJson = common.MOCK_DATA["machine_data"]
MACHINE_ID: str = MACHINE["id"]
HOSTNAME: str = MACHINE["computerDnsName"]
HOSTNAME_ENTITY = create_entity(identifier=HOSTNAME, type_=EntityTypesEnum.HOST_NAME)
UNRELATED_IP_ENTITY = create_entity(identifier="10.10.10.10", type_=EntityTypesEnum.ADDRESS)
WIN_INI: str = "C:\\Windows\\win.ini"
DEADLINE: int = int((datetime.datetime.now() + datetime.timedelta(minutes=10)).timestamp() * NUM_OF_MILLI_IN_SEC)
ENTITY_RESULT_KEYS: set[str] = {
    "action",
    "machine_id",
    "file_path",
    "file_name",
    "download_path",
    "md5",
    "sha1",
    "sha256",
    "size",
    "status",
    "created_at",
    "completed_at",
}


def _context() -> SingleJson:
    """Return a fresh input context (set_metadata stores parameters into it)."""
    return {"async_total_duration_deadline": DEADLINE}


@pytest.fixture(name="run_folder", autouse=True)
def run_folder_fixture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    microsoft_defender_atp: MicrosoftDefenderATP,
) -> pathlib.Path:
    """Seed the target machine, force a first async run and redirect run_folder."""
    microsoft_defender_atp.add_machine(copy.deepcopy(MACHINE))
    monkeypatch.setattr(sys, "argv", ["", "", "True"])
    monkeypatch.setattr(SiemplifyBase, "run_folder", str(tmp_path))
    return tmp_path


def _poll(
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    deadline: int = DEADLINE,
    additional_data: str | None = None,
    polling_interval: int = 0,
) -> None:
    """Re-run the action as an async polling run with the previous run's state (or additional_data)."""
    context = {
        "parameters": {"additional_data": additional_data or action_output.results.result_value},
        "async_total_duration_deadline": deadline,
        "async_polling_interval_in_sec": polling_interval,
    }
    action_output.flush()
    monkeypatch.setattr(sys, "argv", ["", "", "False"])
    with unittest.mock.patch(
        "soar_sdk.SiemplifyBase.SiemplifyBase.get_script_context",
        functools.partial(get_mock_input_context, context=context),
    ):
        AcquireFile.main()


def _live_response_bodies(script_session: MicrosoftDefenderATPSession) -> list[SingleJson]:
    """Return the request bodies sent to the runliveresponse endpoint."""
    return [
        record.request.kwargs["json"]
        for record in script_session.request_history
        if record.request.url.path.endswith("/runliveresponse")
    ]


def _get_file_body(path: str) -> SingleJson:
    """Return the expected runliveresponse body for a GetFile of path."""
    return {
        "Commands": [{"type": "GetFile", "params": [{"key": "Path", "value": path}]}],
        "Comment": "Acquire File via Google SecOps",
    }


def _entity_results(action_output: MockActionOutput) -> SingleJson:
    """Map each JSON result Entity to its EntityResult."""
    return {item["Entity"]: item["EntityResult"] for item in action_output.results.json_output.json_result}


def _state(action_output: MockActionOutput) -> SingleJson:
    """Return the async state carried in the IN_PROGRESS result value."""
    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    return json.loads(action_output.results.result_value)


def _active_task(microsoft_defender_atp: MicrosoftDefenderATP, command: SingleJson) -> str:
    """Seed an InProgress live-response action on the machine and return its ID."""
    microsoft_defender_atp.add_task(
        {
            "id": "active-action-id",
            "type": "LiveResponse",
            "status": "InProgress",
            "machineId": MACHINE_ID,
            "commands": [{"index": 0, "commandStatus": "Created", "command": command}],
        },
    )
    return "active-action-id"


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI, "Machine ID": MACHINE_ID},
    entities=[UNRELATED_IP_ENTITY],
    input_context=_context(),
)
def test_acquire_file_machine_id_success(
    microsoft_defender_atp: MicrosoftDefenderATP,
    script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    run_folder: pathlib.Path,
) -> None:
    """Machine ID overrides entities; the .gz is saved and hashed after decompression."""
    AcquireFile.main()

    assert _state(action_output)["targets"][MACHINE_ID]["status"] == "Pending"
    assert _live_response_bodies(script_session) == [_get_file_body(WIN_INI)]

    microsoft_defender_atp.set_live_response_final_status("Succeeded")
    _poll(action_output, monkeypatch)

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert "10.10.10.10" not in action_output.results.output_message
    result = _entity_results(action_output)[MACHINE_ID]
    assert set(result) == ENTITY_RESULT_KEYS
    assert result["md5"] == hashlib.md5(DEFAULT_ACQUIRED_CONTENT).hexdigest()
    assert result["sha1"] == hashlib.sha1(DEFAULT_ACQUIRED_CONTENT).hexdigest()
    assert result["sha256"] == hashlib.sha256(DEFAULT_ACQUIRED_CONTENT).hexdigest()
    assert result["size"] == len(DEFAULT_ACQUIRED_CONTENT)
    assert (result["file_path"], result["file_name"]) == (WIN_INI, "win.ini")
    download_path = pathlib.Path(result["download_path"])
    assert (download_path.parent, download_path.suffix) == (run_folder, ".gz")
    assert download_path.read_bytes() == microsoft_defender_atp.get_live_response_file_bytes()
    assert any(record.request.url.path.endswith("/AddAttachment") for record in script_session.request_history)


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI, "Machine ID": "   "},
    entities=[HOSTNAME_ENTITY],
    input_context=_context(),
)
def test_acquire_file_entity_success(
    microsoft_defender_atp: MicrosoftDefenderATP,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A whitespace Machine ID falls back to entities; results are keyed by entity."""
    AcquireFile.main()
    microsoft_defender_atp.set_live_response_final_status("Succeeded")
    _poll(action_output, monkeypatch)

    assert action_output.results.result_value is True
    assert _entity_results(action_output)[HOSTNAME]["machine_id"] == MACHINE_ID


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": "%SystemRoot%\\\\win.ini", "Machine ID": MACHINE_ID},
    input_context=_context(),
)
def test_acquire_file_systemroot_normalized(
    script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """%systemroot% is expanded and repeated backslashes are collapsed."""
    AcquireFile.main()

    assert _state(action_output)["file_path"] == WIN_INI
    assert _live_response_bodies(script_session) == [_get_file_body(WIN_INI)]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": "\\\\fs01\\\\\\share\\a.txt", "Machine ID": MACHINE_ID},
    input_context=_context(),
)
def test_acquire_file_unc_prefix_preserved(
    script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """A leading UNC prefix is kept while inner repeated backslashes are collapsed."""
    AcquireFile.main()

    assert _live_response_bodies(script_session) == [_get_file_body("\\\\fs01\\share\\a.txt")]
    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": "relative\\path.txt", "Machine ID": MACHINE_ID},
    input_context=_context(),
)
def test_acquire_file_relative_path_fails(
    script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """A relative path fails the action before any machine is contacted."""
    AcquireFile.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
    assert action_output.results.output_message.startswith(
        'Error executing action "Acquire File". Reason: File path must be an absolute',
    )
    assert not _live_response_bodies(script_session)


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI, "Machine ID": "0" * 40},
    input_context=_context(),
)
def test_acquire_file_machine_not_found(action_output: MockActionOutput, caplog: pytest.LogCaptureFixture) -> None:
    """An unknown Machine ID completes with result False and a not-found message."""
    AcquireFile.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is False
    assert f"not found in Microsoft Defender for Endpoint: {'0' * 40}." in (action_output.results.output_message)
    assert _entity_results(action_output)["0" * 40]["error_type"] == "ENDPOINT_NOT_FOUND"
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("FAILURE", "ENDPOINT_NOT_FOUND", "COMPLETED", targets=1, failed=1),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI, "Machine ID": MACHINE_ID},
    input_context=_context(),
)
def test_acquire_file_command_failed(
    microsoft_defender_atp: MicrosoftDefenderATP,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Failed GetFile completes with result False and the command error text."""
    AcquireFile.main()
    microsoft_defender_atp.set_live_response_final_status("Failed", errors=["File not found"])
    _poll(action_output, monkeypatch)

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is False
    assert f"{MACHINE_ID}: File not found" in action_output.results.output_message
    results = _entity_results(action_output)
    assert results[MACHINE_ID]["status"] == "failure"
    assert results[MACHINE_ID]["error"] == "File not found"


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI, "Machine ID": MACHINE_ID},
    input_context=_context(),
)
def test_acquire_file_adopts_identical_action(
    microsoft_defender_atp: MicrosoftDefenderATP,
    script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """An active GetFile of the same path (any case) is tracked instead of re-issued."""
    command = {"type": "GetFile", "params": [{"key": "Path", "value": "c:\\windows\\WIN.INI"}]}
    action_id = _active_task(microsoft_defender_atp, command)

    AcquireFile.main()

    target = _state(action_output)["targets"][MACHINE_ID]
    assert (target["action_id"], target["status"]) == (action_id, "InProgress")
    assert not _live_response_bodies(script_session)


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI, "Machine ID": MACHINE_ID},
    input_context=_context(),
)
def test_acquire_file_waits_for_conflicting_action(
    microsoft_defender_atp: MicrosoftDefenderATP,
    script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Another active action defers the GetFile until it finishes."""
    action_id = _active_task(microsoft_defender_atp, {"type": "PutFile", "params": []})

    AcquireFile.main()

    assert _state(action_output)["targets"][MACHINE_ID]["status"] == "Waiting"
    assert not _live_response_bodies(script_session)

    microsoft_defender_atp.get_task(action_id)["status"] = "Succeeded"
    _poll(action_output, monkeypatch)

    assert _state(action_output)["targets"][MACHINE_ID]["status"] == "Pending"
    assert _live_response_bodies(script_session) == [_get_file_body(WIN_INI)]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI, "Machine ID": MACHINE_ID},
    input_context=_context(),
)
def test_acquire_file_non_gzip_payload_saved_as_bin(
    microsoft_defender_atp: MicrosoftDefenderATP,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A payload without gzip magic bytes is saved as .bin and hashed as-is."""
    microsoft_defender_atp.set_live_response_file_bytes(b"plain content")

    AcquireFile.main()
    microsoft_defender_atp.set_live_response_final_status("Succeeded")
    _poll(action_output, monkeypatch)

    result = _entity_results(action_output)[MACHINE_ID]
    assert result["download_path"].endswith(".bin")
    assert result["md5"] == hashlib.md5(b"plain content").hexdigest()


@set_metadata(
    integration_config={**common.CONFIG, "Graph API Root": "https://graph.microsoft.com"},
    parameters={"File Path": WIN_INI, "Machine ID": MACHINE_ID},
    input_context=_context(),
)
def test_acquire_file_ignores_graph_api_root(action_output: MockActionOutput, monkeypatch: pytest.MonkeyPatch) -> None:
    """The Defender-scoped V1 manager is used even when Graph API Root is configured."""
    clients = []
    init_api_clients = AcquireFile.AcquireFileAction._init_api_clients
    monkeypatch.setattr(
        AcquireFile.AcquireFileAction,
        "_init_api_clients",
        lambda self: clients.append(init_api_clients(self)) or clients[-1],
    )

    AcquireFile.main()

    assert [type(client).__name__ for client in clients] == ["MicrosoftDefenderATPManager"]
    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI, "Machine ID": MACHINE_ID},
    input_context=_context(),
)
def test_acquire_file_async_timeout(
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An expired async deadline fails the run and lists the pending endpoints."""
    AcquireFile.main()
    _poll(action_output, monkeypatch, deadline=0)

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is False
    assert "Action ran into a timeout during execution." in action_output.results.output_message
    results = _entity_results(action_output)
    assert results[MACHINE_ID]["status"] == "failure"
    assert "timeout" in results[MACHINE_ID]["error"].lower()
    assert results[MACHINE_ID]["error_type"] == "TIMEOUT"
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("FAILURE", "TIMEOUT", "COMPLETED", targets=1, failed=1),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI, "Machine ID": MACHINE_ID},
    input_context=_context(),
)
def test_acquire_file_run_folder_fallback(
    microsoft_defender_atp: MicrosoftDefenderATP,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """An inaccessible run_folder falls back to the system temp directory."""
    fallback = tmp_path / "fallback"
    fallback.mkdir()

    def _deny(_: SiemplifyBase) -> str:
        raise PermissionError("[Errno 13] Permission denied: '/opt/siemplify'")

    monkeypatch.setattr(SiemplifyBase, "run_folder", property(_deny))
    monkeypatch.setattr(tempfile, "tempdir", str(fallback))

    AcquireFile.main()
    microsoft_defender_atp.set_live_response_final_status("Succeeded")
    _poll(action_output, monkeypatch)

    download_path = pathlib.Path(_entity_results(action_output)[MACHINE_ID]["download_path"])
    assert download_path.parent == fallback
    assert download_path.is_file()


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI, "Machine ID": MACHINE_ID},
    input_context=_context(),
)
def test_acquire_file_resolution_error_counts_as_failed(
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An API error while resolving the machine is a failure, not a not-found."""

    monkeypatch.setattr(
        "microsoft_defender_atp.core.MicrosoftDefenderATPManager.MicrosoftDefenderATPManager.get_machine_by_id",
        common.raise_error(MicrosoftDefenderATPError("Service unavailable")),
    )

    AcquireFile.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is False
    assert f"{MACHINE_ID}: Service unavailable" in action_output.results.output_message
    assert "not found" not in action_output.results.output_message
    assert _entity_results(action_output)[MACHINE_ID]["error_type"] == "VENDOR_ERROR"


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI},
    entities=[HOSTNAME_ENTITY, UNRELATED_IP_ENTITY],
    input_context=_context(),
)
def test_acquire_file_json_results_completeness_with_not_found(
    microsoft_defender_atp: MicrosoftDefenderATP,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Successful, failed, and not-found entities are all present in JSON results."""
    AcquireFile.main()
    microsoft_defender_atp.set_live_response_final_status("Succeeded")
    _poll(action_output, monkeypatch)

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    results = _entity_results(action_output)
    assert HOSTNAME in results
    assert results[HOSTNAME]["status"] == "success"
    assert "10.10.10.10" in results
    assert results["10.10.10.10"]["status"] == "failure"
    assert "not found" in results["10.10.10.10"]["error"].lower()
    assert results["10.10.10.10"]["error_type"] == "ENDPOINT_NOT_FOUND"
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("PARTIAL_SUCCESS", "ENDPOINT_NOT_FOUND", "COMPLETED", targets=2, failed=1),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI},
    entities=[HOSTNAME_ENTITY, create_entity("10.0.0.99", type_=EntityTypesEnum.ADDRESS)],
    input_context=_context(),
)
def test_acquire_file_timeout_preserves_completed_targets(
    microsoft_defender_atp: MicrosoftDefenderATP,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Timeout preserves results of targets completed in earlier polls."""
    second_machine = dict(MACHINE)
    second_machine["id"] = "b" * 40
    second_machine["lastIpAddress"] = "10.0.0.99"
    second_machine["computerDnsName"] = "desktop-second"
    microsoft_defender_atp.add_machine(second_machine)

    AcquireFile.main()

    # Finish the first machine's action only
    first_target = _state(action_output)["targets"][MACHINE_ID]
    first_action_id = first_target["action_id"]

    def _get_status(aid: str) -> SingleJson:
        if aid == first_action_id:
            return {"id": aid, "status": "Succeeded", "commands": []}
        return {"id": aid, "status": "Pending", "commands": []}

    monkeypatch.setattr(
        "microsoft_defender_atp.core.MicrosoftDefenderATPManager.MicrosoftDefenderATPManager.get_live_response_status",
        lambda self, aid: _get_status(aid),
    )

    _poll(action_output, monkeypatch)

    # Now simulate approaching timeout on the second machine
    _poll(action_output, monkeypatch, deadline=0)

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is False
    results = _entity_results(action_output)
    assert HOSTNAME in results
    assert results[HOSTNAME]["status"] == "success"
    assert "10.0.0.99" in results
    assert results["10.0.0.99"]["status"] == "failure"
    assert "timeout" in results["10.0.0.99"]["error"].lower()


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI, "Machine ID": MACHINE_ID},
    input_context=_context(),
)
def test_acquire_file_exception_isolation(action_output: MockActionOutput, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unexpected exception on target is caught, logged, and isolated."""

    monkeypatch.setattr(
        "microsoft_defender_atp.core.MicrosoftDefenderATPManager.MicrosoftDefenderATPManager.run_live_response_command",
        common.raise_error(RuntimeError("Unexpected internal crash")),
    )

    AcquireFile.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is False
    assert "Unexpected internal crash" in action_output.results.output_message
    results = _entity_results(action_output)
    assert results[MACHINE_ID]["status"] == "failure"
    assert "Unexpected internal crash" in results[MACHINE_ID]["error"]


def _failure(error: str, error_type: str) -> SingleJson:
    """Return the JSON result entry of a failed target."""
    return {"status": "failure", "error": error, "error_type": error_type}


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": "relative\\path.txt", "Machine ID": MACHINE_ID},
    input_context=_context(),
)
def test_acquire_file_invalid_path_json_result(
    action_output: MockActionOutput,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An invalid File Path sends a failure entry keyed by the Machine ID."""
    AcquireFile.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    expected = {MACHINE_ID: _failure(action_output.results.output_message, "INVALID_INPUT")}
    assert _entity_results(action_output) == expected
    assert "must be an absolute" in _entity_results(action_output)[MACHINE_ID]["error"]
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("FAILURE", "INVALID_INPUT", "FAILED", targets=1, failed=1),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI},
    entities=[create_entity("c" * 64, type_=EntityTypesEnum.FILE_HASH)],
    input_context=_context(),
)
def test_acquire_file_no_targets_json_result(action_output: MockActionOutput, caplog: pytest.LogCaptureFixture) -> None:
    """Without Machine ID or supported entities, the failure is keyed by the integration name."""
    AcquireFile.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is False
    assert action_output.results.output_message == f'None of the provided endpoints returned file "{WIN_INI}".'
    assert _entity_results(action_output) == {
        AcquireFile.constants.INTEGRATION_IDENTIFIER: _failure(action_output.results.output_message, "INVALID_INPUT"),
    }
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("FAILURE", "INVALID_INPUT", "COMPLETED", targets=0, failed=0, skipped=1),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI},
    entities=[HOSTNAME_ENTITY, UNRELATED_IP_ENTITY],
    input_context=_context(),
)
def test_acquire_file_setup_error_json_result(
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A setup error sends a failure entry for each supported entity."""
    monkeypatch.setattr(
        AcquireFile.AcquireFileAction,
        "_init_api_clients",
        common.raise_error(RuntimeError("Invalid credentials")),
    )

    AcquireFile.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
    assert _entity_results(action_output) == {
        HOSTNAME: _failure("Invalid credentials", "UNKNOWN_ERROR"),
        "10.10.10.10": _failure("Invalid credentials", "UNKNOWN_ERROR"),
    }
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("FAILURE", "UNKNOWN_ERROR", "FAILED", targets=2, failed=2, exc_type="RuntimeError"),
    ]


@set_metadata(integration_config=common.CONFIG, parameters={"Machine ID": MACHINE_ID}, input_context=_context())
def test_acquire_file_missing_file_path_json_result(
    action_output: MockActionOutput,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A missing File Path on the first run fails the action with a failure entry."""
    AcquireFile.main()

    output_message = action_output.results.output_message
    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
    assert output_message.startswith('Error executing action "Acquire File". Reason: ')
    assert "Missing mandatory parameter File Path" in output_message
    assert _entity_results(action_output) == {MACHINE_ID: _failure(output_message, "INVALID_INPUT")}
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("FAILURE", "INVALID_INPUT", "FAILED", targets=1, failed=1, exc_type="Exception"),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI},
    entities=[HOSTNAME_ENTITY, create_entity("10.0.0.99", type_=EntityTypesEnum.ADDRESS)],
    input_context=_context(),
)
def test_acquire_file_raised_poll_error_keeps_completed_targets(
    microsoft_defender_atp: MicrosoftDefenderATP,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A raised error on a later poll keeps earlier successes and fails pending targets."""
    success = _finish_first_of_two_targets(microsoft_defender_atp, action_output, monkeypatch)

    monkeypatch.setattr(
        AcquireFile,
        "is_approaching_action_timeout",
        common.raise_error(RuntimeError("Unexpected polling error")),
    )
    _poll(action_output, monkeypatch)

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
    expected = {HOSTNAME: success, "10.0.0.99": _failure("Unexpected polling error", "UNKNOWN_ERROR")}
    assert _entity_results(action_output) == expected
    assert common.get_summary_lines(caplog) == [
        common.expected_summary(
            "PARTIAL_SUCCESS",
            "UNKNOWN_ERROR",
            "FAILED",
            targets=2,
            failed=1,
            exc_type="RuntimeError",
        ),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI},
    entities=[HOSTNAME_ENTITY, create_entity("10.0.0.99", type_=EntityTypesEnum.ADDRESS)],
    input_context=_context(),
)
def test_acquire_file_setup_error_on_later_poll_keeps_completed_targets(
    microsoft_defender_atp: MicrosoftDefenderATP,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A setup error on a later poll, before the state is loaded, keeps earlier successes."""
    success = _finish_first_of_two_targets(microsoft_defender_atp, action_output, monkeypatch)

    monkeypatch.setattr(
        AcquireFile.AcquireFileAction,
        "_init_api_clients",
        common.raise_error(RuntimeError("Token request failed")),
    )
    _poll(action_output, monkeypatch)

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
    expected = {HOSTNAME: success, "10.0.0.99": _failure("Token request failed", "UNKNOWN_ERROR")}
    assert _entity_results(action_output) == expected


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI},
    entities=[HOSTNAME_ENTITY],
    input_context=_context(),
)
def test_acquire_file_unreadable_state_keeps_original_error(
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the saved state can't be read, the failure hook falls back to failure entries and keeps the error."""
    monkeypatch.setattr(
        AcquireFile.AcquireFileAction,
        "_init_api_clients",
        common.raise_error(RuntimeError("Token request failed")),
    )
    _poll(action_output, monkeypatch, additional_data="{not json")

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.output_message.endswith("Reason: Token request failed")
    assert _entity_results(action_output) == {HOSTNAME: _failure("Token request failed", "UNKNOWN_ERROR")}


def _finish_first_of_two_targets(
    microsoft_defender_atp: MicrosoftDefenderATP,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> SingleJson:
    """Run the first run and one poll: the first target succeeds, the second stays pending.

    Returns:
        The success entry of the first target.
    """
    second_machine = dict(MACHINE)
    second_machine["id"] = "b" * 40
    second_machine["lastIpAddress"] = "10.0.0.99"
    second_machine["computerDnsName"] = "desktop-second"
    microsoft_defender_atp.add_machine(second_machine)

    AcquireFile.main()
    first_action_id = _state(action_output)["targets"][MACHINE_ID]["action_id"]
    monkeypatch.setattr(
        "microsoft_defender_atp.core.MicrosoftDefenderATPManager.MicrosoftDefenderATPManager.get_live_response_status",
        lambda _, aid: {"id": aid, "status": "Succeeded" if aid == first_action_id else "Pending", "commands": []},
    )
    _poll(action_output, monkeypatch)

    return _state(action_output)["targets"][MACHINE_ID]["result"]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI, "Machine ID": MACHINE_ID},
    input_context=_context(),
)
@pytest.mark.parametrize(
    ("status", "errors", "error_type"),
    [
        ("Failed", ["File C:\\Windows\\win.ini could not be located"], "FILE_NOT_FOUND"),
        ("TimeOut", None, "TIMEOUT"),
        ("Cancelled", None, "CANCELLED"),
        ("Failed", ["Unexpected agent error"], "VENDOR_ERROR"),
    ],
)
def test_acquire_file_live_response_failure_error_type(
    microsoft_defender_atp: MicrosoftDefenderATP,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    status: str,
    errors: list[str] | None,
    error_type: str,
) -> None:
    """A finished GetFile without success gets an error_type, and only the final run logs the summary line."""
    AcquireFile.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    assert common.get_summary_lines(caplog) == []

    microsoft_defender_atp.set_live_response_final_status(status, errors=errors)
    _poll(action_output, monkeypatch)

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is False
    assert _entity_results(action_output)[MACHINE_ID]["error_type"] == error_type
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("FAILURE", error_type, "COMPLETED", targets=1, failed=1),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI, "Machine ID": MACHINE_ID},
    input_context=_context(),
)
def test_acquire_file_success_summary_line(
    microsoft_defender_atp: MicrosoftDefenderATP,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A successful acquisition logs one SUCCESS summary line and keeps the success entry shape."""
    AcquireFile.main()
    microsoft_defender_atp.set_live_response_final_status("Succeeded")
    _poll(action_output, monkeypatch)

    assert set(_entity_results(action_output)[MACHINE_ID]) == ENTITY_RESULT_KEYS
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("SUCCESS", "NONE", "COMPLETED", targets=1, failed=0),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI, "Machine ID": MACHINE_ID},
    input_context=_context(),
)
def test_acquire_file_lookup_http_status_error_type(
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A lookup error with HTTP status 403 is tagged PERMISSION_DENIED, not ENDPOINT_NOT_FOUND."""
    monkeypatch.setattr(
        "microsoft_defender_atp.core.MicrosoftDefenderATPManager.MicrosoftDefenderATPManager.get_machine_by_id",
        common.raise_error(MicrosoftDefenderATPError("Failed to get machine.", status_code=403)),
    )

    AcquireFile.main()

    assert action_output.results.result_value is False
    assert _entity_results(action_output) == {MACHINE_ID: _failure("Failed to get machine.", "PERMISSION_DENIED")}
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("FAILURE", "PERMISSION_DENIED", "COMPLETED", targets=1, failed=1),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI, "Machine ID": MACHINE_ID},
    input_context={"async_total_duration_deadline": DEADLINE, "async_polling_interval_in_sec": 3600},
)
def test_acquire_file_timeout_marker_logged_once(
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If the next poll can miss the async deadline, one IN_PROGRESS TIMEOUT marker is logged and the run continues."""
    AcquireFile.main()

    assert _state(action_output)[AcquireFile.constants.TIMEOUT_MARKER_STATE_KEY] is True
    assert action_output.results.output_message.startswith(f'Waiting for file "{WIN_INI}"')

    _poll(action_output, monkeypatch, polling_interval=3600)

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("FAILURE", "TIMEOUT", "IN_PROGRESS", targets=1, failed=1),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI, "Machine ID": MACHINE_ID},
    input_context={"async_total_duration_deadline": DEADLINE, "async_polling_interval_in_sec": 3600},
)
def test_acquire_file_timeout_marker_error_keeps_state(
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If the timeout marker check raises, the run stays IN_PROGRESS, warns, and logs no summary line."""
    monkeypatch.setattr(AcquireFile, "unix_now", common.raise_error(RuntimeError("clock error")))

    AcquireFile.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    assert AcquireFile.constants.TIMEOUT_MARKER_STATE_KEY not in _state(action_output)
    assert common.logged_levels(caplog, "Failed to log timeout summary marker: clock error") == ["WARNING"]
    assert common.get_summary_lines(caplog) == []


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI, "Machine ID": MACHINE_ID},
    input_context={"async_total_duration_deadline": DEADLINE, "async_polling_interval_in_sec": 3600},
)
def test_acquire_file_timeout_marker_broken_logger_keeps_state(
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If both the timeout marker check and logger.warn raise, the run still stays IN_PROGRESS."""
    monkeypatch.setattr(AcquireFile, "unix_now", common.raise_error(RuntimeError("clock error")))
    monkeypatch.setattr(
        "TIPCommon.base.utils.NewLineLogger.warn",
        common.raise_error(RuntimeError("logger error")),
    )

    AcquireFile.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    assert AcquireFile.constants.TIMEOUT_MARKER_STATE_KEY not in _state(action_output)


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI},
    entities=[HOSTNAME_ENTITY],
    input_context=_context(),
)
def test_acquire_file_previous_version_state_loads(
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Async state saved by the previous version (no error types) still loads; failures get UNKNOWN_ERROR."""
    old_state = {
        "file_path": WIN_INI,
        "comment": "Acquire File via Google SecOps",
        "failed": {"10.0.0.99": "Lookup failed"},
        "not_found": [],
        "targets": {
            MACHINE_ID: {"entities": [HOSTNAME], "status": "Failed", "action_id": "a", "error": "Old failure"},
        },
    }

    _poll(action_output, monkeypatch, additional_data=json.dumps(old_state))

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is False
    assert _entity_results(action_output) == {
        HOSTNAME: _failure("Old failure", "UNKNOWN_ERROR"),
        "10.0.0.99": _failure("Lookup failed", "UNKNOWN_ERROR"),
    }
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("FAILURE", "UNKNOWN_ERROR", "COMPLETED", targets=2, failed=2),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI, "Machine ID": MACHINE_ID},
    input_context=_context(),
)
def test_acquire_file_summary_error_keeps_action_result(
    microsoft_defender_atp: MicrosoftDefenderATP,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If building the summary line raises, the result value, state, and output message do not change."""
    monkeypatch.setattr(
        "microsoft_defender_atp.core.UtilsManager.build_action_result_summary",
        common.raise_error(RuntimeError("summary error")),
    )

    AcquireFile.main()
    microsoft_defender_atp.set_live_response_final_status("Failed", errors=["File not found"])
    _poll(action_output, monkeypatch)

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is False
    assert f"{MACHINE_ID}: File not found" in action_output.results.output_message
    assert common.get_summary_lines(caplog) == []


FILE_HASH_ENTITY = create_entity(identifier="c" * 64, type_=EntityTypesEnum.FILE_HASH)
# A case Manual Action with "Specific" scope can give a poll all case entities, not only the first-run targets.
CASE_ENTITIES = [HOSTNAME_ENTITY, UNRELATED_IP_ENTITY, FILE_HASH_ENTITY]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI},
    entities=[HOSTNAME_ENTITY, FILE_HASH_ENTITY],
    input_context=_context(),
)
def test_acquire_file_first_run_saves_summary_scope(action_output: MockActionOutput) -> None:
    """The first run saves the targets in scope and the skipped entities in the async state."""
    AcquireFile.main()

    state = _state(action_output)
    assert (state["target_count"], state["unsupported_count"]) == (1, 1)


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI},
    entities=[HOSTNAME_ENTITY],
    input_context=_context(),
)
def test_acquire_file_poll_with_changed_scope_logs_first_run_counts(
    microsoft_defender_atp: MicrosoftDefenderATP,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If the poll gets more entities than the first run, the summary line uses the first-run counts."""
    AcquireFile.main()
    microsoft_defender_atp.set_live_response_final_status("Succeeded")
    with unittest.mock.patch("soar_sdk.SiemplifyAction.SiemplifyAction.target_entities", CASE_ENTITIES):
        _poll(action_output, monkeypatch)

    assert action_output.results.result_value is True
    assert list(_entity_results(action_output)) == [HOSTNAME]
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("SUCCESS", "NONE", "COMPLETED", targets=1, failed=0),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI},
    entities=[HOSTNAME_ENTITY],
    input_context=_context(),
)
def test_acquire_file_raised_poll_error_with_changed_scope_logs_first_run_counts(
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If a poll with more entities raises, unfinished targets are counted from the first-run scope."""
    AcquireFile.main()

    monkeypatch.setattr(
        AcquireFile,
        "is_approaching_action_timeout",
        common.raise_error(RuntimeError("Unexpected polling error")),
    )
    with unittest.mock.patch("soar_sdk.SiemplifyAction.SiemplifyAction.target_entities", CASE_ENTITIES):
        _poll(action_output, monkeypatch)

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert _entity_results(action_output) == {HOSTNAME: _failure("Unexpected polling error", "UNKNOWN_ERROR")}
    assert common.get_summary_lines(caplog) == [
        common.expected_summary(
            "FAILURE",
            "UNKNOWN_ERROR",
            "FAILED",
            targets=1,
            failed=1,
            exc_type="RuntimeError",
        ),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"File Path": WIN_INI},
    entities=[HOSTNAME_ENTITY],
    input_context=_context(),
)
def test_acquire_file_poll_with_previous_version_state_counts_current_entities(
    microsoft_defender_atp: MicrosoftDefenderATP,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Async state without a saved scope falls back to the target entities of the poll."""
    AcquireFile.main()
    state = _state(action_output)
    state.pop("target_count", None)
    state.pop("unsupported_count", None)
    microsoft_defender_atp.set_live_response_final_status("Succeeded")
    with unittest.mock.patch("soar_sdk.SiemplifyAction.SiemplifyAction.target_entities", CASE_ENTITIES):
        _poll(action_output, monkeypatch, additional_data=json.dumps(state))

    assert action_output.results.result_value is True
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("SUCCESS", "NONE", "COMPLETED", targets=1, failed=0, skipped=1),
    ]
