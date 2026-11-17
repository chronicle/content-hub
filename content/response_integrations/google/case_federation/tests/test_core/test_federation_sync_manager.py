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

from unittest.mock import MagicMock

import pytest
import requests
from google.auth.exceptions import RefreshError, TransportError

from ...core import auth as auth_module
from ...core import federation_sync_manager as manager_module
from ...core.constants import (
    CLIENT_ADDRESS_ENV_VAR,
    CREDENTIALS_REFRESH_ERROR_MESSAGE,
    REMOTE_PLATFORM_BACKSTORY_REDIRECT_HEADER,
    SUCCESS_STATUS_CODE,
    SYNC_REQUEST_ERROR_MESSAGE,
)
from ...core.exceptions import CaseFederationError
from ...core.federation_sync_manager import ApiClientParameters, FederationSyncManager
from ..core.mocks import GetFederationCasesStub, MockHttpClient, PatchFederationCasesStub

SYNC_API_ROOT: str = "https://primary.example.com"
SECONDARY_CLIENT_ADDRESS: str = "https://secondary.backstory.chronicle.security"
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
    monkeypatch.setenv(CLIENT_ADDRESS_ENV_VAR, SECONDARY_CLIENT_ADDRESS)
    monkeypatch.setattr(manager_module, "create_p4sa_authorized_session", lambda *_args, **_kwargs: mock_http_client)
    return FederationSyncManager(
        logger=MagicMock(),
        api_client_parameters=ApiClientParameters(sync_api_root=SYNC_API_ROOT, verify_ssl=True),
        chronicle_soar=MagicMock(),
    )


def test_init_creates_p4sa_authorized_session_when_api_key_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    mock_session = MagicMock()
    mock_create_session = MagicMock(return_value=mock_session)
    mock_soar = MagicMock()
    monkeypatch.setattr(manager_module, "create_p4sa_authorized_session", mock_create_session)

    # Act
    sync_manager = FederationSyncManager(
        logger=MagicMock(),
        api_client_parameters=ApiClientParameters(sync_api_root=SYNC_API_ROOT, verify_ssl=False),
        chronicle_soar=mock_soar,
    )

    # Assert
    mock_create_session.assert_called_once_with(mock_soar, verify_ssl=False)
    assert sync_manager.http_client is mock_session


def test_no_cases_returns_success_without_sync_request(
    manager: FederationSyncManager,
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
) -> None:
    # Arrange
    federation_cases.response.json.return_value = {"cases": [], "continuationToken": None}

    # Act
    result = manager.sync_cases_from(continuation_token=None)

    # Assert
    assert result.status_code == SUCCESS_STATUS_CODE
    assert result.execution_data.continuation_token is None
    assert result.cases_payload is None
    assert result.response_text is None
    assert not mock_http_client.requests


def test_null_cases_in_response_falls_back_safely(
    manager: FederationSyncManager,
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
) -> None:
    # Arrange
    federation_cases.response.json.return_value = {
        "cases": None,
        "legacyFederatedCases": None,
        "continuationToken": None,
        "nextPageToken": None,
        "executionMessage": None,
    }

    # Act
    result = manager.sync_cases_from(continuation_token=None)

    # Assert
    assert result.status_code == SUCCESS_STATUS_CODE
    assert result.execution_data.continuation_token is None
    assert result.execution_data.execution_message == "No additional execution details available."
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
    assert request["headers"] == {REMOTE_PLATFORM_BACKSTORY_REDIRECT_HEADER: SECONDARY_CLIENT_ADDRESS}
    assert "data" not in request
    payload = request["json"]
    assert payload["cases"][0]["alertsSla"]["expirationStatus"] == "not_expired"
    assert payload["cases"][0]["caseSla"]["expirationStatus"] == "already_expired"

    # Assert - the result
    assert result.status_code == 200
    assert result.execution_data.continuation_token == DEFAULT_NEXT_CONTINUATION
    assert result.execution_data.execution_message == "message"
    assert result.cases_payload == payload["cases"]


def test_sync_without_client_address_raises_error(
    manager: FederationSyncManager,
    federation_cases: GetFederationCasesStub,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.delenv(CLIENT_ADDRESS_ENV_VAR, raising=False)
    federation_cases.response.json.return_value = {"cases": [{"id": 1}], "continuationToken": DEFAULT_NEXT_CONTINUATION}

    # Act & Assert
    with pytest.raises(CaseFederationError):
        manager.sync_cases_from(continuation_token=None)


@pytest.mark.parametrize(
    ("error", "expected_message"),
    [
        (RefreshError("Permission 'iam.serviceAccounts.getAccessToken' denied"), CREDENTIALS_REFRESH_ERROR_MESSAGE),
        (TransportError("Unable to reach STS endpoint"), SYNC_REQUEST_ERROR_MESSAGE),
        (requests.ConnectionError("Connection refused"), SYNC_REQUEST_ERROR_MESSAGE),
    ],
)
def test_sync_request_failure_raises_case_federation_error(
    error: Exception,
    expected_message: str,
    manager: FederationSyncManager,
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
) -> None:
    # Arrange
    federation_cases.response.json.return_value = {"cases": [{"id": 1}], "continuationToken": DEFAULT_NEXT_CONTINUATION}
    mock_http_client.error = error

    # Act & Assert
    with pytest.raises(CaseFederationError, match=expected_message) as exc_info:
        manager.sync_cases_from(continuation_token=None)

    assert exc_info.value.__cause__ is error


def test_legacy_response_keys_are_supported(
    manager: FederationSyncManager,
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
) -> None:
    # Arrange - response uses the legacy keys (even if primary keys are null)
    federation_cases.response.json.return_value = {
        "cases": None,
        "legacyFederatedCases": [{"id": 7}],
        "continuationToken": None,
        "nextPageToken": DEFAULT_LEGACY_CONTINUATION,
    }
    mock_http_client.response.status_code = 200

    # Act
    result = manager.sync_cases_from(continuation_token=None)

    # Assert
    assert len(mock_http_client.requests) == 1
    payload = mock_http_client.requests[0]["json"]
    assert payload["cases"] == [{"id": 7}]
    assert result.execution_data.continuation_token == DEFAULT_LEGACY_CONTINUATION


def test_failed_sync_propagates_status_code_and_response_text(
    manager: FederationSyncManager,
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
) -> None:
    # Arrange
    federation_cases.response.json.return_value = {"cases": [{"id": 1}], "continuationToken": "token"}
    mock_http_client.response.status_code = 503
    mock_http_client.response.text = "Service Unavailable"

    # Act
    result = manager.sync_cases_from(continuation_token=None)

    # Assert
    assert result.status_code == 503
    assert result.cases_payload == [{"id": 1}]
    assert result.response_text == "Service Unavailable"


def test_legacy_api_key_sync_uses_patch_federation_cases_without_p4sa(
    monkeypatch: pytest.MonkeyPatch,
    federation_cases: GetFederationCasesStub,
) -> None:
    # Arrange
    patch_stub = PatchFederationCasesStub()
    mock_get_creds = MagicMock()
    mock_soar = MagicMock()
    monkeypatch.setattr(manager_module, "patch_federation_cases", patch_stub)
    monkeypatch.setattr(auth_module, "get_secops_siem_tenant_credentials", mock_get_creds)

    cases = [
        {"id": 42, "alertsSla": {"expirationStatus": "notExpired"}, "caseSla": {"expirationStatus": "alreadyExpired"}},
    ]
    federation_cases.response.json.return_value = {
        "cases": cases,
        "continuationToken": DEFAULT_NEXT_CONTINUATION,
        "executionMessage": "message",
    }

    sync_manager = FederationSyncManager(
        logger=MagicMock(),
        api_client_parameters=ApiClientParameters(
            sync_api_root="https://primary.example.com/api",
            api_key="secret-api-key",
        ),
        chronicle_soar=mock_soar,
    )

    # Act
    result = sync_manager.sync_cases_from(continuation_token=DEFAULT_PREVIOUS_CONTINUATION)

    # Assert
    mock_get_creds.assert_not_called()
    assert sync_manager.http_client is None
    assert len(patch_stub.calls) == 1
    assert patch_stub.calls[0] == {
        "chronicle_soar": mock_soar,
        "cases_payload": cases,
        "api_root": "https://primary.example.com/api",
        "api_key": "secret-api-key",
    }
    assert cases[0]["alertsSla"]["expirationStatus"] == "notExpired"
    assert cases[0]["caseSla"]["expirationStatus"] == "alreadyExpired"
    assert result.status_code == 200
    assert result.execution_data.continuation_token == DEFAULT_NEXT_CONTINUATION
