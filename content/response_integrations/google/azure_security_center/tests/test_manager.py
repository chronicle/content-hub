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

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from ..core import consts
from ..core.AzureSecurityCenterManager import AzureSecurityCenterManager

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def mock_requests_session() -> Generator[MagicMock, None, None]:
    """Fixture providing a mocked requests session."""
    with patch("azure_security_center.core.AzureSecurityCenterManager.requests.session") as mock_session_cls:
        session_instance = MagicMock()
        mock_session_cls.return_value = session_instance
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "mock_access_token",
            "refresh_token": "mock_new_refresh_token",
        }
        mock_response.status_code = 200
        mock_response.ok = True
        mock_session_instance_post = MagicMock(return_value=mock_response)
        session_instance.post = mock_session_instance_post
        yield session_instance


def test_manager_default_endpoints(mock_requests_session: MagicMock) -> None:
    """Test AzureSecurityCenterManager initializes with default endpoints."""
    manager = AzureSecurityCenterManager(
        client_id="test_client_id",
        client_secret="test_client_secret",  # ruff: ignore[hardcoded-password-func-arg]
        username="test_user",
        password="test_password",  # ruff: ignore[hardcoded-password-func-arg]
        tenant_id="test_tenant_id",
        subscription_id="test_sub_id",
    )
    assert manager.login_api_root == consts.DEFAULT_LOGIN_API_ROOT
    assert manager.api_root == consts.DEFAULT_API_ROOT
    assert manager.graph_api_root == consts.DEFAULT_GRAPH_API_ROOT


def test_manager_custom_endpoints(mock_requests_session: MagicMock) -> None:
    """Test AzureSecurityCenterManager formats URLs with custom sovereign endpoints."""
    manager = AzureSecurityCenterManager(
        client_id="test_client_id",
        client_secret="test_client_secret",  # ruff: ignore[hardcoded-password-func-arg]
        username="test_user",
        password="test_password",  # ruff: ignore[hardcoded-password-func-arg]
        tenant_id="test_tenant_id",
        subscription_id="test_sub_id",
        login_api_root="https://login.microsoftonline.us/",
        api_root="https://management.usgovcloudapi.net/",
        graph_api_root="https://graph.microsoft.us/",
    )
    assert manager.login_api_root == "https://login.microsoftonline.us"
    assert manager.api_root == "https://management.usgovcloudapi.net"
    assert manager.graph_api_root == "https://graph.microsoft.us"

    url = manager._get_full_url("ping")
    assert url == "https://management.usgovcloudapi.net/providers/Microsoft.Security/operations"

    auth_endpoint_url = manager._get_full_url("get-auth-token", tenant_id="test_tenant")
    assert auth_endpoint_url == "https://login.microsoftonline.us/test_tenant/oauth2/v2.0/token"

    url_graph = manager._get_full_url("get-alert-ids")
    assert url_graph == "https://graph.microsoft.us/v1.0/security/alerts"


def test_manager_obtain_refresh_token_custom_login_api_root() -> None:
    """Test obtain_refresh_token posts to the custom login_api_root."""
    with patch("azure_security_center.core.AzureSecurityCenterManager.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "token123",
            "refresh_token": "refreshtoken123",
        }
        mock_post.return_value = mock_response

        res = AzureSecurityCenterManager.obtain_refresh_token(
            client_id="cid",
            client_secret="csec",  # ruff: ignore[hardcoded-password-func-arg]
            redirect_uri="https://redirect",
            code="code123",
            tenant_id="tid",
            verify_ssl=False,
            login_api_root="https://login.microsoftonline.us/",
        )
        assert res["refresh_token"] == "refreshtoken123"  # ruff: ignore[hardcoded-password-string]
        mock_post.assert_called_once_with(
            "https://login.microsoftonline.us/tid/oauth2/token",
            data={
                "code": "code123",
                "client_id": "cid",
                "client_secret": "csec",
                "redirect_uri": "https://redirect",
                "grant_type": "authorization_code",
            },
            verify=False,
        )


def test_manager_get_access_token_custom_login_api_root(mock_requests_session: MagicMock) -> None:
    """Test get_access_token uses custom login_api_root."""
    manager = AzureSecurityCenterManager(
        client_id="test_client_id",
        client_secret="test_client_secret",  # ruff: ignore[hardcoded-password-func-arg]
        username="test_user",
        password="test_password",  # ruff: ignore[hardcoded-password-func-arg]
        tenant_id="test_tenant_id",
        subscription_id="test_sub_id",
        refresh_token="initial_refresh_token",  # ruff: ignore[hardcoded-password-func-arg]
        login_api_root="https://login.microsoftonline.us/",
    )
    mock_requests_session.post.assert_called_with(
        "https://login.microsoftonline.us/test_tenant_id/oauth2/token",
        data={
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "grant_type": "refresh_token",
            "refresh_token": "initial_refresh_token",
        },
    )
    assert manager.auth_token == "mock_access_token"  # ruff: ignore[hardcoded-password-string]
