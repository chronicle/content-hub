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

import base64
import sys
from pathlib import Path
from typing import Any

import pytest
import soar_sdk

if soar_sdk.__path__[0] not in sys.path:
    sys.path.insert(0, soar_sdk.__path__[0])

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED, ScriptResult
from soar_sdk.SiemplifyDataModel import EntityTypes

from ..actions import DetonateFile, GetFile, GetPcap, GetReport, Ping
from ..core.WildfireManager import WildfireManagerError, WildfireNotFoundError

SAMPLE_MD5 = "44d88612fea8a8f36de82e1278abb02f"
SAMPLE_MD5_OTHER = "098f6bcd4621d373cade4e832627b4f6"
SAMPLE_SHA256 = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"


class MockEntity:
    def __init__(self, identifier: str, entity_type: int = EntityTypes.FILEHASH) -> None:
        self.identifier = identifier
        self.entity_type = entity_type
        self.additional_properties: dict[str, Any] = {}
        self.is_suspicious = False


def test_get_file_action_with_param(mocker: Any, tmp_path: Path) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {"File Hash": SAMPLE_SHA256}
    mock_siemplify.target_entities = []
    mock_siemplify.run_folder = str(tmp_path)

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value=SAMPLE_SHA256)

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.return_value = {
        "filename": "sample.tar",
        "content": b"sample_bytes",
    }
    mocker.patch.object(
        GetFile.WildfireManager,
        "from_siemplify",
        return_value=mock_mgr,
    )

    GetFile.main()

    mock_mgr.get_sample.assert_called_once_with(SAMPLE_SHA256)
    expected_b64 = base64.b64encode(b"sample_bytes").decode("utf-8")
    mock_siemplify.result.add_attachment.assert_called_once_with(
        f"WildFire sample {SAMPLE_SHA256}", "sample.tar", expected_b64
    )
    mock_siemplify.result.add_result_json.assert_called_once()
    json_results = mock_siemplify.result.add_result_json.call_args.args[0]
    assert len(json_results) == 1
    download_path = Path(json_results[0]["download_path"])
    assert download_path.parent == tmp_path
    assert download_path.name.startswith(f"{SAMPLE_SHA256}_")
    assert download_path.suffix == ".tar"
    assert download_path.read_bytes() == b"sample_bytes"
    assert json_results == [
        {
            "file_hash": SAMPLE_SHA256,
            "filename": "sample.tar",
            "download_path": str(download_path),
            "downloaded": True,
        }
    ]
    mock_siemplify.end.assert_called_once_with(
        f"Successfully downloaded file sample for {SAMPLE_SHA256} using Palo Alto Wildfire.",
        True,
        EXECUTION_STATE_COMPLETED,
    )


@pytest.mark.parametrize(
    ("filename", "expected_suffix"),
    [
        ("../../etc/passwd;rm", ".dat"),
        ("sample.exe;rm", ".dat"),
        ("sample.toolongextension", ".dat"),
        ("sample.TAR", ".TAR"),
    ],
)
def test_get_file_action_with_param_sanitizes_suffix(
    mocker: Any,
    tmp_path: Path,
    filename: str,
    expected_suffix: str,
) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {"File Hash": SAMPLE_MD5}
    mock_siemplify.target_entities = []
    mock_siemplify.run_folder = str(tmp_path)

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value=SAMPLE_MD5)

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.return_value = {
        "filename": filename,
        "content": b"payload",
    }
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetFile.main()

    json_results = mock_siemplify.result.add_result_json.call_args.args[0]
    download_path = Path(json_results[0]["download_path"])
    assert download_path.parent == tmp_path
    assert download_path.suffix == expected_suffix
    assert download_path.read_bytes() == b"payload"


def test_get_file_action_with_param_attaches_matching_entity(mocker: Any, tmp_path: Path) -> None:
    matching_entity = MockEntity(SAMPLE_MD5.upper(), EntityTypes.FILEHASH)
    other_entity = MockEntity(SAMPLE_MD5_OTHER, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {"File Hash": SAMPLE_MD5}
    mock_siemplify.target_entities = [matching_entity, other_entity]
    mock_siemplify.run_folder = str(tmp_path)

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value=SAMPLE_MD5)

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.return_value = {"filename": "sample.tar", "content": b"sample_bytes"}
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetFile.main()

    expected_b64 = base64.b64encode(b"sample_bytes").decode("utf-8")
    mock_siemplify.result.add_attachment.assert_called_once_with(
        f"WildFire sample {SAMPLE_MD5}", "sample.tar", expected_b64
    )
    mock_siemplify.result.add_entity_attachment.assert_called_once_with(SAMPLE_MD5.upper(), "sample.tar", expected_b64)
    json_results = mock_siemplify.result.add_result_json.call_args.args[0]
    assert Path(json_results[0]["download_path"]).read_bytes() == b"sample_bytes"


def test_get_file_action_with_param_save_error(mocker: Any, tmp_path: Path) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {"File Hash": SAMPLE_MD5}
    mock_siemplify.target_entities = []
    mock_siemplify.run_folder = str(tmp_path)

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value=SAMPLE_MD5)
    mocker.patch.object(GetFile, "_save_sample_to_disk", side_effect=OSError("No space left on device"))

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.return_value = {
        "filename": f"{SAMPLE_MD5}.tar",
        "content": b"sample_bytes",
    }
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetFile.main()

    mock_siemplify.result.add_attachment.assert_not_called()
    mock_siemplify.result.add_result_json.assert_not_called()
    mock_siemplify.end.assert_called_once_with(
        f'Error executing action "Get File". Reason: Failed to save sample for hash {SAMPLE_MD5} to disk: '
        "No space left on device",
        False,
        EXECUTION_STATE_FAILED,
    )


def test_get_file_download_dir_fallback(mocker: Any, tmp_path: Path) -> None:
    fallback_dir = tmp_path / "fallback"
    fallback_dir.mkdir()
    mocker.patch.object(GetFile.tempfile, "gettempdir", return_value=str(fallback_dir))

    siemplify_missing = mocker.Mock()
    siemplify_missing.run_folder = str(tmp_path / "missing")
    assert GetFile._get_download_dir(siemplify_missing) == fallback_dir
    assert GetFile._get_download_dir(mocker.Mock(spec=[])) == fallback_dir

    class UnwritableRunFolder:
        @property
        def run_folder(self) -> str:
            msg = "read-only filesystem"
            raise PermissionError(msg)

    assert GetFile._get_download_dir(UnwritableRunFolder()) == fallback_dir

    readonly_dir = tmp_path / "readonly"
    readonly_dir.mkdir()
    siemplify_readonly = mocker.Mock()
    siemplify_readonly.run_folder = str(readonly_dir)
    mocker.patch.object(GetFile.os, "access", return_value=False)
    assert GetFile._get_download_dir(siemplify_readonly) == fallback_dir


def test_save_sample_to_disk_cleans_up_on_write_error(mocker: Any, tmp_path: Path) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.run_folder = str(tmp_path)

    partial_file = tmp_path / "partial.tar"
    partial_file.write_bytes(b"")

    fake_file = mocker.MagicMock()
    fake_file.__enter__.return_value = fake_file
    fake_file.__exit__.return_value = False
    fake_file.name = str(partial_file)
    fake_file.write.side_effect = OSError("disk full")
    mocker.patch.object(GetFile.tempfile, "NamedTemporaryFile", return_value=fake_file)

    with pytest.raises(OSError, match="disk full"):
        GetFile._save_sample_to_disk(mock_siemplify, SAMPLE_MD5, "sample.tar", b"data")

    assert not partial_file.exists()


def test_get_file_action_with_param_not_found(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {"File Hash": SAMPLE_MD5}
    mock_siemplify.target_entities = []

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value=SAMPLE_MD5)

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.side_effect = WildfireNotFoundError(f"Sample is not available for {SAMPLE_MD5}")
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetFile.main()

    mock_siemplify.end.assert_called_once_with(
        f"No file sample was found for hash {SAMPLE_MD5} in Palo Alto Wildfire.",
        False,
        EXECUTION_STATE_COMPLETED,
    )


def test_get_file_action_with_entities(mocker: Any, tmp_path: Path) -> None:
    entity = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [entity]
    mock_siemplify.run_folder = str(tmp_path)

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value="")

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.return_value = {
        "filename": f"{SAMPLE_MD5}.tar",
        "content": b"sample_bytes_entity",
    }
    mocker.patch.object(
        GetFile.WildfireManager,
        "from_siemplify",
        return_value=mock_mgr,
    )

    GetFile.main()

    mock_mgr.get_sample.assert_called_once_with(SAMPLE_MD5)
    expected_b64 = base64.b64encode(b"sample_bytes_entity").decode("utf-8")
    mock_siemplify.result.add_entity_attachment.assert_called_once_with(SAMPLE_MD5, f"{SAMPLE_MD5}.tar", expected_b64)
    mock_siemplify.result.add_result_json.assert_called_once()
    json_results = mock_siemplify.result.add_result_json.call_args.args[0]
    assert len(json_results) == 1
    download_path = Path(json_results[0]["download_path"])
    assert download_path.parent == tmp_path
    assert download_path.read_bytes() == b"sample_bytes_entity"
    assert json_results == [
        {
            "file_hash": SAMPLE_MD5,
            "filename": f"{SAMPLE_MD5}.tar",
            "download_path": str(download_path),
            "downloaded": True,
        }
    ]
    mock_siemplify.end.assert_called_once_with(
        f"Successfully downloaded files for the following entities using Palo Alto Wildfire: {SAMPLE_MD5}.",
        True,
        EXECUTION_STATE_COMPLETED,
    )


def test_get_file_action_with_entities_save_error(mocker: Any, tmp_path: Path) -> None:
    entity = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [entity]
    mock_siemplify.run_folder = str(tmp_path)

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value="")
    mocker.patch.object(GetFile, "_save_sample_to_disk", side_effect=OSError("Permission denied"))

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.return_value = {"filename": f"{SAMPLE_MD5}.tar", "content": b"sample_bytes"}
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetFile.main()

    mock_siemplify.result.add_entity_attachment.assert_not_called()
    mock_siemplify.result.add_result_json.assert_not_called()
    mock_siemplify.end.assert_called_once_with(
        f'Error executing action "Get File". Reason: {SAMPLE_MD5}: Failed to save sample to disk: Permission denied',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_get_file_action_with_entities_partial_save_error(mocker: Any, tmp_path: Path) -> None:
    e_ok = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    e_err = MockEntity(SAMPLE_MD5_OTHER, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [e_ok, e_err]
    mock_siemplify.run_folder = str(tmp_path)

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value="")

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.side_effect = [
        {"filename": f"{SAMPLE_MD5}.tar", "content": b"ok_bytes"},
        {"filename": f"{SAMPLE_MD5_OTHER}.tar", "content": b"fail_bytes"},
    ]
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    real_save = GetFile._save_sample_to_disk
    calls = 0

    def save_side_effect(siemplify: Any, file_hash: str, filename: str, content: bytes) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            return real_save(siemplify, file_hash, filename, content)
        msg = "disk full"
        raise OSError(msg)

    mocker.patch.object(GetFile, "_save_sample_to_disk", side_effect=save_side_effect)

    GetFile.main()

    expected_msg = (
        f"Successfully downloaded files for the following entities using Palo Alto Wildfire: {SAMPLE_MD5}.\n"
        f"Action wasn't able to download files for the following entities using "
        f"Palo Alto Wildfire: {SAMPLE_MD5_OTHER}.\n"
        f"Errors:\n{SAMPLE_MD5_OTHER}: Failed to save sample to disk: disk full"
    )
    mock_siemplify.end.assert_called_once_with(expected_msg, True, EXECUTION_STATE_COMPLETED)
    json_results = mock_siemplify.result.add_result_json.call_args.args[0]
    assert len(json_results) == 1
    assert json_results[0]["file_hash"] == SAMPLE_MD5
    assert Path(json_results[0]["download_path"]).read_bytes() == b"ok_bytes"


def test_get_file_action_with_entities_partial_not_found(mocker: Any, tmp_path: Path) -> None:
    e_ok = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    e_missing = MockEntity(SAMPLE_MD5_OTHER, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [e_ok, e_missing]
    mock_siemplify.run_folder = str(tmp_path)

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value="")

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.side_effect = [
        {"filename": f"{SAMPLE_MD5}.tar", "content": b"sample_bytes"},
        WildfireNotFoundError(f"Sample is not available for {SAMPLE_MD5_OTHER}"),
    ]
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetFile.main()

    expected_msg = (
        f"Successfully downloaded files for the following entities using Palo Alto Wildfire: {SAMPLE_MD5}.\n"
        f"Action wasn't able to download files for the following entities using Palo Alto Wildfire: {SAMPLE_MD5_OTHER}."
    )
    mock_siemplify.end.assert_called_once_with(expected_msg, True, EXECUTION_STATE_COMPLETED)
    json_results = mock_siemplify.result.add_result_json.call_args.args[0]
    assert len(json_results) == 1
    assert json_results[0]["file_hash"] == SAMPLE_MD5
    assert Path(json_results[0]["download_path"]).read_bytes() == b"sample_bytes"


def test_get_file_action_with_entities_partial_hard_error(mocker: Any, tmp_path: Path) -> None:
    e_ok = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    e_err = MockEntity(SAMPLE_MD5_OTHER, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [e_ok, e_err]
    mock_siemplify.run_folder = str(tmp_path)

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value="")

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.side_effect = [
        {"filename": f"{SAMPLE_MD5}.tar", "content": b"sample_bytes"},
        WildfireManagerError("Rate limit exceeded"),
    ]
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetFile.main()

    expected_msg = (
        f"Successfully downloaded files for the following entities using Palo Alto Wildfire: {SAMPLE_MD5}.\n"
        f"Action wasn't able to download files for the following entities using "
        f"Palo Alto Wildfire: {SAMPLE_MD5_OTHER}.\n"
        f"Errors:\n{SAMPLE_MD5_OTHER}: Rate limit exceeded"
    )
    mock_siemplify.end.assert_called_once_with(expected_msg, True, EXECUTION_STATE_COMPLETED)
    json_results = mock_siemplify.result.add_result_json.call_args.args[0]
    assert len(json_results) == 1
    assert json_results[0]["file_hash"] == SAMPLE_MD5
    assert Path(json_results[0]["download_path"]).read_bytes() == b"sample_bytes"


def test_get_file_action_with_entities_all_not_found(mocker: Any) -> None:
    entity = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [entity]

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value="")

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.side_effect = WildfireNotFoundError(f"Sample is not available for {SAMPLE_MD5}")
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetFile.main()

    expected_msg = (
        "No files were downloaded using Palo Alto Wildfire.\n"
        f"Action wasn't able to download files for the following entities using Palo Alto Wildfire: {SAMPLE_MD5}."
    )
    mock_siemplify.end.assert_called_once_with(expected_msg, False, EXECUTION_STATE_COMPLETED)


def test_get_file_action_with_entities_empty(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = []

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value="")
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", return_value=mocker.Mock())

    GetFile.main()

    mock_siemplify.end.assert_called_once_with(
        "No files were downloaded using Palo Alto Wildfire.",
        False,
        EXECUTION_STATE_COMPLETED,
    )


def test_get_file_action_with_entities_all_hard_error(mocker: Any) -> None:
    entity = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [entity]

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value="")

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.side_effect = WildfireManagerError("Unauthorized")
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetFile.main()

    mock_siemplify.end.assert_called_once_with(
        f'Error executing action "Get File". Reason: {SAMPLE_MD5}: Unauthorized',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_get_file_action_failure(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {"File Hash": SAMPLE_MD5}
    mock_siemplify.target_entities = []

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value=SAMPLE_MD5)

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.side_effect = RuntimeError("HTTP 500 Internal Server Error")
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetFile.main()

    mock_siemplify.end.assert_called_once_with(
        'Error executing action "Get File". Reason: HTTP 500 Internal Server Error',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_get_file_action_init_failure(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value="")
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", side_effect=Exception("Missing config"))

    GetFile.main()

    mock_siemplify.end.assert_called_once_with(
        'Error executing action "Get File". Reason: Missing config',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_get_report_action_with_param(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {"File Hash": SAMPLE_MD5}
    mock_siemplify.target_entities = []

    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value=SAMPLE_MD5)

    report_data = {
        "file_info": {"malware": "yes", "md5": SAMPLE_MD5},
        "task_info": {"report": {"verdict": "malware"}},
    }
    mock_mgr = mocker.Mock()
    mock_mgr.get_report.return_value = report_data
    mock_mgr.get_pdf_report.return_value = {
        "filename": f"{SAMPLE_MD5}.pdf",
        "content": b"%PDF data",
    }
    mocker.patch.object(
        GetReport.WildfireManager,
        "from_siemplify",
        return_value=mock_mgr,
    )

    GetReport.main()

    mock_mgr.get_report.assert_called_once_with(SAMPLE_MD5)
    mock_mgr.get_pdf_report.assert_called_once_with(SAMPLE_MD5)
    mock_siemplify.result.add_result_json.assert_called_once_with([report_data])
    mock_siemplify.result.add_attachment.assert_called_once()
    mock_siemplify.result.add_data_table.assert_called_once()
    mock_siemplify.end.assert_called_once_with(
        f"Successfully downloaded report for {SAMPLE_MD5} using Palo Alto Wildfire.",
        True,
        EXECUTION_STATE_COMPLETED,
    )


def test_get_report_action_with_param_not_found(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {"File Hash": SAMPLE_MD5}
    mock_siemplify.target_entities = []

    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value=SAMPLE_MD5)

    mock_mgr = mocker.Mock()
    mock_mgr.get_report.side_effect = WildfireNotFoundError(f"Report is not available for {SAMPLE_MD5}")
    mocker.patch.object(GetReport.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetReport.main()

    mock_siemplify.end.assert_called_once_with(
        f"No report was found for hash {SAMPLE_MD5} in Palo Alto Wildfire.",
        False,
        EXECUTION_STATE_COMPLETED,
    )


def test_get_report_action_with_entities(mocker: Any) -> None:
    entity = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [entity]

    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value="")

    report_data = {
        "file_info": {"malware": "yes", "md5": SAMPLE_MD5},
        "task_info": {"report": {"verdict": "malware"}},
    }
    mock_mgr = mocker.Mock()
    mock_mgr.get_report.return_value = report_data
    mock_mgr.get_pdf_report.return_value = {
        "filename": f"{SAMPLE_MD5}.pdf",
        "content": b"%PDF data",
    }
    mocker.patch.object(
        GetReport.WildfireManager,
        "from_siemplify",
        return_value=mock_mgr,
    )

    GetReport.main()

    mock_mgr.get_report.assert_called_once_with(SAMPLE_MD5)
    mock_mgr.get_pdf_report.assert_called_once_with(SAMPLE_MD5)
    mock_siemplify.result.add_result_json.assert_called_once_with([report_data])
    mock_siemplify.result.add_entity_attachment.assert_called_once()
    mock_siemplify.result.add_entity_table.assert_called_once()
    mock_siemplify.end.assert_called_once_with(
        f"Successfully enriched the following entities using Palo Alto Wildfire: {SAMPLE_MD5}.",
        True,
        EXECUTION_STATE_COMPLETED,
    )


def test_get_report_action_with_entities_partial_not_found(mocker: Any) -> None:
    e_ok = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    e_missing = MockEntity(SAMPLE_MD5_OTHER, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [e_ok, e_missing]

    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value="")

    report_data = {
        "file_info": {"malware": "no", "md5": SAMPLE_MD5},
        "task_info": {"report": {"verdict": "benign"}},
    }
    mock_mgr = mocker.Mock()
    mock_mgr.get_report.side_effect = [
        report_data,
        WildfireNotFoundError(f"Report is not available for {SAMPLE_MD5_OTHER}"),
    ]
    mock_mgr.get_pdf_report.return_value = {"filename": f"{SAMPLE_MD5}.pdf", "content": b"%PDF"}
    mocker.patch.object(GetReport.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetReport.main()

    expected_msg = (
        f"Successfully enriched the following entities using Palo Alto Wildfire: {SAMPLE_MD5}.\n"
        f"Action wasn't able to enrich the following entities using Palo Alto Wildfire: {SAMPLE_MD5_OTHER}."
    )
    mock_siemplify.end.assert_called_once_with(expected_msg, True, EXECUTION_STATE_COMPLETED)


def test_get_report_action_with_entities_partial_hard_error(mocker: Any) -> None:
    e_ok = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    e_err = MockEntity(SAMPLE_MD5_OTHER, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [e_ok, e_err]

    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value="")

    report_data = {
        "file_info": {"malware": "no", "md5": SAMPLE_MD5},
        "task_info": {"report": {"verdict": "benign"}},
    }
    mock_mgr = mocker.Mock()
    mock_mgr.get_report.side_effect = [
        report_data,
        WildfireManagerError("Rate limit exceeded"),
    ]
    mock_mgr.get_pdf_report.return_value = {"filename": f"{SAMPLE_MD5}.pdf", "content": b"%PDF"}
    mocker.patch.object(GetReport.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetReport.main()

    expected_msg = (
        f"Successfully enriched the following entities using Palo Alto Wildfire: {SAMPLE_MD5}.\n"
        f"Action wasn't able to enrich the following entities using Palo Alto Wildfire: {SAMPLE_MD5_OTHER}.\n"
        f"Errors:\n{SAMPLE_MD5_OTHER}: Rate limit exceeded"
    )
    mock_siemplify.end.assert_called_once_with(expected_msg, True, EXECUTION_STATE_COMPLETED)


def test_get_report_action_with_entities_empty(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = []

    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value="")
    mocker.patch.object(GetReport.WildfireManager, "from_siemplify", return_value=mocker.Mock())

    GetReport.main()

    mock_siemplify.end.assert_called_once_with(
        "None of the provided entities were enriched.",
        False,
        EXECUTION_STATE_COMPLETED,
    )


def test_get_report_action_with_entities_all_not_found(mocker: Any) -> None:
    entity = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [entity]

    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value="")

    mock_mgr = mocker.Mock()
    mock_mgr.get_report.side_effect = WildfireNotFoundError(f"Report is not available for {SAMPLE_MD5}")
    mocker.patch.object(GetReport.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetReport.main()

    expected_msg = (
        "None of the provided entities were enriched.\n"
        f"Action wasn't able to enrich the following entities using Palo Alto Wildfire: {SAMPLE_MD5}."
    )
    mock_siemplify.end.assert_called_once_with(expected_msg, False, EXECUTION_STATE_COMPLETED)


def test_get_report_action_with_entities_all_hard_error(mocker: Any) -> None:
    entity = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [entity]

    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value="")

    mock_mgr = mocker.Mock()
    mock_mgr.get_report.side_effect = WildfireManagerError("Unauthorized")
    mocker.patch.object(GetReport.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetReport.main()

    mock_siemplify.end.assert_called_once_with(
        f'Error executing action "Get Report". Reason: {SAMPLE_MD5}: Unauthorized',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_get_report_action_failure(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {"File Hash": SAMPLE_MD5}
    mock_siemplify.target_entities = []

    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value=SAMPLE_MD5)

    mock_mgr = mocker.Mock()
    mock_mgr.get_report.side_effect = RuntimeError("WildFire report unavailable")
    mocker.patch.object(GetReport.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetReport.main()

    mock_siemplify.end.assert_called_once_with(
        'Error executing action "Get Report". Reason: WildFire report unavailable',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_get_report_action_init_failure(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value="")
    mocker.patch.object(GetReport.WildfireManager, "from_siemplify", side_effect=Exception("Missing config"))

    GetReport.main()

    mock_siemplify.end.assert_called_once_with(
        'Error executing action "Get Report". Reason: Missing config',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_detonate_file_action(mocker: Any) -> None:
    mocker.patch.object(DetonateFile, "time", mocker.Mock(sleep=mocker.Mock()))
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {"File Paths": "test.exe"}
    mock_siemplify.case_id = "12345"

    mocker.patch.object(DetonateFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(DetonateFile, "extract_action_param", return_value="test.exe")

    mock_mgr = mocker.Mock()
    mock_mgr.submit_file.return_value = {"md5": SAMPLE_MD5}
    mock_mgr.get_report.return_value = {
        "file_info": {"malware": "no", "md5": SAMPLE_MD5},
        "task_info": {"report": {"verdict": "benign"}},
    }
    mock_mgr.get_pdf_report.return_value = {
        "filename": "test.pdf",
        "content": b"%PDF data",
    }
    mocker.patch.object(DetonateFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    DetonateFile.main()

    mock_mgr.submit_file.assert_called_once_with("test.exe")
    mock_siemplify.result.add_attachment.assert_called_once()
    mock_siemplify.end.assert_called_once_with(
        "Successfully uploaded files and downloaded reports using Palo Alto Wildfire: test.exe.",
        True,
        EXECUTION_STATE_COMPLETED,
    )


def test_detonate_file_action_init_failure(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.parameters = {"File Paths": "test.exe"}
    mocker.patch.object(DetonateFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(DetonateFile, "extract_action_param", return_value="test.exe")
    mocker.patch.object(DetonateFile.WildfireManager, "from_siemplify", side_effect=Exception("Missing config"))

    DetonateFile.main()

    mock_siemplify.end.assert_called_once_with(
        'Error executing action "Detonate File". Reason: Missing config', False, EXECUTION_STATE_FAILED
    )


def test_detonate_file_action_submit_failure(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.parameters = {"File Paths": "missing.exe"}
    mocker.patch.object(DetonateFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(DetonateFile, "extract_action_param", return_value="missing.exe")

    mock_mgr = mocker.Mock()
    mock_mgr.submit_file.side_effect = WildfireManagerError("File not found: missing.exe")
    mocker.patch.object(DetonateFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    DetonateFile.main()

    mock_siemplify.end.assert_called_once_with(
        'Error executing action "Detonate File". Reason: File not found: missing.exe',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_detonate_file_action_empty_paths(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mocker.patch.object(DetonateFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(DetonateFile, "extract_action_param", return_value=" , ")

    DetonateFile.main()

    mock_siemplify.end.assert_called_once_with(
        'Error executing action "Detonate File". Reason: At least one file path must be provided.',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_detonate_file_action_pdf_failure(mocker: Any) -> None:
    mocker.patch.object(DetonateFile, "time", mocker.Mock(sleep=mocker.Mock()))
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {"File Paths": "test.exe"}
    mock_siemplify.case_id = "12345"

    mocker.patch.object(DetonateFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(DetonateFile, "extract_action_param", return_value="test.exe")

    mock_mgr = mocker.Mock()
    mock_mgr.submit_file.return_value = {"md5": SAMPLE_MD5}
    mock_mgr.get_report.return_value = {
        "file_info": {"malware": "no", "md5": SAMPLE_MD5},
        "task_info": {"report": {"verdict": "benign"}},
    }
    mock_mgr.get_pdf_report.side_effect = WildfireManagerError(f"Unable to get PDF report for {SAMPLE_MD5}: HTTP 500")
    mocker.patch.object(DetonateFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    DetonateFile.main()

    mock_siemplify.end.assert_called_once_with(
        f'Error executing action "Detonate File". Reason: Unable to get PDF report for {SAMPLE_MD5}: HTTP 500',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_get_pcap_action(mocker: Any) -> None:
    entity = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.target_entities = [entity]

    mocker.patch.object(GetPcap, "SiemplifyAction", return_value=mock_siemplify)

    mock_mgr = mocker.Mock()
    mock_mgr.get_pcap.return_value = {
        "filename": f"{SAMPLE_MD5}.pcap",
        "content": b"PCAPDATA",
    }
    mocker.patch.object(GetPcap.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetPcap.main()

    mock_mgr.get_pcap.assert_called_once_with(SAMPLE_MD5)
    mock_siemplify.result.add_entity_attachment.assert_called_once()
    mock_siemplify.end.assert_called_once_with(
        f"Successfully downloaded PCAP files for the following entities using Palo Alto Wildfire: {SAMPLE_MD5}.",
        True,
        EXECUTION_STATE_COMPLETED,
    )


def test_get_pcap_action_partial_not_found(mocker: Any) -> None:
    e_ok = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    e_missing = MockEntity(SAMPLE_MD5_OTHER, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.target_entities = [e_ok, e_missing]

    mocker.patch.object(GetPcap, "SiemplifyAction", return_value=mock_siemplify)

    mock_mgr = mocker.Mock()
    mock_mgr.get_pcap.side_effect = [
        {"filename": f"{SAMPLE_MD5}.pcap", "content": b"PCAPDATA"},
        WildfireNotFoundError(f"PCAP is not available for {SAMPLE_MD5_OTHER}"),
    ]
    mocker.patch.object(GetPcap.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetPcap.main()

    expected_msg = (
        f"Successfully downloaded PCAP files for the following entities using Palo Alto Wildfire: {SAMPLE_MD5}.\n"
        f"Action wasn't able to download PCAP files for the following entities using "
        f"Palo Alto Wildfire: {SAMPLE_MD5_OTHER}."
    )
    mock_siemplify.end.assert_called_once_with(expected_msg, True, EXECUTION_STATE_COMPLETED)


def test_get_pcap_action_partial_hard_error(mocker: Any) -> None:
    e_ok = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    e_err = MockEntity(SAMPLE_MD5_OTHER, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.target_entities = [e_ok, e_err]

    mocker.patch.object(GetPcap, "SiemplifyAction", return_value=mock_siemplify)

    mock_mgr = mocker.Mock()
    mock_mgr.get_pcap.side_effect = [
        {"filename": f"{SAMPLE_MD5}.pcap", "content": b"PCAPDATA"},
        WildfireManagerError("Rate limit exceeded"),
    ]
    mocker.patch.object(GetPcap.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetPcap.main()

    expected_msg = (
        f"Successfully downloaded PCAP files for the following entities using Palo Alto Wildfire: {SAMPLE_MD5}.\n"
        f"Action wasn't able to download PCAP files for the following entities using "
        f"Palo Alto Wildfire: {SAMPLE_MD5_OTHER}.\n"
        f"Errors:\n{SAMPLE_MD5_OTHER}: Rate limit exceeded"
    )
    mock_siemplify.end.assert_called_once_with(expected_msg, True, EXECUTION_STATE_COMPLETED)


def test_get_pcap_action_empty(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.target_entities = []

    mocker.patch.object(GetPcap, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetPcap.WildfireManager, "from_siemplify", return_value=mocker.Mock())

    GetPcap.main()

    mock_siemplify.end.assert_called_once_with(
        "No PCAP files were downloaded using Palo Alto Wildfire.",
        False,
        EXECUTION_STATE_COMPLETED,
    )


def test_get_pcap_action_all_not_found(mocker: Any) -> None:
    entity = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.target_entities = [entity]

    mocker.patch.object(GetPcap, "SiemplifyAction", return_value=mock_siemplify)

    mock_mgr = mocker.Mock()
    mock_mgr.get_pcap.side_effect = WildfireNotFoundError(f"PCAP is not available for {SAMPLE_MD5}")
    mocker.patch.object(GetPcap.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetPcap.main()

    expected_msg = (
        "No PCAP files were downloaded using Palo Alto Wildfire.\n"
        f"Action wasn't able to download PCAP files for the following entities using Palo Alto Wildfire: {SAMPLE_MD5}."
    )
    mock_siemplify.end.assert_called_once_with(expected_msg, False, EXECUTION_STATE_COMPLETED)


def test_get_pcap_action_all_hard_error(mocker: Any) -> None:
    entity = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.target_entities = [entity]

    mocker.patch.object(GetPcap, "SiemplifyAction", return_value=mock_siemplify)

    mock_mgr = mocker.Mock()
    mock_mgr.get_pcap.side_effect = WildfireManagerError("Unauthorized")
    mocker.patch.object(GetPcap.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetPcap.main()

    mock_siemplify.end.assert_called_once_with(
        f'Error executing action "Get Pcap". Reason: {SAMPLE_MD5}: Unauthorized',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_get_pcap_action_init_failure(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mocker.patch.object(GetPcap, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetPcap.WildfireManager, "from_siemplify", side_effect=Exception("Missing config"))

    GetPcap.main()

    mock_siemplify.end.assert_called_once_with(
        'Error executing action "Get Pcap". Reason: Missing config', False, EXECUTION_STATE_FAILED
    )


def test_ping_action_success(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mocker.patch.object(Ping, "SiemplifyAction", return_value=mock_siemplify)

    mock_mgr = mocker.Mock()
    mock_mgr.test_connectivity.return_value = True
    mocker.patch.object(
        Ping.WildfireManager,
        "from_siemplify",
        return_value=mock_mgr,
    )

    Ping.main()

    mock_siemplify.end.assert_called_once_with(
        "Successfully connected to the Palo Alto Wildfire server with the provided connection parameters!",
        True,
        EXECUTION_STATE_COMPLETED,
    )


def test_ping_action_failure(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mocker.patch.object(Ping, "SiemplifyAction", return_value=mock_siemplify)

    mock_mgr = mocker.Mock()
    mock_mgr.test_connectivity.side_effect = RuntimeError("Invalid SCM credentials")
    mocker.patch.object(
        Ping.WildfireManager,
        "from_siemplify",
        return_value=mock_mgr,
    )

    Ping.main()

    mock_siemplify.end.assert_called_once_with(
        'Error executing action "Ping". Reason: '
        "Failed to connect to the Palo Alto Wildfire server: Invalid SCM credentials",
        False,
        EXECUTION_STATE_FAILED,
    )


def test_ping_action_init_failure(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mocker.patch.object(Ping, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(Ping.WildfireManager, "from_siemplify", side_effect=WildfireManagerError("Missing config"))

    Ping.main()

    mock_siemplify.end.assert_called_once_with(
        'Error executing action "Ping". Reason: Failed to connect to the Palo Alto Wildfire server: Missing config',
        False,
        EXECUTION_STATE_FAILED,
    )
