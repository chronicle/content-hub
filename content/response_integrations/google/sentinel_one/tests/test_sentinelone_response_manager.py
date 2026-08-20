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
import pytest
from unittest.mock import MagicMock, patch
import requests

from ..core.SentinelOneResponseManager import SentinelOneResponseManager
from ..core.exceptions import (
    SentinelOneConnectivityError,
    SentinelOneNotFoundError,
)
from ..core.datamodels import Agent

API_ROOT = "https://usea1-partners.sentinelone.net"
API_TOKEN = "test-token-123"


@pytest.fixture
def manager():
    return SentinelOneResponseManager(
        api_root=API_ROOT,
        api_token=API_TOKEN,
        verify_ssl=True,
    )


class TestSentinelOneResponseManagerInit:
    def test_init_with_token(self):
        mgr = SentinelOneResponseManager(API_ROOT, api_token="tok123")
        assert mgr.api_root == API_ROOT
        assert mgr.session.headers["Authorization"] == "ApiToken tok123"

    def test_init_with_token_with_prefix(self):
        mgr = SentinelOneResponseManager(API_ROOT, api_token="ApiToken tok123")
        assert mgr.session.headers["Authorization"] == "ApiToken tok123"

    def test_init_trailing_slash_stripped(self):
        mgr = SentinelOneResponseManager(f"{API_ROOT}/", api_token="tok123")
        assert mgr.api_root == API_ROOT

    def test_get_full_url(self, manager):
        assert manager.get_full_url("agents") == f"{API_ROOT}/web/api/v2.1/agents"
        assert manager.get_full_url("/activities") == f"{API_ROOT}/web/api/v2.1/activities"


class TestContainmentMethods:
    def test_disconnect_agent_success(self, manager):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"data": {"affected": 1}}
        with patch.object(manager.session, "post", return_value=mock_resp) as mock_post:
            result = manager.disconnect_agent_from_network("12345")
            assert result is True
            mock_post.assert_called_once_with(
                f"{API_ROOT}/web/api/v2.1/agents/12345/actions/disconnect",
                json={"data": {}},
            )

    def test_disconnect_agent_404(self, manager):
        mock_resp = MagicMock(status_code=404, text="Not Found")
        mock_resp.json.return_value = {"errors": [{"detail": "Agent not found"}]}
        with patch.object(manager.session, "post", return_value=mock_resp):
            with pytest.raises(SentinelOneNotFoundError):
                manager.disconnect_agent_from_network("99999")

    def test_connect_agent_success(self, manager):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"data": {"affected": 1}}
        with patch.object(manager.session, "post", return_value=mock_resp) as mock_post:
            result = manager.connect_agent_to_network("12345")
            assert result is True
            mock_post.assert_called_once_with(
                f"{API_ROOT}/web/api/v2.1/agents/12345/actions/connect",
                json={"data": {}},
            )

    def test_connect_agent_404(self, manager):
        mock_resp = MagicMock(status_code=404, text="Not Found")
        mock_resp.json.return_value = {"errors": [{"detail": "Agent not found"}]}
        with patch.object(manager.session, "post", return_value=mock_resp):
            with pytest.raises(SentinelOneNotFoundError):
                manager.connect_agent_to_network("99999")


class TestAgentLookup:
    def test_get_agent_by_uuid_success(self, manager):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "12345",
                    "uuid": "test-uuid",
                    "networkStatus": "connected",
                    "computerName": "DESKTOP-TEST",
                    "lastActiveDate": "2026-08-20T12:00:00Z",
                    "osType": "windows",
                }
            ]
        }
        with patch.object(manager.session, "get", return_value=mock_resp):
            agent = manager.get_agent_by_uuid("test-uuid")
            assert isinstance(agent, Agent)
            assert agent.id == "12345"
            assert agent.uuid == "test-uuid"
            assert agent.network_status == "connected"
            assert agent.computer_name == "DESKTOP-TEST"

    def test_get_agent_by_uuid_not_found_empty_data(self, manager):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"data": []}
        with patch.object(manager.session, "get", return_value=mock_resp):
            with pytest.raises(SentinelOneNotFoundError):
                manager.get_agent_by_uuid("nonexistent-uuid")


class TestContainmentStatusMapping:
    def test_containment_status_mappings(self, manager):
        assert manager.get_containment_status("disconnected") == "contained"
        assert manager.get_containment_status("disconnecting") == "containment_requested"
        assert manager.get_containment_status("connecting") == "uncontainment_requested"
        assert manager.get_containment_status("connected") == "uncontained"
        assert manager.get_containment_status(None) == "unknown"
        assert manager.get_containment_status("") == "unknown"
        assert manager.get_containment_status("custom_status") == "custom_status"


class TestFileAcquisitionMethods:
    def test_initiate_fetch_files_success(self, manager):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"data": {"affected": 1}}
        with patch.object(manager.session, "post", return_value=mock_resp) as mock_post:
            result = manager.initiate_fetch_files("12345", "C:\\test.exe", "Pass!123")
            assert result == {"affected": 1}
            mock_post.assert_called_once_with(
                f"{API_ROOT}/web/api/v2.1/agents/12345/actions/fetch-files",
                json={"data": {"files": ["C:\\test.exe"], "password": "Pass!123"}},
            )

    def test_get_file_upload_activities_success(self, manager):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "act-1",
                    "activityType": 80,
                    "data": {"downloadUrl": "web/api/v2.1/download/1"},
                }
            ]
        }
        with patch.object(manager.session, "get", return_value=mock_resp) as mock_get:
            result = manager.get_file_upload_activities("12345", "2026-08-20T00:00:00Z")
            assert len(result) == 1
            assert result[0]["id"] == "act-1"
            mock_get.assert_called_once_with(
                f"{API_ROOT}/web/api/v2.1/activities",
                params={
                    "createdAt__gte": "2026-08-20T00:00:00Z",
                    "agent_ids": "12345",
                    "activity_types": 80,
                    "sortBy": "createdAt",
                    "sortOrder": "desc",
                },
            )

    def test_download_file_relative_url(self, manager):
        mock_resp = MagicMock(status_code=200)
        with patch.object(manager.session, "get", return_value=mock_resp) as mock_get:
            resp = manager.download_file("download/1")
            assert resp == mock_resp
            mock_get.assert_called_once_with(
                f"{API_ROOT}/web/api/v2.1/download/1",
                stream=True,
            )

    def test_download_file_absolute_url(self, manager):
        mock_resp = MagicMock(status_code=200)
        with patch.object(manager.session, "get", return_value=mock_resp) as mock_get:
            resp = manager.download_file("https://s3.amazonaws.com/sentinelone/pkg.zip")
            assert resp == mock_resp
            mock_get.assert_called_once_with(
                "https://s3.amazonaws.com/sentinelone/pkg.zip",
                stream=True,
            )

    def test_fetch_token_success(self):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"token": "retrieved-token-456"}
        with patch("requests.Session.post", return_value=mock_resp):
            mgr = SentinelOneResponseManager(
                API_ROOT, username="admin@corp.com", password="SecurePassword123"
            )
            assert mgr.session.headers["Authorization"] == "ApiToken retrieved-token-456"

    def test_fetch_token_failure(self):
        mock_resp = MagicMock(status_code=401, text="Unauthorized")
        mock_resp.json.return_value = {"errors": [{"detail": "Invalid credentials"}]}
        with patch("requests.Session.post", return_value=mock_resp):
            with pytest.raises(SentinelOneConnectivityError):
                SentinelOneResponseManager(
                    API_ROOT, username="admin@corp.com", password="BadPassword"
                )

    def test_validate_response_error_formats(self, manager):
        # Format 1: errors list with details
        resp1 = MagicMock(status_code=500, text="Internal Error")
        resp1.json.return_value = {"errors": [{"detail": "Custom server error"}]}
        with pytest.raises(SentinelOneConnectivityError) as exc1:
            manager.validate_response(resp1)
        assert "Custom server error" in str(exc1.value)

        # Format 2: message key
        resp2 = MagicMock(status_code=400, text="Bad Request")
        resp2.json.return_value = {"message": "Invalid query parameters"}
        with pytest.raises(SentinelOneConnectivityError) as exc2:
            manager.validate_response(resp2)
        assert "Invalid query parameters" in str(exc2.value)

        # Format 3: detail key
        resp3 = MagicMock(status_code=403, text="Forbidden")
        resp3.json.return_value = {"detail": "Insufficient permissions"}
        with pytest.raises(SentinelOneConnectivityError) as exc3:
            manager.validate_response(resp3)
        assert "Insufficient permissions" in str(exc3.value)
