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
import io
import json
import pytest
from unittest.mock import MagicMock, patch
import zipfile

from ..actions import AcquireFile
from ..core.datamodels import Agent
from ..core.exceptions import (
    SentinelOneNotFoundError,
    SentinelOneTimeoutException,
)

EXECUTION_STATE_COMPLETED = 0
EXECUTION_STATE_FAILED = 1
EXECUTION_STATE_INPROGRESS = 2
EXECUTION_STATE_TIMEDOUT = 3


@pytest.fixture
def mock_siemplify():
    siemplify = MagicMock()
    siemplify.script_name = "Acquire File"
    siemplify.execution_deadline_unix_time_ms = 9999999999999
    siemplify.target_entities = []
    siemplify.parameters = {}
    siemplify.result = MagicMock()
    siemplify.LOGGER = MagicMock()
    return siemplify


def create_mock_zip(files_dict, password=None):
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        if password:
            zf.setpassword(password.encode("utf-8"))
        for fname, content in files_dict.items():
            zf.writestr(fname, content)
    return bio.getvalue()


class TestAcquireFileAction:
    def test_first_run_initiate_success(self, mock_siemplify):
        mock_mgr = MagicMock()
        agent = Agent(id="12345", uuid="uuid-123", network_status="connected", computer_name="HOST1")
        mock_mgr.get_agent_by_uuid.return_value = agent
        mock_mgr.initiate_fetch_files.return_value = {"activityId": "act-1"}

        def mock_extract(siemplify, param_name, **kwargs):
            return {
                "Fail If Timeout": False,
                "Agent ID": "12345",
                "Agent UUID": None,
                "File Path": "C:\\Windows\\System32\\calc.exe",
                "Password": "MySecretPassword123!",
            }.get(param_name, kwargs.get("default_value"))

        with patch.object(AcquireFile, "SiemplifyAction", return_value=mock_siemplify), \
             patch.object(AcquireFile, "get_manager", return_value=mock_mgr), \
             patch.object(AcquireFile, "extract_action_param", side_effect=mock_extract), \
             patch.object(AcquireFile, "extract_configuration_param"):

            AcquireFile.main(is_first_run=True)

        mock_mgr.initiate_fetch_files.assert_called_once_with(
            "12345", "C:\\Windows\\System32\\calc.exe", "MySecretPassword123!"
        )
        mock_siemplify.end.assert_called_once()
        args = mock_siemplify.end.call_args[0]
        assert "File acquisition initiated" in args[0]
        assert args[2] == EXECUTION_STATE_INPROGRESS

    def test_polling_run_completed_file_downloaded(self, mock_siemplify):
        mock_mgr = MagicMock()
        mock_siemplify.parameters = {
            "additional_data": json.dumps(
                {
                    "agent_id": "12345",
                    "file_path": "C:\\test.txt",
                    "password": "pass",
                    "created_at": "2026-08-20T00:00:00Z",
                    "activities_seen": [],
                }
            )
        }

        def mock_extract(siemplify, param_name, **kwargs):
            return {
                "Fail If Timeout": False,
            }.get(param_name, kwargs.get("default_value"))

        mock_mgr.get_file_upload_activities.return_value = [
            {"id": "act-80", "data": {"downloadUrl": "download/1"}}
        ]

        manifest = [{"path": "C:\\test.txt", "included": True, "size": 11}]
        zip_bytes = create_mock_zip(
            {"manifest.json": json.dumps(manifest).encode("utf-8"), "test.txt": b"hello world"}
        )

        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = [zip_bytes]
        mock_resp.content = zip_bytes
        mock_mgr.download_file.return_value = mock_resp

        with patch.object(AcquireFile, "SiemplifyAction", return_value=mock_siemplify), \
             patch.object(AcquireFile, "get_manager", return_value=mock_mgr), \
             patch.object(AcquireFile, "extract_action_param", side_effect=mock_extract), \
             patch.object(AcquireFile, "extract_configuration_param"):

            AcquireFile.main(is_first_run=False)

        mock_siemplify.end.assert_called_once()
        args = mock_siemplify.end.call_args[0]
        assert "Successfully acquired file" in args[0]
        assert args[1] is True
        assert args[2] == EXECUTION_STATE_COMPLETED

    def test_first_run_invalid_path_error(self, mock_siemplify):
        def mock_extract(siemplify, param_name, **kwargs):
            return {
                "Fail If Timeout": False,
                "Agent ID": "12345",
                "Agent UUID": None,
                "File Path": "relative/path/test.txt",
                "Password": None,
            }.get(param_name, kwargs.get("default_value"))

        with patch.object(AcquireFile, "SiemplifyAction", return_value=mock_siemplify), \
             patch.object(AcquireFile, "get_manager"), \
             patch.object(AcquireFile, "extract_action_param", side_effect=mock_extract), \
             patch.object(AcquireFile, "extract_configuration_param"):

            AcquireFile.main(is_first_run=True)

        mock_siemplify.end.assert_called_once()
        args = mock_siemplify.end.call_args[0]
        assert "not a valid absolute path" in args[0]
        assert args[1] is False
        assert args[2] == EXECUTION_STATE_FAILED

    def test_first_run_agent_not_found(self, mock_siemplify):
        mock_mgr = MagicMock()
        mock_mgr.get_agent_by_uuid.side_effect = SentinelOneNotFoundError("Not found")

        def mock_extract(siemplify, param_name, **kwargs):
            return {
                "Fail If Timeout": False,
                "Agent ID": "nonexistent-uuid",
                "Agent UUID": None,
                "File Path": "C:\\test.txt",
                "Password": "pass",
            }.get(param_name, kwargs.get("default_value"))

        with patch.object(AcquireFile, "SiemplifyAction", return_value=mock_siemplify), \
             patch.object(AcquireFile, "get_manager", return_value=mock_mgr), \
             patch.object(AcquireFile, "extract_action_param", side_effect=mock_extract), \
             patch.object(AcquireFile, "extract_configuration_param"):

            AcquireFile.main(is_first_run=True)

        mock_siemplify.end.assert_called_once()
        args = mock_siemplify.end.call_args[0]
        assert "Could not find endpoint" in args[0]
        assert args[1] is False
        assert args[2] == EXECUTION_STATE_FAILED

    def test_polling_run_still_in_progress(self, mock_siemplify):
        mock_mgr = MagicMock()
        mock_siemplify.parameters = {
            "additional_data": json.dumps(
                {
                    "agent_id": "12345",
                    "file_path": "C:\\test.txt",
                    "password": "pass",
                    "created_at": "2026-08-20T00:00:00Z",
                    "activities_seen": [],
                }
            )
        }

        def mock_extract(siemplify, param_name, **kwargs):
            return {"Fail If Timeout": False}.get(param_name, kwargs.get("default_value"))

        mock_mgr.get_file_upload_activities.return_value = []

        with patch.object(AcquireFile, "SiemplifyAction", return_value=mock_siemplify), \
             patch.object(AcquireFile, "get_manager", return_value=mock_mgr), \
             patch.object(AcquireFile, "extract_action_param", side_effect=mock_extract), \
             patch.object(AcquireFile, "extract_configuration_param"):

            AcquireFile.main(is_first_run=False)

        mock_siemplify.end.assert_called_once()
        args = mock_siemplify.end.call_args[0]
        assert "Waiting for file acquisition package" in args[0]
        assert args[2] == EXECUTION_STATE_INPROGRESS

    def test_polling_run_file_not_included(self, mock_siemplify):
        mock_mgr = MagicMock()
        mock_siemplify.parameters = {
            "additional_data": json.dumps(
                {
                    "agent_id": "12345",
                    "file_path": "C:\\test.txt",
                    "password": "pass",
                    "created_at": "2026-08-20T00:00:00Z",
                    "activities_seen": [],
                }
            )
        }

        def mock_extract(siemplify, param_name, **kwargs):
            return {"Fail If Timeout": False}.get(param_name, kwargs.get("default_value"))

        mock_mgr.get_file_upload_activities.return_value = [
            {"id": "act-80", "data": {"downloadUrl": "download/1"}}
        ]

        manifest = [{"path": "C:\\test.txt", "included": False, "reason": "File not found on disk"}]
        zip_bytes = create_mock_zip(
            {"manifest.json": json.dumps(manifest).encode("utf-8")}
        )

        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = [zip_bytes]
        mock_resp.content = zip_bytes
        mock_mgr.download_file.return_value = mock_resp

        with patch.object(AcquireFile, "SiemplifyAction", return_value=mock_siemplify), \
             patch.object(AcquireFile, "get_manager", return_value=mock_mgr), \
             patch.object(AcquireFile, "extract_action_param", side_effect=mock_extract), \
             patch.object(AcquireFile, "extract_configuration_param"):

            AcquireFile.main(is_first_run=False)

        mock_siemplify.end.assert_called_once()
        args = mock_siemplify.end.call_args[0]
        assert "Failed to acquire file" in args[0]
        assert args[1] is False
        assert args[2] == EXECUTION_STATE_FAILED
