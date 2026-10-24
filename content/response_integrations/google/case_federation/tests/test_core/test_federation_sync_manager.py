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

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from ...core import federation_sync_manager as manager_module
from ...core.constants import SUCCESS_STATUS_CODE
from ...core.federation_sync_manager import (
    ApiClientParameters,
    FederationSyncManager,
)
from ..core.mocks import GetFederationCasesStub, MockHttpClient

if TYPE_CHECKING:
    import requests

SYNC_API_ROOT: str = "https://primary.example.com"
DEFAULT_LEGACY_CONTINUATION: str = "blabla1"
DEFAULT_NEXT_CONTINUATION: str = "blabla2"
DEFAULT_PREVIOUS_CONTINUATION: str = "blabla3"


@pytest.fixture
def mock_http_client() -> MockHttpClient:
    return MockHttpClient()


@pytest.fixture
def federation_cases(monkeypatch: pytest.MonkeyPatch) -> GetFederationCasesStub:
    stub = GetFederationCasesStub()
    monkeypatch.setattr(manager_module, "get_federation_cases", stub)
    return stub


@pytest.fixture
def manager(monkeypatch: pytest.MonkeyPatch, mock_http_client: MockHttpClient) -> FederationSyncManager:
    monkeypatch.setattr(FederationSyncManager, "_get_credentials_using_p4sa", lambda self: None)
    monkeypatch.setattr(
        FederationSyncManager,
        "_prepare_http_client",
        lambda self: setattr(self, "http_client", mock_http_client),
    )
    return FederationSyncManager(
        session=MagicMock(),
        logger=MagicMock(),
        api_client_parameters=ApiClientParameters(sync_api_root=SYNC_API_ROOT, verify_ssl=True),
        chronicle_soar=MagicMock(),
    )


def test_get_credentials_using_p4sa(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    mock_creds = MagicMock()
    mock_get_creds = MagicMock(return_value=mock_creds)
    mock_soar = MagicMock()
    monkeypatch.setenv("GCP_PROJECT_ID", "test-gcp-project")
    monkeypatch.setattr(manager_module, "get_secops_siem_tenant_credentials", mock_get_creds)
    monkeypatch.setattr(FederationSyncManager, "_prepare_http_client", lambda self: None)

    # Act
    sync_manager = FederationSyncManager(
        session=MagicMock(),
        logger=MagicMock(),
        api_client_parameters=ApiClientParameters(sync_api_root=SYNC_API_ROOT, verify_ssl=True),
        chronicle_soar=mock_soar,
    )

    # Assert
    mock_get_creds.assert_called_once_with(
        chronicle_soar=mock_soar,
        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
        quota_project_id="test-gcp-project",
    )
    assert sync_manager.creds is mock_creds


def test_prepare_http_client(monkeypatch: pytest.MonkeyPatch, script_session: requests.Session) -> None:
    # Arrange
    mock_creds = MagicMock()
    monkeypatch.setattr(
        FederationSyncManager,
        "_get_credentials_using_p4sa",
        lambda self: setattr(self, "creds", mock_creds),
    )

    # Act
    sync_manager = FederationSyncManager(
        session=MagicMock(),
        logger=MagicMock(),
        api_client_parameters=ApiClientParameters(sync_api_root=SYNC_API_ROOT, verify_ssl=False),
        chronicle_soar=MagicMock(),
    )

    # Assert
    assert script_session.verify is False
    assert isinstance(sync_manager.http_client, manager_module.AuthorizedSession)
    assert sync_manager.http_client.credentials is mock_creds
    assert sync_manager.http_client.verify is False


def test_no_cases_returns_success_without_sync_request(
    manager: FederationSyncManager,
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
) -> None:
    # Arrange
    federation_cases.response.json.return_value = {
        "cases": [],
        "continuationToken": None,
    }

    # Act
    result = manager.sync_cases_from(continuation_token=None)

    # Assert
    assert result.status_code == SUCCESS_STATUS_CODE
    assert result.execution_data.continuation_token is None
    assert result.cases_payload is None
    assert not mock_http_client.requests


def test_sync_posts_cases_and_normalizes_sla_statuses(
    manager: FederationSyncManager,
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
) -> None:
    # Arrange
    federation_cases.response.json.return_value = {
        "cases": [
            {
                "id": 42,
                "alertsSla": {"expirationStatus": "notExpired"},
                "caseSla": {"expirationStatus": "alreadyExpired"},
            },
        ],
        "continuationToken": DEFAULT_NEXT_CONTINUATION,
        "executionMessage": "message",
    }
    mock_http_client.response.status_code = 200

    # Act
    result = manager.sync_cases_from(continuation_token=DEFAULT_PREVIOUS_CONTINUATION)

    # Assert - the fetch was made with the given continuation token
    assert federation_cases.calls[0]["continuation_token"] == DEFAULT_PREVIOUS_CONTINUATION

    # Assert - the sync request
    assert len(mock_http_client.requests) == 1
    request = mock_http_client.requests[0]
    assert request["method"] == "POST"
    assert request["url"] == f"{SYNC_API_ROOT}/legacyFederatedCases:legacyBatchPatchFederatedCases"
    payload = json.loads(request["data"])
    assert payload["cases"][0]["alertsSla"]["expirationStatus"] == "not_expired"
    assert payload["cases"][0]["caseSla"]["expirationStatus"] == "already_expired"

    # Assert - the result
    assert result.status_code == 200
    assert result.execution_data.continuation_token == DEFAULT_NEXT_CONTINUATION
    assert result.execution_data.execution_message == "message"
    assert result.cases_payload == payload["cases"]


def test_legacy_response_keys_are_supported(
    manager: FederationSyncManager,
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
) -> None:
    # Arrange - response uses the legacy keys
    federation_cases.response.json.return_value = {
        "legacyFederatedCases": [{"id": 7}],
        "nextPageToken": DEFAULT_LEGACY_CONTINUATION,
    }
    mock_http_client.response.status_code = 200

    # Act
    result = manager.sync_cases_from(continuation_token=None)

    # Assert
    assert len(mock_http_client.requests) == 1
    payload = json.loads(mock_http_client.requests[0]["data"])
    assert payload["cases"] == [{"id": 7}]
    assert result.execution_data.continuation_token == DEFAULT_LEGACY_CONTINUATION


def test_failed_sync_propagates_status_code(
    manager: FederationSyncManager,
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
) -> None:
    # Arrange
    federation_cases.response.json.return_value = {
        "cases": [{"id": 1}],
        "continuationToken": "token",
    }
    mock_http_client.response.status_code = 503

    # Act
    result = manager.sync_cases_from(continuation_token=None)

    # Assert
    assert result.status_code == 503
    assert result.cases_payload == [{"id": 1}]
