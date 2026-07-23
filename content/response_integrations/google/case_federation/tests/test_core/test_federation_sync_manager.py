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
from unittest.mock import MagicMock

import pytest

from ...core import FederationSyncManager as manager_module
from ...core.constants import SUCCESS_STATUS_CODE
from ...core.FederationSyncManager import (
    ApiClientParameters,
    FederationSyncManager,
)
from ..core.mocks import GetFederationCasesStub, MockHttpClient

SYNC_API_ROOT: str = "https://primary.example.com"


@pytest.fixture
def mock_http_client() -> MockHttpClient:
    return MockHttpClient()


@pytest.fixture
def federation_cases(monkeypatch: pytest.MonkeyPatch) -> GetFederationCasesStub:
    stub = GetFederationCasesStub()
    monkeypatch.setattr(manager_module, "get_federation_cases", stub)
    return stub


@pytest.fixture
def manager(
    monkeypatch: pytest.MonkeyPatch,
    mock_http_client: MockHttpClient,
) -> FederationSyncManager:
    monkeypatch.setattr(
        FederationSyncManager,
        "_get_credentials_using_p4sa",
        lambda self, verify_ssl: None,
    )
    monkeypatch.setattr(
        FederationSyncManager,
        "_prepare_http_client",
        lambda self: setattr(self, "http_client", mock_http_client),
    )
    return FederationSyncManager(
        session=MagicMock(),
        logger=MagicMock(),
        api_client_parameters=ApiClientParameters(sync_api_root=SYNC_API_ROOT),
        chronicle_soar=MagicMock(),
    )


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
        "continuationToken": "next-token",
        "executionMessage": "message",
    }
    mock_http_client.response.status_code = 200

    # Act
    result = manager.sync_cases_from(continuation_token="previous-token")

    # Assert - the fetch was made with the given continuation token
    assert federation_cases.calls[0]["continuation_token"] == "previous-token"

    # Assert - the sync request
    assert len(mock_http_client.requests) == 1
    request = mock_http_client.requests[0]
    assert request["method"] == "POST"
    assert request["url"] == (
        f"{SYNC_API_ROOT}/legacyFederatedCases:legacyBatchPatchFederatedCases"
    )
    payload = json.loads(request["data"])
    assert payload["cases"][0]["alertsSla"]["expirationStatus"] == "not_expired"
    assert payload["cases"][0]["caseSla"]["expirationStatus"] == "already_expired"

    # Assert - the result
    assert result.status_code == 200
    assert result.execution_data.continuation_token == "next-token"
    assert result.execution_data.execution_message == "message"


def test_legacy_response_keys_are_supported(
    manager: FederationSyncManager,
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
) -> None:
    # Arrange - response uses the legacy keys
    federation_cases.response.json.return_value = {
        "legacyFederatedCases": [{"id": 7}],
        "nextPageToken": "legacy-token",
    }
    mock_http_client.response.status_code = 200

    # Act
    result = manager.sync_cases_from(continuation_token=None)

    # Assert
    assert len(mock_http_client.requests) == 1
    payload = json.loads(mock_http_client.requests[0]["data"])
    assert payload["cases"] == [{"id": 7}]
    assert result.execution_data.continuation_token == "legacy-token"


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