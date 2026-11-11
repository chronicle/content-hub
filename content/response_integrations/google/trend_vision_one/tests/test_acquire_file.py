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

"""Unit tests for the Acquire File action and its manager methods."""

from __future__ import annotations

import json
import pathlib
import traceback
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
import requests
import urllib3.exceptions
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import unix_now

from ..actions import AcquireFile
from ..core import TrendVisionOneManager as manager_module
from ..core.constants import REQUEST_TIMEOUT_SECONDS
from ..core.datamodels import Endpoint, Task
from ..core.TrendVisionOneExceptions import TrendVisionOneException
from ..core.TrendVisionOneManager import TrendVisionOneManager
from ..core.TrendVisionOneParser import TrendVisionOneParser
from ..core.UtilsManager import classify_exception
from .common import get_end_args, get_json_by_entity, get_summary_lines, make_entity, run_action
from .test_action_result_summary import make_http_error

API_ROOT = "https://api.xdr.trendmicro.com"
FILE_PATH = "C:\\Temp\\evil file.exe"
TASK_URL = f"{API_ROOT}/v3.0/response/tasks/"
SIGNED_URL = "https://storage.example.com/signed?X-Amz-Signature=secret"


def make_endpoint(guid: str) -> Endpoint:
    """Build an endpoint search result."""
    return TrendVisionOneParser.build_endpoint_obj({"agentGuid": guid, "endpointName": {"value": f"name-{guid}"}})


def make_task(task_id: str, status: str, **fields: object) -> Task:
    """Build a collect file task."""
    raw_data = {
        "id": task_id,
        "status": status,
        "agentGuid": f"guid-{task_id}",
        "endpointName": f"name-{task_id}",
        "filePath": FILE_PATH,
        "createdDateTime": "2026-11-10T10:00:00Z",
        "lastActionDateTime": "2026-11-10T10:05:00Z",
        **fields,
    }
    if status == "succeeded":
        raw_data.update(
            resourceLocation=f"{API_ROOT}/download/{task_id}",
            password="pass-" + task_id,
            fileSha1="sha1-" + task_id,
            fileSha256="sha256-" + task_id,
            fileSize=18,
        )

    return Task(raw_data=raw_data, status=status, id=task_id)


class FakeVisionOne:
    """Configure the mocked manager with endpoints and task statuses."""

    def __init__(self, tmp_path: pathlib.Path, endpoints: dict[str, str], statuses: dict[str, str]) -> None:
        """Init the fake."""
        self.tmp_path = tmp_path
        self.endpoints = endpoints
        self.statuses = statuses
        self.manager = MagicMock()

    def search_endpoint(
        self,
        ip: str | None = None,
        hostname: str | None = None,
        agent_id: str | None = None,
    ) -> Endpoint | None:
        """Return the endpoint of a search, or None."""
        guid = self.endpoints.get(ip or hostname or agent_id)

        return make_endpoint(guid) if guid else None

    def download(self, resource_location: str, destination: str, max_seconds: float) -> str:
        """Write a fake archive."""
        pathlib.Path(destination).write_bytes(b"archive")

        return destination

    def setup(self, manager: MagicMock) -> None:
        """Configure the mocked manager."""
        self.manager = manager
        manager.siemplify.run_folder = str(self.tmp_path)
        manager.search_endpoint.side_effect = self.search_endpoint
        manager.collect_file.side_effect = lambda guid, file_path, description: f"{TASK_URL}{guid}"
        manager.get_task.side_effect = lambda task_url: make_task(
            task_url.rsplit("/", 1)[-1],
            self.statuses[task_url.rsplit("/", 1)[-1]],
        )
        manager.download_collected_file.side_effect = self.download


def run_first(fake: FakeVisionOne, entities: list[MagicMock], agent_uuids: str = "") -> MagicMock:
    """Run the first run of the action."""
    params = {"File Path": FILE_PATH, "Agent UUID": agent_uuids}

    return run_action(AcquireFile, params, fake.setup, entities, main_args=(True,))


def run_poll(fake: FakeVisionOne, previous: MagicMock) -> MagicMock:
    """Run an async poll with the state that the previous run saved."""
    params = {"additional_data": get_end_args(previous)[1]}

    return run_action(AcquireFile, params, fake.setup, [make_entity("other", EntityTypes.HOSTNAME)], main_args=(False,))


@pytest.fixture
def host() -> MagicMock:
    """Build a hostname entity."""
    return make_entity("HOST1", EntityTypes.HOSTNAME)


def _make_connection_error() -> requests.ConnectionError:
    """Build a connection error with a urllib3 context."""
    error = requests.ConnectionError("reset")
    error.__context__ = urllib3.exceptions.ProtocolError("Connection aborted.")

    return error


class TestAcquireFileAction:
    """Tests for the Acquire File action flow."""

    def test_success_by_entity(self, tmp_path: pathlib.Path, host: MagicMock) -> None:
        """Verifies that a hostname is resolved, collected, downloaded, and attached in the first run."""
        fake = FakeVisionOne(tmp_path, {"HOST1": "g1"}, {"g1": "succeeded"})
        user = make_entity("bob", EntityTypes.USER)

        siemplify = run_first(fake, [host, user])

        message, result_value, status = get_end_args(siemplify)
        entry = get_json_by_entity(siemplify)["HOST1"]
        local_path = str(tmp_path / "g1_evil_file.exe.zip")
        assert (status, result_value) == (EXECUTION_STATE_COMPLETED, True)
        assert message == (
            'Successfully acquired the file "C:\\Temp\\evil file.exe" on the following entities using '
            "Trend Vision One: HOST1."
        )
        assert entry == {
            "status": "success",
            "action": "Acquire File",
            "agent_id": "g1",
            "endpoint_name": "name-g1",
            "file_path": local_path,
            "requested_file_path": FILE_PATH,
            "download_path": local_path,
            "zip_password": "pass-g1",
            "sha1": "sha1-g1",
            "sha256": "sha256-g1",
            "size": 18,
            "task_id": "g1",
            "created_at": "2026-11-10T10:00:00Z",
            "completed_at": "2026-11-10T10:05:00Z",
        }
        fake.manager.search_endpoint.assert_called_once_with(hostname="HOST1")
        fake.manager.collect_file.assert_called_once_with(
            guid="g1",
            file_path=FILE_PATH,
            description="Collect file from Google SecOps",
        )
        siemplify.result.add_attachment.assert_called_once()
        assert get_summary_lines(siemplify) == [
            {
                "outcome": "SUCCESS",
                "error_type": "NONE",
                "execution_state": "COMPLETED",
                "targets": "1",
                "failed": "0",
                "skipped": "1",
                "exc_type": "NONE",
                "http_status": "NONE",
            }
        ]

    def test_success_by_agent_uuid_and_ip(self, tmp_path: pathlib.Path) -> None:
        """Verifies that an IP address entity and an Agent UUID are both processed (conjunction)."""
        fake = FakeVisionOne(tmp_path, {"10.0.0.1": "g1", "uuid-2": "g2"}, {"g1": "succeeded", "g2": "succeeded"})

        siemplify = run_first(fake, [make_entity("10.0.0.1", EntityTypes.ADDRESS)], agent_uuids="uuid-2")

        assert get_end_args(siemplify)[1] is True
        assert {key: value["agent_id"] for key, value in get_json_by_entity(siemplify).items()} == {
            "10.0.0.1": "g1",
            "uuid-2": "g2",
        }
        fake.manager.search_endpoint.assert_any_call(ip="10.0.0.1")
        fake.manager.search_endpoint.assert_any_call(agent_id="uuid-2")

    def test_entity_and_uuid_of_same_agent_share_one_task(self, tmp_path: pathlib.Path, host: MagicMock) -> None:
        """Verifies that an entity and an Agent UUID with the same GUID start one task and both get a result."""
        fake = FakeVisionOne(tmp_path, {"HOST1": "g1", "g1": "g1"}, {"g1": "succeeded"})

        siemplify = run_first(fake, [host], agent_uuids="g1, g1")

        results = get_json_by_entity(siemplify)
        assert set(results) == {"HOST1", "g1"}
        assert results["HOST1"] == results["g1"]
        fake.manager.collect_file.assert_called_once()
        fake.manager.download_collected_file.assert_called_once()
        assert get_summary_lines(siemplify)[0]["targets"] == "2"

    def test_endpoint_not_found(self, tmp_path: pathlib.Path, host: MagicMock) -> None:
        """Verifies that an entity without an endpoint fails with ENDPOINT_NOT_FOUND and the playbook continues."""
        siemplify = run_first(FakeVisionOne(tmp_path, {}, {}), [host])

        message, result_value, status = get_end_args(siemplify)
        assert (status, result_value) == (EXECUTION_STATE_COMPLETED, False)
        assert message == (
            'Action wasn\'t able to acquire the file "C:\\Temp\\evil file.exe" on the following entities using '
            "Trend Vision One: HOST1."
        )
        assert get_json_by_entity(siemplify)["HOST1"] == {
            "status": "failure",
            "error": "Endpoint HOST1 was not found in Trend Vision One.",
            "error_type": "ENDPOINT_NOT_FOUND",
            "agent_id": None,
            "requested_file_path": FILE_PATH,
            "task_id": None,
        }
        summary = get_summary_lines(siemplify)[0]
        assert (summary["outcome"], summary["error_type"]) == ("FAILURE", "ENDPOINT_NOT_FOUND")

    def test_endpoint_search_error(self, tmp_path: pathlib.Path, host: MagicMock) -> None:
        """Verifies that a search error fails only its target and keeps the error text."""
        fake = FakeVisionOne(tmp_path, {"uuid-2": "g2"}, {"g2": "succeeded"})

        def setup(manager: MagicMock) -> None:
            fake.setup(manager)
            manager.search_endpoint.side_effect = lambda **kwargs: (
                fake.search_endpoint(**kwargs) if "agent_id" in kwargs else _raise(ConnectionError("refused"))
            )

        siemplify = run_action(
            AcquireFile,
            {"File Path": FILE_PATH, "Agent UUID": "uuid-2"},
            setup,
            [host],
            main_args=(True,),
        )

        results = get_json_by_entity(siemplify)
        assert results["HOST1"]["error"] == "refused"
        assert results["uuid-2"]["status"] == "success"
        assert get_summary_lines(siemplify)[0]["outcome"] == "PARTIAL_SUCCESS"

    @pytest.mark.parametrize("error_type", ["PERMISSION_DENIED", "ENDPOINT_NOT_FOUND", "INVALID_INPUT"])
    def test_collect_file_item_error(self, tmp_path: pathlib.Path, host: MagicMock, error_type: str) -> None:
        """Verifies that a failed collect file item fails its target with the error type of the manager."""
        fake = FakeVisionOne(tmp_path, {"HOST1": "g1"}, {})

        def setup(manager: MagicMock) -> None:
            fake.setup(manager)
            manager.collect_file.side_effect = TrendVisionOneException("rejected item", error_type=error_type)

        siemplify = run_action(AcquireFile, {"File Path": FILE_PATH}, setup, [host], main_args=(True,))

        assert get_end_args(siemplify)[1:] == (False, EXECUTION_STATE_COMPLETED)
        entry = get_json_by_entity(siemplify)["HOST1"]
        assert (entry["error"], entry["error_type"], entry["agent_id"]) == ("rejected item", error_type, "g1")
        assert get_summary_lines(siemplify)[0]["error_type"] == error_type

    @pytest.mark.parametrize(
        ("status", "error", "expected"),
        [
            ("failed", {"code": "TaskError", "message": "Agent error."}, "VENDOR_ERROR"),
            ("canceled", None, "CANCELLED"),
            ("rejected", None, "PERMISSION_DENIED"),
        ],
    )
    def test_task_ends_without_file(
        self,
        tmp_path: pathlib.Path,
        host: MagicMock,
        status: str,
        error: dict[str, str] | None,
        expected: str,
    ) -> None:
        """Verifies the error type of a task that ends with failed, canceled, or rejected."""
        fake = FakeVisionOne(tmp_path, {"HOST1": "g1"}, {"g1": status})

        def setup(manager: MagicMock) -> None:
            fake.setup(manager)
            manager.get_task.side_effect = lambda task_url: make_task("g1", status, error=error)

        siemplify = run_action(AcquireFile, {"File Path": FILE_PATH}, setup, [host], main_args=(True,))

        entry = get_json_by_entity(siemplify)["HOST1"]
        assert get_end_args(siemplify)[1:] == (False, EXECUTION_STATE_COMPLETED)
        assert (entry["error_type"], entry["task_id"]) == (expected, "g1")
        fake.manager.download_collected_file.assert_not_called()

    @pytest.mark.parametrize("status", ["queued", "running", "pendingApproval"])
    def test_pending_status_stays_in_progress(self, tmp_path: pathlib.Path, host: MagicMock, status: str) -> None:
        """Verifies that queued, running, and pendingApproval tasks keep the action in progress with no summary."""
        siemplify = run_first(FakeVisionOne(tmp_path, {"HOST1": "g1"}, {"g1": status}), [host])

        message, result_value, execution_state = get_end_args(siemplify)
        state = json.loads(result_value)
        assert execution_state == EXECUTION_STATE_INPROGRESS
        assert message == "Waiting for results for the following endpoints: HOST1"
        assert state["pending"] == {"g1": {"task_url": f"{TASK_URL}g1", "task_id": "g1", "keys": ["HOST1"]}}
        assert get_summary_lines(siemplify) == []
        siemplify.result.add_result_json.assert_not_called()

    def test_staggered_completion_keeps_state(self, tmp_path: pathlib.Path) -> None:
        """Verifies that results of earlier runs survive later polls (A on poll 1, B on poll 2, C not found)."""
        entities = [make_entity(name, EntityTypes.HOSTNAME) for name in ("A", "B", "C")]
        fake = FakeVisionOne(tmp_path, {"A": "ga", "B": "gb"}, {"ga": "queued", "gb": "queued"})

        first = run_first(fake, entities)
        fake.statuses = {"ga": "succeeded", "gb": "running"}
        poll_1 = run_poll(fake, first)
        fake.statuses = {"gb": "succeeded"}
        poll_2 = run_poll(fake, poll_1)

        assert get_end_args(first)[2] == get_end_args(poll_1)[2] == EXECUTION_STATE_INPROGRESS
        assert get_end_args(poll_1)[0] == "Waiting for results for the following endpoints: B"
        assert get_summary_lines(first) == get_summary_lines(poll_1) == []
        results = get_json_by_entity(poll_2)
        assert {key: value["status"] for key, value in results.items()} == {
            "A": "success",
            "B": "success",
            "C": "failure",
        }
        assert get_end_args(poll_2)[1:] == (True, EXECUTION_STATE_COMPLETED)
        assert "Action wasn't able to acquire" in get_end_args(poll_2)[0]
        summary = get_summary_lines(poll_2)[0]
        assert (summary["outcome"], summary["targets"], summary["failed"]) == ("PARTIAL_SUCCESS", "3", "1")

    def test_download_error_fails_target(self, tmp_path: pathlib.Path, host: MagicMock) -> None:
        """Verifies that a download error fails its target with the task ID."""
        fake = FakeVisionOne(tmp_path, {"HOST1": "g1"}, {"g1": "succeeded"})

        def setup(manager: MagicMock) -> None:
            fake.setup(manager)
            manager.download_collected_file.side_effect = TrendVisionOneException(
                "Failed to download the collected file. HTTP status: 403.",
                error_type="PERMISSION_DENIED",
            )

        siemplify = run_action(AcquireFile, {"File Path": FILE_PATH}, setup, [host], main_args=(True,))

        entry = get_json_by_entity(siemplify)["HOST1"]
        assert (entry["status"], entry["error_type"], entry["task_id"]) == ("failure", "PERMISSION_DENIED", "g1")
        assert get_end_args(siemplify)[1] is False

    def test_timeout_reports_unfinished_targets(self, tmp_path: pathlib.Path) -> None:
        """Verifies that a timeout fails the action and attaches JSON for finished and unfinished targets."""
        entities = [make_entity(name, EntityTypes.HOSTNAME) for name in ("A", "B")]
        fake = FakeVisionOne(tmp_path, {"A": "ga", "B": "gb"}, {"ga": "succeeded", "gb": "queued"})
        first = run_first(fake, entities)

        def setup(manager: MagicMock) -> None:
            fake.setup(manager)
            manager.siemplify.async_total_duration_deadline = unix_now() + 45_000

        poll = run_action(
            AcquireFile,
            {"additional_data": get_end_args(first)[1]},
            setup,
            [],
            main_args=(False,),
        )

        message, result_value, status = get_end_args(poll)
        results = get_json_by_entity(poll)
        assert (status, result_value) == (EXECUTION_STATE_FAILED, False)
        assert message == (
            'Error executing action "Acquire File". Reason: action ran into a timeout during execution. '
            "Pending endpoints: B. Please increase the timeout in IDE and try again."
        )
        assert results["A"]["status"] == "success"
        assert results["B"] == {
            "status": "failure",
            "error": "Action ran into a timeout during execution.",
            "error_type": "TIMEOUT",
            "agent_id": "gb",
            "requested_file_path": FILE_PATH,
            "task_id": "gb",
        }
        fake.manager.get_task.assert_called_once()
        summary = get_summary_lines(poll)[0]
        assert (summary["outcome"], summary["error_type"], summary["execution_state"]) == (
            "PARTIAL_SUCCESS",
            "TIMEOUT",
            "FAILED",
        )
        assert summary["exc_type"] == "TrendVisionOneTimeoutException"

    def test_run_deadline_keeps_tasks_pending(self, tmp_path: pathlib.Path) -> None:
        """Verifies that a run near its own deadline stops polling and saves the unchecked tasks for the next poll."""
        entities = [make_entity(name, EntityTypes.HOSTNAME) for name in ("A", "B")]
        fake = FakeVisionOne(tmp_path, {"A": "ga", "B": "gb"}, {"ga": "succeeded", "gb": "succeeded"})

        def setup(manager: MagicMock) -> None:
            fake.setup(manager)

            def get_task(task_url: str) -> Task:
                manager.siemplify.execution_deadline_unix_time_ms = unix_now()
                return make_task(task_url.rsplit("/", 1)[-1], "succeeded")

            manager.get_task.side_effect = get_task

        first = run_action(AcquireFile, {"File Path": FILE_PATH}, setup, entities, main_args=(True,))
        poll = run_poll(fake, first)

        message, result_value, status = get_end_args(first)
        assert (status, message) == (EXECUTION_STATE_INPROGRESS, "Waiting for results for the following endpoints: B")
        assert set(json.loads(result_value)["pending"]) == {"gb"}
        assert get_summary_lines(first) == []
        assert get_end_args(poll)[1:] == (True, EXECUTION_STATE_COMPLETED)
        statuses = {key: value["status"] for key, value in get_json_by_entity(poll).items()}
        assert statuses == {"A": "success", "B": "success"}

    @pytest.mark.parametrize(
        "error",
        [make_http_error(429), make_http_error(503), _make_connection_error(), requests.Timeout("slow")],
        ids=["rate_limited", "server_error", "connection_error", "timeout"],
    )
    def test_transient_poll_error_keeps_task_pending(
        self,
        tmp_path: pathlib.Path,
        host: MagicMock,
        error: Exception,
    ) -> None:
        """Verifies that a transient task status error keeps the target pending and the next poll finishes it."""
        fake = FakeVisionOne(tmp_path, {"HOST1": "g1"}, {"g1": "succeeded"})

        def setup(manager: MagicMock) -> None:
            fake.setup(manager)
            manager.get_task.side_effect = error

        first = run_action(AcquireFile, {"File Path": FILE_PATH}, setup, [host], main_args=(True,))
        poll = run_poll(fake, first)

        message, result_value, status = get_end_args(first)
        assert status == EXECUTION_STATE_INPROGRESS
        assert message == "Waiting for results for the following endpoints: HOST1"
        assert set(json.loads(result_value)["pending"]) == {"g1"}
        first.result.add_result_json.assert_not_called()
        assert get_json_by_entity(poll)["HOST1"]["status"] == "success"

    def test_transient_download_error_keeps_task_pending(self, tmp_path: pathlib.Path, host: MagicMock) -> None:
        """Verifies that a download connection error keeps the target pending instead of failing it."""
        fake = FakeVisionOne(tmp_path, {"HOST1": "g1"}, {"g1": "succeeded"})

        def setup(manager: MagicMock) -> None:
            fake.setup(manager)
            manager.download_collected_file.side_effect = TrendVisionOneException(
                "Failed to download the collected file: ConnectionError.",
                error_type="CONNECTION_ERROR",
            )

        siemplify = run_action(AcquireFile, {"File Path": FILE_PATH}, setup, [host], main_args=(True,))

        assert get_end_args(siemplify)[2] == EXECUTION_STATE_INPROGRESS
        assert set(json.loads(get_end_args(siemplify)[1])["pending"]) == {"g1"}

    def test_run_error_reports_every_target(self, tmp_path: pathlib.Path, host: MagicMock) -> None:
        """Verifies that a run error (bad credentials) fails the action with a JSON entry per target."""
        fake = FakeVisionOne(tmp_path, {}, {})

        def setup(manager: MagicMock) -> None:
            fake.setup(manager)
            manager.test_connectivity.side_effect = TrendVisionOneException(
                "Unauthorized",
                error_type="AUTHENTICATION_FAILED",
            )

        siemplify = run_action(
            AcquireFile,
            {"File Path": FILE_PATH, "Agent UUID": "uuid-2"},
            setup,
            [host],
            main_args=(True,),
        )

        assert get_end_args(siemplify) == (
            'Error executing action "Acquire File". Reason: Unauthorized',
            False,
            EXECUTION_STATE_FAILED,
        )
        assert {key: value["error_type"] for key, value in get_json_by_entity(siemplify).items()} == {
            "HOST1": "AUTHENTICATION_FAILED",
            "uuid-2": "AUTHENTICATION_FAILED",
        }
        assert get_summary_lines(siemplify)[0]["error_type"] == "AUTHENTICATION_FAILED"

    def test_get_task_error_fails_target(self, tmp_path: pathlib.Path, host: MagicMock) -> None:
        """Verifies that a task status error fails only its target."""
        fake = FakeVisionOne(tmp_path, {"HOST1": "g1"}, {})

        def setup(manager: MagicMock) -> None:
            fake.setup(manager)
            manager.get_task.side_effect = make_http_error(403)

        siemplify = run_action(AcquireFile, {"File Path": FILE_PATH}, setup, [host], main_args=(True,))

        entry = get_json_by_entity(siemplify)["HOST1"]
        assert (entry["error"], entry["error_type"]) == ("failed", "PERMISSION_DENIED")
        assert entry["task_id"] == "g1"

    def test_no_targets(self, tmp_path: pathlib.Path) -> None:
        """Verifies that a run with no supported entity and no Agent UUID returns false without an API call."""
        fake = FakeVisionOne(tmp_path, {}, {})
        siemplify = run_first(fake, [make_entity("bob", EntityTypes.USER)])

        fake.manager.test_connectivity.assert_not_called()
        assert get_end_args(siemplify) == (
            "No suitable entities or Agent UUIDs were found to acquire the file from.",
            False,
            EXECUTION_STATE_COMPLETED,
        )
        summary = get_summary_lines(siemplify)[0]
        assert (summary["targets"], summary["skipped"], summary["error_type"]) == ("0", "1", "INVALID_INPUT")

    def test_attachment_error_keeps_success(self, tmp_path: pathlib.Path, host: MagicMock) -> None:
        """Verifies that a failed case attachment is logged and the target still succeeds."""
        fake = FakeVisionOne(tmp_path, {"HOST1": "g1"}, {"g1": "succeeded"})

        def setup(manager: MagicMock) -> None:
            fake.setup(manager)
            manager.siemplify.result.add_attachment.side_effect = Exception("Attachment size exceeds the limit")

        siemplify = run_action(AcquireFile, {"File Path": FILE_PATH}, setup, [host], main_args=(True,))

        assert get_json_by_entity(siemplify)["HOST1"]["status"] == "success"
        siemplify.LOGGER.exception.assert_called_once_with("Unable to attach g1_evil_file.exe.zip to the case.")

    def test_unreadable_archive_on_attach_keeps_success(self, tmp_path: pathlib.Path, host: MagicMock) -> None:
        """Verifies that an archive that cannot be read for the attachment is logged and the target still succeeds."""
        fake = FakeVisionOne(tmp_path, {"HOST1": "g1"}, {"g1": "succeeded"})

        def setup(manager: MagicMock) -> None:
            fake.setup(manager)
            manager.download_collected_file.side_effect = lambda _location, destination, _seconds: destination

        siemplify = run_action(AcquireFile, {"File Path": FILE_PATH}, setup, [host], main_args=(True,))

        assert get_json_by_entity(siemplify)["HOST1"]["status"] == "success"
        siemplify.result.add_attachment.assert_not_called()
        siemplify.LOGGER.exception.assert_called_once_with("Unable to attach g1_evil_file.exe.zip to the case.")

    def test_large_archive_is_not_attached(
        self,
        tmp_path: pathlib.Path,
        host: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verifies that an archive over the size limit is downloaded but not attached."""
        monkeypatch.setattr(AcquireFile, "ACQUIRE_FILE_MAX_ATTACHMENT_BYTES", 1)

        siemplify = run_first(FakeVisionOne(tmp_path, {"HOST1": "g1"}, {"g1": "succeeded"}), [host])

        assert get_json_by_entity(siemplify)["HOST1"]["status"] == "success"
        siemplify.result.add_attachment.assert_not_called()

    def test_run_folder_fallback(
        self,
        tmp_path: pathlib.Path,
        host: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verifies that the archive goes to ./downloads if the run folder is not available."""
        monkeypatch.chdir(tmp_path)
        fake = FakeVisionOne(tmp_path, {"HOST1": "g1"}, {"g1": "succeeded"})

        def setup(manager: MagicMock) -> None:
            fake.setup(manager)
            type(manager.siemplify).run_folder = PropertyMock(side_effect=PermissionError("/opt/siemplify"))

        siemplify = run_action(AcquireFile, {"File Path": FILE_PATH}, setup, [host], main_args=(True,))

        expected_destination = str(tmp_path / "downloads" / "g1_evil_file.exe.zip")
        assert get_json_by_entity(siemplify)["HOST1"]["download_path"] == expected_destination

    def test_build_file_name_is_safe(self) -> None:
        """Verifies that the local file name has no path separators or unsafe characters."""
        assert AcquireFile.build_file_name("RM-1", "/var/../a b;c.sh") == "RM-1_a_b_c.sh.zip"
        assert AcquireFile.build_file_name("RM-2", "C:\\dir\\") == "RM-2_collected_file.zip"

    def test_download_timeout_fails_after_limit(self, tmp_path: pathlib.Path) -> None:
        """Verifies that a download timeout fails a target after 3 attempts and lets other targets finish."""
        fake = FakeVisionOne(tmp_path, {"A": "ga", "B": "gb"}, {"ga": "queued", "gb": "queued"})
        first = run_first(fake, [make_entity("A", EntityTypes.HOSTNAME), make_entity("B", EntityTypes.HOSTNAME)])
        fake.statuses = {"ga": "succeeded", "gb": "succeeded"}

        def setup(manager: MagicMock) -> None:
            fake.setup(manager)
            original_download = manager.download_collected_file.side_effect

            def download(resource_location: str, destination: str, max_seconds: float) -> str:
                if "ga" in resource_location:
                    manager.siemplify.execution_deadline_unix_time_ms = unix_now()
                    timeout_error = "download timeout"
                    raise TrendVisionOneException(timeout_error, error_type="TIMEOUT")
                return original_download(resource_location, destination, max_seconds)

            manager.download_collected_file.side_effect = download

        poll_1 = run_action(AcquireFile, {"additional_data": get_end_args(first)[1]}, setup, [], main_args=(False,))
        assert get_end_args(poll_1)[2] == EXECUTION_STATE_INPROGRESS

        poll_2 = run_action(AcquireFile, {"additional_data": get_end_args(poll_1)[1]}, setup, [], main_args=(False,))
        assert get_end_args(poll_2)[2] == EXECUTION_STATE_INPROGRESS
        state_2 = json.loads(get_end_args(poll_2)[1])
        assert state_2["pending"]["ga"]["download_timeouts"] == 2
        assert list(state_2["pending"]) == ["ga", "gb"]

        poll_3 = run_action(AcquireFile, {"additional_data": get_end_args(poll_2)[1]}, setup, [], main_args=(False,))
        assert get_end_args(poll_3)[2] == EXECUTION_STATE_INPROGRESS
        state_3 = json.loads(get_end_args(poll_3)[1])
        assert list(state_3["pending"]) == ["gb"]

        poll_4 = run_action(AcquireFile, {"additional_data": get_end_args(poll_3)[1]}, setup, [], main_args=(False,))
        _, result_value, status = get_end_args(poll_4)
        assert (status, result_value) == (EXECUTION_STATE_COMPLETED, True)
        results = get_json_by_entity(poll_4)
        assert results["B"]["status"] == "success"
        assert results["A"] == {
            "status": "failure",
            "error": "The archive did not download in the script timeout. Increase the script timeout in the IDE.",
            "error_type": "TIMEOUT",
            "agent_id": "ga",
            "requested_file_path": FILE_PATH,
            "task_id": "ga",
        }

    def test_final_timeout_run_checks_tasks_and_succeeds(self, tmp_path: pathlib.Path) -> None:
        """Verifies that the final timeout run still checks pending tasks and finishes succeeded tasks."""
        fake = FakeVisionOne(tmp_path, {"A": "ga"}, {"ga": "queued"})
        first = run_first(fake, [make_entity("A", EntityTypes.HOSTNAME)])
        fake.statuses = {"ga": "succeeded"}

        def setup(manager: MagicMock) -> None:
            fake.setup(manager)
            manager.siemplify.async_total_duration_deadline = unix_now() + 45_000
            manager.siemplify.async_polling_interval_in_sec = 60

        poll = run_action(AcquireFile, {"additional_data": get_end_args(first)[1]}, setup, [], main_args=(False,))

        _, result_value, status = get_end_args(poll)
        assert (status, result_value) == (EXECUTION_STATE_COMPLETED, True)
        fake.manager.get_task.assert_called_once()
        assert get_json_by_entity(poll)["A"]["status"] == "success"

    def test_zip_password_not_in_logs(self, tmp_path: pathlib.Path) -> None:
        """Verifies that the zip archive password is saved in state but never logged."""
        fake = FakeVisionOne(tmp_path, {"A": "ga", "B": "gb"}, {"ga": "succeeded", "gb": "queued"})
        first = run_first(fake, [make_entity("A", EntityTypes.HOSTNAME), make_entity("B", EntityTypes.HOSTNAME)])
        assert "pass-ga" in get_end_args(first)[1]
        logged = " ".join(str(call) for call in first.LOGGER.mock_calls)
        assert "pass-ga" not in logged

    def test_non_transient_poll_error_fails_one_target(self, tmp_path: pathlib.Path) -> None:
        """Verifies that a non-transient error on one target fails that target while the other finishes."""
        fake = FakeVisionOne(tmp_path, {"A": "ga", "B": "gb"}, {"ga": "queued", "gb": "queued"})
        first = run_first(fake, [make_entity("A", EntityTypes.HOSTNAME), make_entity("B", EntityTypes.HOSTNAME)])
        fake.statuses = {"gb": "succeeded"}

        def setup(manager: MagicMock) -> None:
            fake.setup(manager)

            def get_task(task_url: str) -> Task:
                if "ga" in task_url:
                    raise make_http_error(403)
                return make_task("gb", "succeeded")

            manager.get_task.side_effect = get_task

        poll = run_action(AcquireFile, {"additional_data": get_end_args(first)[1]}, setup, [], main_args=(False,))

        _, result_value, status = get_end_args(poll)
        assert (status, result_value) == (EXECUTION_STATE_COMPLETED, True)
        results = get_json_by_entity(poll)
        assert results["A"]["status"] == "failure"
        assert results["A"]["error_type"] == "PERMISSION_DENIED"
        assert results["B"]["status"] == "success"

    def test_poll_config_error_preserves_finished_results(self, tmp_path: pathlib.Path) -> None:
        """Verifies that a config extraction error on a poll preserves finished results in the JSON result."""
        fake = FakeVisionOne(tmp_path, {"A": "ga", "B": "gb"}, {"ga": "succeeded", "gb": "queued"})
        first = run_first(fake, [make_entity("A", EntityTypes.HOSTNAME), make_entity("B", EntityTypes.HOSTNAME)])

        with patch.object(AcquireFile, "build_manager", side_effect=Exception("Missing mandatory parameter API Token")):
            poll = run_action(
                AcquireFile, {"additional_data": get_end_args(first)[1]}, fake.setup, [], main_args=(False,)
            )

        assert get_end_args(poll)[2] == EXECUTION_STATE_FAILED
        results = get_json_by_entity(poll)
        assert results["A"]["status"] == "success"
        assert results["B"]["status"] == "failure"

    def test_poll_with_none_polling_interval_stays_in_progress(self, tmp_path: pathlib.Path) -> None:
        """Verifies that a poll with null polling interval and future deadline ends IN_PROGRESS."""
        fake = FakeVisionOne(tmp_path, {"A": "ga"}, {"ga": "queued"})
        first = run_first(fake, [make_entity("A", EntityTypes.HOSTNAME)])

        def setup(manager: MagicMock) -> None:
            fake.setup(manager)
            manager.siemplify.async_polling_interval_in_sec = None
            manager.siemplify.async_total_duration_deadline = unix_now() + 3_600_000

        poll = run_action(AcquireFile, {"additional_data": get_end_args(first)[1]}, setup, [], main_args=(False,))
        assert get_end_args(poll)[2] == EXECUTION_STATE_INPROGRESS


def _raise(error: Exception) -> None:
    """Raise an error from a lambda."""
    raise error


def _chunks_then_raise(chunk: bytes, message: str) -> object:
    """Yield one chunk, then fail like a dropped connection."""
    yield chunk
    raise requests.exceptions.ChunkedEncodingError(message)


def make_manager() -> TrendVisionOneManager:
    """Build a manager with a mocked session."""
    manager = TrendVisionOneManager(API_ROOT, "token", verify_ssl=True, siemplify=MagicMock())
    manager.session = MagicMock()

    return manager


def make_download_response(status_code: int, chunks: tuple[bytes, ...] = (b"arch", b"ive")) -> MagicMock:
    """Build a streamed download response."""
    response = MagicMock(status_code=status_code, ok=status_code < 400)
    response.iter_content.return_value = iter(chunks)

    return response


class TestCollectFile:
    """Tests for TrendVisionOneManager.collect_file."""

    def test_accepted_item_returns_task_url(self) -> None:
        """Verifies that a 202 item returns the Operation-Location URL and the body is a JSON array."""
        manager = make_manager()
        location = f"{TASK_URL}00000001"
        manager.session.post.return_value.json.return_value = [
            {"status": 202, "headers": [{"name": "Operation-Location", "value": location}]}
        ]

        assert manager.collect_file("g1", FILE_PATH, "reason") == location
        manager.session.post.assert_called_once_with(
            f"{API_ROOT}/v3.0/response/endpoints/collectFile",
            json=[{"agentGuid": "g1", "filePath": FILE_PATH, "description": "reason"}],
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

    @pytest.mark.parametrize(
        ("status", "code", "message", "expected"),
        [
            (400, "BadRequest", "Target not found.", "ENDPOINT_NOT_FOUND"),
            (400, "NotSupported", "Action not supported.", "UNSUPPORTED_ENDPOINT"),
            (400, "BadRequest", "Invalid request - Invalid field format: filePath.", "INVALID_INPUT"),
            (403, "AccessDenied", "Insufficient permissions.", "PERMISSION_DENIED"),
            (404, "NotFound", "Not found.", "ENDPOINT_NOT_FOUND"),
            (500, "InternalServerError", "Internal server error.", "VENDOR_ERROR"),
        ],
    )
    def test_failed_item_raises_with_error_type(self, status: int, code: str, message: str, expected: str) -> None:
        """Verifies that a non-2xx item of the 207 response raises with its message and error type."""
        manager = make_manager()
        manager.session.post.return_value.json.return_value = [
            {"status": status, "body": {"error": {"code": code, "message": message}}}
        ]

        with pytest.raises(TrendVisionOneException, match=message) as error:
            manager.collect_file("g1", FILE_PATH, "reason")

        assert error.value.error_type == expected

    def test_duplicate_task_returns_existing_task_url(self) -> None:
        """Verifies that a 400 TaskError item with an Operation-Location returns the URL of the existing task."""
        manager = make_manager()
        location = f"{TASK_URL}00000001"
        manager.session.post.return_value.json.return_value = [
            {
                "status": 400,
                "headers": [{"name": "Operation-Location", "value": location}],
                "body": {"error": {"code": "TaskError", "message": "Task duplication."}},
            }
        ]

        assert manager.collect_file("g1", FILE_PATH, "reason") == location
        manager.siemplify.LOGGER.info.assert_called_once()

    def test_item_without_location_raises(self) -> None:
        """Verifies that a 2xx item with no Operation-Location raises VENDOR_ERROR."""
        manager = make_manager()
        manager.session.post.return_value.json.return_value = [{"status": 202, "headers": []}]

        with pytest.raises(TrendVisionOneException) as error:
            manager.collect_file("g1", FILE_PATH, "reason")

        assert error.value.error_type == "VENDOR_ERROR"


class TestDownloadCollectedFile:
    """Tests for TrendVisionOneManager.download_collected_file."""

    def test_api_host_uses_bearer_session(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifies that a location on the API host is downloaded with the bearer session only."""
        manager = make_manager()
        manager.session.get.return_value = make_download_response(200)
        plain_get = MagicMock()
        monkeypatch.setattr(requests, "get", plain_get)
        destination = str(tmp_path / "a.zip")

        assert manager.download_collected_file(f"{API_ROOT}/files/1", destination) == destination
        assert pathlib.Path(destination).read_bytes() == b"archive"
        plain_get.assert_not_called()

    @pytest.mark.parametrize("status_code", [401, 403])
    def test_auth_rejection_retries_without_token(
        self,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        status_code: int,
    ) -> None:
        """Verifies that a 401 or 403 with the bearer token retries once with no Authorization header."""
        manager = make_manager()
        manager.session.get.return_value = make_download_response(status_code)
        plain_get = MagicMock(return_value=make_download_response(200))
        monkeypatch.setattr(requests, "get", plain_get)

        manager.download_collected_file(f"{API_ROOT}/files/1", str(tmp_path / "a.zip"))

        manager.session.get.return_value.close.assert_called_once()
        plain_get.assert_called_once_with(f"{API_ROOT}/files/1", stream=True, verify=True, timeout=60)

    def test_other_host_never_gets_token(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifies that a location on another host is downloaded without the bearer session."""
        manager = make_manager()
        plain_get = MagicMock(return_value=make_download_response(200))
        monkeypatch.setattr(requests, "get", plain_get)

        manager.download_collected_file("https://storage.example.com/signed?sig=secret", str(tmp_path / "a.zip"))

        manager.session.get.assert_not_called()
        plain_get.assert_called_once()

    def test_failed_download_hides_url(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifies that a failed download raises with the HTTP status, no URL, and the HTTP error type."""
        manager = make_manager()
        monkeypatch.setattr(requests, "get", MagicMock(return_value=make_download_response(403)))

        with pytest.raises(TrendVisionOneException) as error:
            manager.download_collected_file("https://storage.example.com/signed?sig=secret", str(tmp_path / "a.zip"))

        assert str(error.value) == "Failed to download the collected file. HTTP status: 403."
        assert "secret" not in str(error.value.__cause__)
        assert classify_exception(error.value) == ("PERMISSION_DENIED", "TrendVisionOneException", 403)

    def test_http_location_never_gets_token(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifies that a plain HTTP location on the API host is downloaded without the bearer session."""
        manager = make_manager()
        plain_get = MagicMock(return_value=make_download_response(200))
        monkeypatch.setattr(requests, "get", plain_get)

        manager.download_collected_file("http://api.xdr.trendmicro.com/files/1", str(tmp_path / "a.zip"))

        manager.session.get.assert_not_called()
        plain_get.assert_called_once()

    @pytest.mark.parametrize(
        ("error", "error_type"),
        [
            (requests.ConnectionError(SIGNED_URL), "CONNECTION_ERROR"),
            (requests.exceptions.InvalidURL(SIGNED_URL), "VENDOR_ERROR"),
        ],
    )
    def test_request_error_hides_url(
        self,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        error: requests.RequestException,
        error_type: str,
    ) -> None:
        """Verifies that a requests error is replaced by an error with no URL in its text or traceback."""
        manager = make_manager()
        monkeypatch.setattr(requests, "get", MagicMock(side_effect=error))

        with pytest.raises(TrendVisionOneException) as raised:
            manager.download_collected_file(SIGNED_URL, str(tmp_path / "a.zip"))

        assert str(raised.value) == f"Failed to download the collected file: {type(error).__name__}."
        assert raised.value.error_type == error_type
        assert "secret" not in "".join(traceback.format_exception(raised.value))

    def test_stream_error_removes_partial_file(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifies that a connection drop during the stream removes the partial archive and is a connection error."""
        manager = make_manager()
        response = make_download_response(200)
        response.iter_content.side_effect = lambda chunk_size: _chunks_then_raise(b"arch", "drop")
        monkeypatch.setattr(requests, "get", MagicMock(return_value=response))
        destination = tmp_path / "a.zip"

        with pytest.raises(TrendVisionOneException) as raised:
            manager.download_collected_file("https://storage.example.com/signed", str(destination))

        assert raised.value.error_type == "CONNECTION_ERROR"
        assert not destination.exists()

    def test_time_limit_stops_download(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifies that a download past its time limit raises TIMEOUT and removes the partial archive."""
        manager = make_manager()
        monkeypatch.setattr(requests, "get", MagicMock(return_value=make_download_response(200)))
        monkeypatch.setattr(manager_module.time, "monotonic", MagicMock(side_effect=[0, 5, 11]))
        destination = tmp_path / "a.zip"

        with pytest.raises(TrendVisionOneException) as raised:
            manager.download_collected_file("https://storage.example.com/signed", str(destination), max_seconds=10)

        assert raised.value.error_type == "TIMEOUT"
        assert not destination.exists()

    def test_missing_location_raises(self, tmp_path: pathlib.Path) -> None:
        """Verifies that a task result with no resource location raises VENDOR_ERROR."""
        with pytest.raises(TrendVisionOneException) as error:
            make_manager().download_collected_file("", str(tmp_path / "a.zip"))

        assert error.value.error_type == "VENDOR_ERROR"


class TestSearchEndpoint:
    """Tests for TrendVisionOneManager.search_endpoint."""

    def test_query_header_does_not_leak_to_later_requests(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifies that TMV1-Query is sent on the search request only, not on later session requests."""
        manager = TrendVisionOneManager(API_ROOT, "token", verify_ssl=True, siemplify=MagicMock())
        sent: list[requests.PreparedRequest] = []
        response = MagicMock()
        response.json.return_value = {"items": []}

        def fake_send(request: requests.PreparedRequest, **_: object) -> MagicMock:
            sent.append(request)

            return response

        monkeypatch.setattr(manager.session, "send", fake_send)

        manager.search_endpoint(agent_id="g1")
        manager.get_endpoint_isolation_status("g1")

        assert sent[0].headers["TMV1-Query"] == "agentGuid eq 'g1'"
        assert "TMV1-Query" not in sent[1].headers
        assert sent[1].headers["Authorization"] == "Bearer token"
