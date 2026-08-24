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

import hashlib
import io
import json
import zipfile
from unittest import mock

import pytest
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyDataModel import EntityTypes

from ..actions import AcquireFile
from ..actions.AcquireFile import (
    BadZipPasswordError,
    generate_password,
    get_acquired_file_info,
    main,
    process_acquired_file_bytes,
    resolve_agent_id,
)
from ..core.SentinelOneManager import (
    SentinelOneAgentNotFoundError,
    SentinelOneManager,
)


def create_test_zip_package(
    file_path: str,
    file_name: str,
    content: bytes,
    password: str = "TestPassword123!",
    included: bool = True,
    reason: str = "OK",
) -> bytes:
    """Helper to construct an in-memory ZIP package matching SentinelOne format."""
    manifest = [
        {
            "path": file_path,
            "name": file_name,
            "included": included,
            "reason": reason,
            "size": len(content),
            "sha1": hashlib.sha1(content).hexdigest(),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    ]
    manifest_bytes = json.dumps(manifest).encode("utf-8")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("manifest.json", manifest_bytes)
        if included:
            zipf.writestr(file_name, content)

    return buf.getvalue()


class MockEntity:
    def __init__(self, identifier: str, entity_type: str):
        self.identifier = identifier
        self.entity_type = entity_type


class TestAcquireFileHelpers:
    def test_generate_password_complexity(self):
        pwd = generate_password()
        assert len(pwd) == 15
        assert any(c.islower() for c in pwd)
        assert any(c.isupper() for c in pwd)
        assert any(c.isdigit() for c in pwd)
        assert any(not c.isalnum() for c in pwd)

    def test_resolve_agent_id_from_param(self):
        mock_siemplify = mock.MagicMock()
        mock_manager = mock.MagicMock()
        res = resolve_agent_id(mock_siemplify, mock_manager, "agent-123")
        assert res == "agent-123"

    def test_resolve_agent_id_from_entity(self):
        mock_siemplify = mock.MagicMock()
        mock_siemplify.target_entities = [
            MockEntity("host-1", EntityTypes.HOSTNAME)
        ]
        mock_manager = mock.MagicMock()
        mock_manager.find_endpoint_agent_id.return_value = 998877

        res = resolve_agent_id(mock_siemplify, mock_manager, None)
        assert res == "998877"
        mock_manager.find_endpoint_agent_id.assert_called_once_with(
            "host-1", by_ip_address=False
        )

    def test_resolve_agent_id_from_ip_entity(self):
        mock_siemplify = mock.MagicMock()
        mock_siemplify.target_entities = [
            MockEntity("10.0.0.1", EntityTypes.ADDRESS)
        ]
        mock_manager = mock.MagicMock()
        mock_manager.find_endpoint_agent_id.return_value = 112233

        res = resolve_agent_id(mock_siemplify, mock_manager, "")
        assert res == "112233"
        mock_manager.find_endpoint_agent_id.assert_called_once_with(
            "10.0.0.1", by_ip_address=True
        )

    def test_resolve_agent_id_not_found(self):
        mock_siemplify = mock.MagicMock()
        mock_siemplify.target_entities = [
            MockEntity("unknown-host", EntityTypes.HOSTNAME)
        ]
        mock_manager = mock.MagicMock()
        mock_manager.find_endpoint_agent_id.side_effect = (
            SentinelOneAgentNotFoundError("Not found")
        )

        res = resolve_agent_id(mock_siemplify, mock_manager, None)
        assert res is None

    def test_get_acquired_file_info_success(self):
        zip_bytes = create_test_zip_package(
            "/tmp/test.exe", "test.exe", b"test content"
        )
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zipf:
            info, manifest = get_acquired_file_info(zipf, "/tmp/test.exe")
            assert info["path"] == "/tmp/test.exe"
            assert info["included"] is True

    def test_get_acquired_file_info_fallback_single_file(self):
        zip_bytes = create_test_zip_package(
            "C:\\path\\file.txt", "file.txt", b"test content"
        )
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zipf:
            info, manifest = get_acquired_file_info(zipf, "/other/path/file.txt")
            assert info["name"] == "file.txt"

    def test_get_acquired_file_info_bad_password(self):
        zip_bytes = create_test_zip_package(
            "/tmp/test.exe", "test.exe", b"test content"
        )
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zipf:
            with mock.patch.object(
                zipf,
                "read",
                side_effect=RuntimeError(
                    "Bad password for file: manifest.json"
                ),
            ):
                with pytest.raises(BadZipPasswordError):
                    get_acquired_file_info(zipf, "/tmp/test.exe")

    def test_process_acquired_file_bytes(self):
        content = b"sample binary payload"
        zip_bytes = create_test_zip_package(
            "/tmp/test.bin", "test.bin", content
        )
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zipf:
            fname, md5_val, sha256_val, size = process_acquired_file_bytes(zipf)
            assert fname == "test.bin"
            assert md5_val == hashlib.md5(content).hexdigest()
            assert sha256_val == hashlib.sha256(content).hexdigest()
            assert size == len(content)

    def test_process_acquired_file_bytes_manifest_only(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr("manifest.json", b"[]")
        with zipfile.ZipFile(buf) as zipf:
            fname, md5_val, sha256_val, size = process_acquired_file_bytes(zipf)
            assert fname == ""
            assert md5_val == ""
            assert size == 0


class TestAcquireFileAction:
    @mock.patch.object(AcquireFile, "SiemplifyAction")
    @mock.patch.object(SentinelOneManager, "get_token", return_value="dummy_token")
    @mock.patch.object(SentinelOneManager, "fetch_files")
    def test_first_run_success_auto_password(
        self, mock_fetch, mock_token, mock_siemplify_cls
    ):
        mock_siemplify = mock_siemplify_cls.return_value
        mock_siemplify.get_configuration.return_value = {
            "Api Root": "https://test.sentinelone.net",
            "Username": "testuser",
            "Password": "testpass",
        }
        mock_siemplify.parameters = {
            "Agent ID": "123456",
            "File Path": "/tmp/malware.exe",
            "Password": None,
        }

        main(is_first_run=True)

        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args[1]
        assert call_args["agent_id"] == "123456"
        assert call_args["file_path"] == "/tmp/malware.exe"
        assert len(call_args["password"]) == 15

        mock_siemplify.end.assert_called_once()
        msg, state_json, state = mock_siemplify.end.call_args[0]
        assert state == EXECUTION_STATE_INPROGRESS
        parsed_state = json.loads(state_json)
        assert parsed_state["agent_id"] == "123456"
        assert parsed_state["file_path"] == "/tmp/malware.exe"

    @mock.patch.object(AcquireFile, "SiemplifyAction")
    @mock.patch.object(SentinelOneManager, "get_token", return_value="dummy_token")
    @mock.patch.object(SentinelOneManager, "fetch_files")
    def test_first_run_custom_password(
        self, mock_fetch, mock_token, mock_siemplify_cls
    ):
        mock_siemplify = mock_siemplify_cls.return_value
        mock_siemplify.get_configuration.return_value = {
            "Api Root": "https://test.sentinelone.net",
            "Username": "testuser",
            "Password": "testpass",
        }
        mock_siemplify.parameters = {
            "Agent ID": "agent_uuid_123",
            "File Path": "C:\\Windows\\System32\\calc.exe",
            "Password": "CustomSecret123!",
        }

        main(is_first_run=True)

        mock_fetch.assert_called_once_with(
            agent_id="agent_uuid_123",
            file_path="C:\\Windows\\System32\\calc.exe",
            password="CustomSecret123!",
        )
        assert mock_siemplify.end.call_args[0][2] == EXECUTION_STATE_INPROGRESS

    @mock.patch.object(AcquireFile, "SiemplifyAction")
    @mock.patch.object(SentinelOneManager, "get_token", return_value="dummy_token")
    def test_first_run_invalid_relative_path(
        self, mock_token, mock_siemplify_cls
    ):
        mock_siemplify = mock_siemplify_cls.return_value
        mock_siemplify.get_configuration.return_value = {
            "Api Root": "https://test.sentinelone.net",
            "Username": "testuser",
            "Password": "testpass",
        }
        mock_siemplify.parameters = {
            "Agent ID": "123456",
            "File Path": "relative_file.txt",
            "Password": None,
        }

        main(is_first_run=True)

        mock_siemplify.end.assert_called_once()
        _, _, status = mock_siemplify.end.call_args[0]
        assert status == EXECUTION_STATE_FAILED

    @mock.patch.object(AcquireFile, "SiemplifyAction")
    @mock.patch.object(SentinelOneManager, "get_token", return_value="dummy_token")
    def test_first_run_no_agent_id(self, mock_token, mock_siemplify_cls):
        mock_siemplify = mock_siemplify_cls.return_value
        mock_siemplify.target_entities = []
        mock_siemplify.get_configuration.return_value = {
            "Api Root": "https://test.sentinelone.net",
            "Username": "testuser",
            "Password": "testpass",
        }
        mock_siemplify.parameters = {
            "Agent ID": None,
            "File Path": "/tmp/test.exe",
            "Password": None,
        }

        main(is_first_run=True)

        mock_siemplify.end.assert_called_once()
        _, _, status = mock_siemplify.end.call_args[0]
        assert status == EXECUTION_STATE_FAILED

    @mock.patch.object(AcquireFile, "SiemplifyAction")
    @mock.patch.object(SentinelOneManager, "get_token", return_value="dummy_token")
    @mock.patch.object(SentinelOneManager, "get_file_upload_activities")
    def test_polling_in_progress(
        self, mock_activities, mock_token, mock_siemplify_cls
    ):
        mock_siemplify = mock_siemplify_cls.return_value
        mock_siemplify.get_configuration.return_value = {
            "Api Root": "https://test.sentinelone.net",
            "Username": "testuser",
            "Password": "testpass",
        }
        mock_siemplify.parameters = {
            "additional_data": json.dumps(
                {
                    "agent_id": "123456",
                    "file_path": "/tmp/test.exe",
                    "password": "Password123!",
                    "created_at": "2026-08-21T18:00:00Z",
                    "activities_seen": [],
                }
            )
        }

        mock_activities.return_value = []

        main(is_first_run=False)

        mock_activities.assert_called_once_with(
            agent_id="123456", created_at_gte="2026-08-21T18:00:00Z"
        )
        mock_siemplify.end.assert_called_once()
        msg, state_json, status = mock_siemplify.end.call_args[0]
        assert status == EXECUTION_STATE_INPROGRESS

    @mock.patch.object(AcquireFile, "SiemplifyAction")
    @mock.patch.object(SentinelOneManager, "get_token", return_value="dummy_token")
    def test_polling_missing_additional_data(
        self, mock_token, mock_siemplify_cls
    ):
        mock_siemplify = mock_siemplify_cls.return_value
        mock_siemplify.get_configuration.return_value = {
            "Api Root": "https://test.sentinelone.net",
            "Username": "testuser",
            "Password": "testpass",
        }
        mock_siemplify.parameters = {
            "additional_data": "{}"
        }

        main(is_first_run=False)

        mock_siemplify.end.assert_called_once()
        _, _, status = mock_siemplify.end.call_args[0]
        assert status == EXECUTION_STATE_FAILED

    @mock.patch.object(AcquireFile, "SiemplifyAction")
    @mock.patch.object(SentinelOneManager, "get_token", return_value="dummy_token")
    @mock.patch.object(SentinelOneManager, "get_file_upload_activities")
    @mock.patch.object(SentinelOneManager, "download_file_by_url")
    def test_polling_completed_success(
        self,
        mock_download,
        mock_activities,
        mock_token,
        mock_siemplify_cls,
    ):
        password = "SecretPass123!"
        content = b"executable payload binary"
        zip_bytes = create_test_zip_package(
            "/tmp/test.exe", "test.exe", content, password
        )

        mock_siemplify = mock_siemplify_cls.return_value
        mock_siemplify.get_configuration.return_value = {
            "Api Root": "https://test.sentinelone.net",
            "Username": "testuser",
            "Password": "testpass",
        }
        mock_siemplify.parameters = {
            "additional_data": json.dumps(
                {
                    "agent_id": "123456",
                    "file_path": "/tmp/test.exe",
                    "password": password,
                    "created_at": "2026-08-21T18:00:00Z",
                    "activities_seen": [],
                }
            )
        }

        mock_activities.return_value = [
            {
                "id": "act-101",
                "data": {
                    "downloadUrl": "/activities/download-file?download_url=act-101"
                },
            }
        ]
        mock_download.return_value = zip_bytes

        main(is_first_run=False)

        mock_siemplify.result.add_result_json.assert_called_once()
        result_json = mock_siemplify.result.add_result_json.call_args[0][0]
        assert result_json["status"] == "COMPLETED"
        assert result_json["file_path"] == "/tmp/test.exe"
        assert result_json["md5"] == hashlib.md5(content).hexdigest()
        assert result_json["sha256"] == hashlib.sha256(content).hexdigest()
        assert "download_path" in result_json
        assert result_json["download_path"].endswith(".zip")
        assert result_json["local_package_file"].endswith(".zip")

        mock_siemplify.end.assert_called_once()
        msg, is_success, status = mock_siemplify.end.call_args[0]
        assert status == EXECUTION_STATE_COMPLETED
        assert is_success == "true"

    @mock.patch.object(AcquireFile, "SiemplifyAction")
    @mock.patch.object(SentinelOneManager, "get_token", return_value="dummy_token")
    @mock.patch.object(SentinelOneManager, "get_file_upload_activities")
    @mock.patch.object(SentinelOneManager, "download_file_by_url")
    def test_polling_file_not_included(
        self,
        mock_download,
        mock_activities,
        mock_token,
        mock_siemplify_cls,
    ):
        password = "SecretPass123!"
        zip_bytes = create_test_zip_package(
            "/tmp/missing.exe",
            "missing.exe",
            b"",
            password,
            included=False,
            reason="File permission denied",
        )

        mock_siemplify = mock_siemplify_cls.return_value
        mock_siemplify.get_configuration.return_value = {
            "Api Root": "https://test.sentinelone.net",
            "Username": "testuser",
            "Password": "testpass",
        }
        mock_siemplify.parameters = {
            "additional_data": json.dumps(
                {
                    "agent_id": "123456",
                    "file_path": "/tmp/missing.exe",
                    "password": password,
                    "created_at": "2026-08-21T18:00:00Z",
                    "activities_seen": [],
                }
            )
        }

        mock_activities.return_value = [
            {"id": "act-102", "data": {"downloadUrl": "/download/102"}}
        ]
        mock_download.return_value = zip_bytes

        main(is_first_run=False)

        mock_siemplify.result.add_result_json.assert_called_once()
        result_json = mock_siemplify.result.add_result_json.call_args[0][0]
        assert result_json["status"] == "FAILED"
        assert result_json["reason"] == "File permission denied"

        mock_siemplify.end.assert_called_once()
        msg, is_success, status = mock_siemplify.end.call_args[0]
        assert status == EXECUTION_STATE_FAILED
        assert is_success == "false"

    @mock.patch.object(AcquireFile, "SiemplifyAction")
    @mock.patch.object(SentinelOneManager, "get_token", return_value="dummy_token")
    @mock.patch.object(SentinelOneManager, "get_file_upload_activities")
    @mock.patch.object(SentinelOneManager, "download_file_by_url")
    def test_polling_skip_bad_password_and_corrupt_zip(
        self,
        mock_download,
        mock_activities,
        mock_token,
        mock_siemplify_cls,
    ):
        password = "TargetPassword123!"
        good_content = b"valid file"
        good_zip = create_test_zip_package(
            "/tmp/target.exe", "target.exe", good_content, password
        )

        mock_siemplify = mock_siemplify_cls.return_value
        mock_siemplify.get_configuration.return_value = {
            "Api Root": "https://test.sentinelone.net",
            "Username": "testuser",
            "Password": "testpass",
        }
        mock_siemplify.parameters = {
            "additional_data": json.dumps(
                {
                    "agent_id": "123456",
                    "file_path": "/tmp/target.exe",
                    "password": password,
                    "created_at": "2026-08-21T18:00:00Z",
                    "activities_seen": ["act-seen"],
                }
            )
        }

        mock_activities.return_value = [
            {"id": "act-seen", "data": {"downloadUrl": "/download/seen"}},
            {"id": "act-corrupt", "data": {"downloadUrl": "/download/corrupt"}},
            {"id": "act-good", "data": {"downloadUrl": "/download/good"}},
        ]

        def download_side_effect(url: str) -> bytes:
            if "corrupt" in url:
                return b"corrupted not a zip"
            return good_zip

        mock_download.side_effect = download_side_effect

        main(is_first_run=False)

        mock_siemplify.end.assert_called_once()
        msg, is_success, status = mock_siemplify.end.call_args[0]
        assert status == EXECUTION_STATE_COMPLETED
        assert is_success == "true"


class TestSentinelOneManagerAcquisitionMethods:
    @mock.patch.object(SentinelOneManager, "get_token", return_value="mock_token")
    def test_manager_fetch_files(self, mock_token):
        manager = SentinelOneManager(
            "https://test.sentinelone.net", "user", "pass"
        )
        with mock.patch.object(manager.session, "post") as mock_post:
            mock_post.return_value.json.return_value = {
                "data": {"success": True}
            }
            mock_post.return_value.status_code = 200

            res = manager.fetch_files("agent_1", "/tmp/file.txt", "Pass123!")
            assert res == {"success": True}
            mock_post.assert_called_once()
            assert (
                mock_post.call_args[0][0]
                == "https://test.sentinelone.net/web/api/v2.1/agents/agent_1/actions/fetch-files"
            )

    @mock.patch.object(SentinelOneManager, "get_token", return_value="mock_token")
    def test_manager_get_file_upload_activities(self, mock_token):
        manager = SentinelOneManager(
            "https://test.sentinelone.net", "user", "pass"
        )
        with mock.patch.object(manager.session, "get") as mock_get:
            mock_get.return_value.json.return_value = {
                "data": [{"id": 1, "data": {"downloadUrl": "/dl/1"}}]
            }
            mock_get.return_value.status_code = 200

            res = manager.get_file_upload_activities(
                "agent_1", created_at_gte="2026-08-21T00:00:00Z"
            )
            assert len(res) == 1
            assert res[0]["id"] == 1
            params = mock_get.call_args[1]["params"]
            assert params["activity_types"] == "80"
            assert params["agent_ids"] == "agent_1"
            assert params["createdAt__gte"] == "2026-08-21T00:00:00Z"

    @mock.patch.object(SentinelOneManager, "get_token", return_value="mock_token")
    def test_manager_download_file_by_url(self, mock_token):
        manager = SentinelOneManager(
            "https://test.sentinelone.net", "user", "pass"
        )
        with mock.patch.object(manager.session, "get") as mock_get:
            mock_get.return_value.content = b"zip_content_bytes"
            mock_get.return_value.status_code = 200

            content = manager.download_file_by_url("/download/act-1")
            assert content == b"zip_content_bytes"
            assert (
                mock_get.call_args[0][0]
                == "https://test.sentinelone.net/web/api/v2.1/download/act-1"
            )
