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

import gzip
import hashlib
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from integration_testing.logger import Logger
from integration_testing.requests.response import MockResponse
from soar_sdk.SiemplifyDataModel import EntityTypes

from microsoft_defender_atp.core.datamodels import Machine
from microsoft_defender_atp.core.exceptions import (
    DefenderActiveRequestExistsException,
    DefenderException,
    DefenderNotFoundException,
)
from microsoft_defender_atp.core.MicrosoftDefenderATPManager import MicrosoftDefenderATPManager, normalize_machine_id
from microsoft_defender_atp.core.UtilsManager import hash_acquired_file, normalize_mde_file_path
from microsoft_defender_atp.tests import common
from microsoft_defender_atp.tests.core.product import DEFAULT_ACQUIRED_CONTENT

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

    from microsoft_defender_atp.tests.core.product import MicrosoftDefenderATP

MACHINE: SingleJson = common.MOCK_DATA["machine_data"]
MACHINE_ID: str = MACHINE["id"]


@pytest.fixture(name="product")
def product_fixture(microsoft_defender_atp: MicrosoftDefenderATP) -> MicrosoftDefenderATP:
    """Return the mock product seeded with the two mock machines."""
    microsoft_defender_atp.add_machine(dict(MACHINE))
    microsoft_defender_atp.add_machine(dict(common.MOCK_DATA["machine_data_ip"]))

    return microsoft_defender_atp


@pytest.fixture(name="logger")
def logger_fixture() -> Logger:
    """Return a mock SOAR logger."""
    return Logger()


@pytest.fixture(name="api")
def api_fixture(product: MicrosoftDefenderATP, logger: Logger) -> MicrosoftDefenderATPManager:
    """Return a manager wired to the mock session (patched by conftest)."""
    del product

    return MicrosoftDefenderATPManager(
        client_id=common.CONFIG["Client ID"],
        client_secret=common.CONFIG["Client Secret"],
        tenant_id=common.CONFIG["Azure Active Directory ID"],
        resource=common.CONFIG["Api Root"],
        login_api_root=common.CONFIG["Login API Root"],
        siemplify=SimpleNamespace(LOGGER=logger),
    )


# --------------------------------------------------------------------------- #
# UtilsManager
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "raw",
    [
        MACHINE_ID,
        f"  {MACHINE_ID} ",
        f"DeviceId:{MACHINE_ID}",
        f"DeviceID: {MACHINE_ID}",
        f"Device ID: {MACHINE_ID}",
        f"MICROSOFT_GRAPH_ALERT: {MACHINE_ID}",
        f"MICROSOFT_GRAPH_ALERT: DeviceId: {MACHINE_ID}",
    ],
)
def test_normalize_machine_id(raw: str) -> None:
    """Known alert prefixes and whitespace are stripped."""
    assert normalize_machine_id(raw) == MACHINE_ID


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("C:\\Windows\\win.ini", "C:\\Windows\\win.ini"),
        ("%SystemRoot%\\win.ini", "C:\\Windows\\win.ini"),
        ("%SYSTEMROOT%\\\\System32\\\\drivers", "C:\\Windows\\System32\\drivers"),
        ("  D:\\\\a\\\\\\b.txt ", "D:\\a\\b.txt"),
        ("\\\\server\\\\share\\f.txt", "\\\\server\\share\\f.txt"),
        ("\\\\\\server\\share", "\\\\server\\share"),
        (" /etc/hostname ", "/etc/hostname"),
    ],
)
def test_normalize_mde_file_path(raw: str, expected: str) -> None:
    """%systemroot% expands and backslashes collapse, keeping the UNC prefix."""
    assert normalize_mde_file_path(raw) == expected


@pytest.mark.parametrize("raw", ["relative\\path.txt", "", "\\\\", "C:/Windows/win.ini", "//etc/hostname"])
def test_normalize_mde_file_path_rejects_non_absolute(raw: str) -> None:
    """Non-absolute paths raise ValueError."""
    with pytest.raises(ValueError):
        normalize_mde_file_path(raw)


def test_hash_acquired_file_gzip_hashes_decompressed_bytes() -> None:
    """Gzip payloads are hashed after decompression."""
    result = hash_acquired_file(gzip.compress(DEFAULT_ACQUIRED_CONTENT))

    assert result == {
        "md5": hashlib.md5(DEFAULT_ACQUIRED_CONTENT).hexdigest(),
        "sha1": hashlib.sha1(DEFAULT_ACQUIRED_CONTENT).hexdigest(),
        "sha256": hashlib.sha256(DEFAULT_ACQUIRED_CONTENT).hexdigest(),
        "size": len(DEFAULT_ACQUIRED_CONTENT),
        "is_gzip": True,
    }


def test_hash_acquired_file_plain_bytes() -> None:
    """Non-gzip payloads are hashed as-is."""
    result = hash_acquired_file(b"plain")

    assert result["is_gzip"] is False
    assert result["sha256"] == hashlib.sha256(b"plain").hexdigest()
    assert result["size"] == 5


@pytest.mark.parametrize("raw", [b"\x1f\x8bnot-gzip", gzip.compress(DEFAULT_ACQUIRED_CONTENT)[:-8]])
def test_hash_acquired_file_fails_closed_on_corrupt_gzip(raw: bytes) -> None:
    """Corrupt or truncated gzip payloads raise DefenderException."""
    with pytest.raises(DefenderException):
        hash_acquired_file(raw)


# --------------------------------------------------------------------------- #
# Machine datamodel
# --------------------------------------------------------------------------- #


def test_machine_output_unchanged_without_isolation_status() -> None:
    """Isolation keys are absent unless isolation_status is set."""
    machine = Machine(raw_data=MACHINE, **MACHINE)

    assert "isolation_status" not in machine.to_json()
    assert "isolation_status" not in machine.to_enrichment_data()
    assert "Isolation Status" not in machine.to_table()


def test_machine_output_with_isolation_status() -> None:
    """Isolation keys are emitted in JSON, enrichment and table once set."""
    machine = Machine(raw_data=MACHINE, **MACHINE)
    machine.isolation_status, machine.is_isolated = "contained", True

    assert machine.to_json()["isolation_status"] == "contained"
    assert machine.to_enrichment_data()["is_isolated"] is True
    assert machine.to_table()["Isolation Status"] == "contained"
    assert machine.to_table()["Is Isolated"] is True


# --------------------------------------------------------------------------- #
# Manager: machine lookup
# --------------------------------------------------------------------------- #


def test_get_machine_by_id_strips_prefix(api: MicrosoftDefenderATPManager) -> None:
    """A prefixed, upper-cased ID resolves to the machine."""
    machine = api.get_machine_by_id(f"DeviceId: {MACHINE_ID.upper()}")

    assert machine.id == MACHINE_ID


@pytest.mark.parametrize("machine_id", ["0" * 40, MACHINE["computerDnsName"], "  "])
def test_get_machine_by_id_not_found(api: MicrosoftDefenderATPManager, machine_id: str) -> None:
    """Unknown IDs (404), hostnames (identity guardrail) and blanks are not found."""
    with pytest.raises(DefenderNotFoundException):
        api.get_machine_by_id(machine_id)


@pytest.mark.parametrize(
    ("identifier", "entity_type"),
    [(MACHINE["computerDnsName"], EntityTypes.HOSTNAME), (MACHINE["lastIpAddress"], EntityTypes.ADDRESS)],
)
def test_find_machine_for_entity(api: MicrosoftDefenderATPManager, identifier: str, entity_type: str) -> None:
    """HOSTNAME and ADDRESS entities resolve to their machine."""
    assert api.find_machine_for_entity(identifier, entity_type).id == MACHINE_ID


@pytest.mark.parametrize(
    ("identifier", "entity_type"),
    [
        ("not.found.com", EntityTypes.HOSTNAME),
        ("10.9.9.9", EntityTypes.ADDRESS),
        (MACHINE["computerDnsName"], EntityTypes.USER),
    ],
)
def test_find_machine_for_entity_not_found(api: MicrosoftDefenderATPManager, identifier: str, entity_type: str) -> None:
    """Unmatched or unsupported entities raise DefenderNotFoundException."""
    with pytest.raises(DefenderNotFoundException):
        api.find_machine_for_entity(identifier, entity_type)


# --------------------------------------------------------------------------- #
# Manager: containment
# --------------------------------------------------------------------------- #


def test_isolate_and_unisolate_active_request_exists(
    api: MicrosoftDefenderATPManager,
    product: MicrosoftDefenderATP,
) -> None:
    """A 400 ActiveRequestAlreadyExists raises the dedicated exception."""
    product.set_active_request_exists(MACHINE_ID, "Isolate")
    product.set_active_request_exists(MACHINE_ID, "Unisolate")

    with pytest.raises(DefenderActiveRequestExistsException):
        api.isolate_machine(MACHINE_ID, "Full", "test")
    with pytest.raises(DefenderActiveRequestExistsException):
        api.unisolate_machine(MACHINE_ID, "test")


@pytest.mark.parametrize(
    ("error", "raises"),
    [
        ({"code": "ActiveRequestAlreadyExists", "message": "Action is already in progress"}, True),
        (
            {
                "code": "BadRequest",
                "message": "Cannot isolate device because Isolate action: "
                "5c14d46c-8d22-4b84-b48b-43f79a04912f is still active.",
            },
            True,
        ),
        ({"code": "BadRequest", "message": "Invalid isolation type"}, False),
    ],
)
def test_raise_if_active_request_exists_matches_code_or_live_message(error: dict[str, str], raises: bool) -> None:
    """Both the documented code and MDE's live "is still active" message count."""
    response = MockResponse(content={"error": error}, status_code=400)

    if raises:
        with pytest.raises(DefenderActiveRequestExistsException):
            MicrosoftDefenderATPManager._raise_if_active_request_exists(response)
    else:
        MicrosoftDefenderATPManager._raise_if_active_request_exists(response)


def test_isolate_machine_still_returns_task(api: MicrosoftDefenderATPManager) -> None:
    """Without a conflict, isolate returns the created task as before."""
    task = api.isolate_machine(MACHINE_ID, "Full", "test")

    assert (task.type, task.status) == ("Isolate", "Pending")


def test_get_machine_containment_tasks_sorted_and_filtered(
    api: MicrosoftDefenderATPManager,
    product: MicrosoftDefenderATP,
) -> None:
    """Only this machine's Isolate/Unisolate tasks are returned, newest first."""
    product.create_task("Isolate", MACHINE_ID, "Succeeded", creation_time="2024-01-01T01:00:00Z")
    product.create_task("Unisolate", MACHINE_ID, "Failed", creation_time="2024-01-03T01:00:00Z")
    product.create_task("RunAntiVirusScan", MACHINE_ID, creation_time="2024-01-04T01:00:00Z")
    product.create_task("Isolate", "other-machine", creation_time="2024-01-05T01:00:00Z")

    tasks = api.get_machine_containment_tasks(MACHINE_ID)

    assert [(task.type, task.status) for task in tasks] == [("Unisolate", "Failed"), ("Isolate", "Succeeded")]


@pytest.mark.parametrize(
    ("history", "expected"),
    [
        ([], ("uncontained", False)),
        ([("Isolate", "Succeeded")], ("contained", True)),
        ([("Isolate", "Pending")], ("containment_requested", False)),
        ([("Isolate", "Succeeded"), ("Isolate", "Failed")], ("contain_failed", True)),
        ([("Isolate", "TimeOut")], ("contain_failed", False)),
        ([("Isolate", "Succeeded"), ("Isolate", "Cancelled")], ("contained", True)),
        ([("Isolate", "Succeeded"), ("Unisolate", "Succeeded")], ("uncontained", False)),
        ([("Isolate", "Succeeded"), ("Unisolate", "InProgress")], ("uncontainment_requested", True)),
        ([("Isolate", "Succeeded"), ("Unisolate", "TimeOut")], ("uncontain_failed", True)),
        ([("Unisolate", "Cancelled")], ("uncontained", False)),
    ],
)
def test_get_machine_isolation_status(
    api: MicrosoftDefenderATPManager,
    product: MicrosoftDefenderATP,
    history: list[tuple[str, str]],
    expected: tuple[str, bool],
) -> None:
    """Status follows the newest task; is_isolated follows the newest success."""
    for day, (task_type, status) in enumerate(history, start=1):
        product.create_task(task_type, MACHINE_ID, status, creation_time=f"2024-01-0{day}T00:00:00Z")

    assert api.get_machine_isolation_status(MACHINE_ID) == expected


def test_get_machine_isolation_status_fails_soft(
    api: MicrosoftDefenderATPManager,
    product: MicrosoftDefenderATP,
    logger: Logger,
) -> None:
    """A machineactions error yields ("unknown", None) and a warning."""
    product.set_containment_tasks_error()

    assert api.get_machine_isolation_status(MACHINE_ID) == ("unknown", None)
    assert any("isolation status" in row for row in logger.log_rows)


# --------------------------------------------------------------------------- #
# Test infrastructure: live response outcome and result download
# --------------------------------------------------------------------------- #


def test_live_response_pending_by_default_then_downloadable(
    api: MicrosoftDefenderATPManager,
    product: MicrosoftDefenderATP,
) -> None:
    """Status stays Pending until opted in; the result downloads as gzip bytes."""
    command = {"type": "GetFile", "params": [{"key": "Path", "value": "C:\\a.txt"}]}
    action_id = api.run_live_response_command(MACHINE_ID, [command], "test")["id"]
    assert api.get_live_response_status(action_id)["status"] == "Pending"

    product.set_live_response_final_status("Succeeded")
    status = api.get_live_response_status(action_id)
    link = api.get_live_response_result_download_link(action_id)["value"]

    assert status["commands"][0]["commandStatus"] == "Completed"
    assert gzip.decompress(api.get_live_response_result(link)) == DEFAULT_ACQUIRED_CONTENT


def test_live_response_failed_reports_command_errors(
    api: MicrosoftDefenderATPManager,
    product: MicrosoftDefenderATP,
) -> None:
    """A Failed outcome exposes the command errors like MDE."""
    command = {"type": "GetFile", "params": [{"key": "Path", "value": "C:\\a.txt"}]}
    action_id = api.run_live_response_command(MACHINE_ID, [command], "test")["id"]
    product.set_live_response_final_status("Failed", errors=["File not found"])

    status = api.get_live_response_status(action_id)

    assert status["status"] == "Failed"
    assert status["commands"][0]["errors"] == ["File not found"]
