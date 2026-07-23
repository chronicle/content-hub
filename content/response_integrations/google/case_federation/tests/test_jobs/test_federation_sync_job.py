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

import pytest
from integration_testing.set_meta import set_metadata

from ...core.exceptions import MissingParameterError
from ...jobs import FederationSyncJob
from ..common import CONFIG_PATH
from ..core.mocks import GetFederationCasesStub, MockHttpClient

TARGET_PLATFORM: str = "primary.example.com"
DEFAULT_PARAMETERS: dict[str, str] = {"Target Platform": TARGET_PLATFORM}
SYNC_URL: str = (
    f"https://{TARGET_PLATFORM}/legacyFederatedCases:legacyBatchPatchFederatedCases"
)


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={"Target Platform": ""},
)
def test_missing_target_platform_fails(
    federation_cases: GetFederationCasesStub,
) -> None:
    with pytest.raises((MissingParameterError, SystemExit)):
        FederationSyncJob.main()

    # No fetch should have been attempted
    assert not federation_cases.calls


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_first_run_without_cases_does_not_save_execution_data(
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
    job_context: dict,
) -> None:
    # Arrange
    federation_cases.response.json.return_value = {
        "cases": [],
        "continuationToken": None,
    }

    # Act
    FederationSyncJob.main()

    # Assert
    assert len(federation_cases.calls) == 1
    assert federation_cases.calls[0]["continuation_token"] is None
    assert not mock_http_client.requests  # nothing to sync
    assert not job_context  # previous execution data is kept (none)


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_sync_success_sends_cases_and_saves_execution_data(
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
    job_context: dict,
) -> None:
    # Arrange
    federation_cases.response.json.return_value = {
        "cases": [
            {
                "id": 1,
                "alertsSla": {"expirationStatus": "notExpired"},
                "caseSla": {"expirationStatus": "alreadyExpired"},
            },
        ],
        "continuationToken": "token-123",
        "executionMessage": "Synced up to case 1",
    }
    mock_http_client.response.status_code = 200

    # Act
    FederationSyncJob.main()

    # Assert - sync request
    assert len(mock_http_client.requests) == 1
    request = mock_http_client.requests[0]
    assert request["method"] == "POST"
    assert request["url"] == SYNC_URL

    payload = json.loads(request["data"])
    synced_case = payload["cases"][0]
    assert synced_case["alertsSla"]["expirationStatus"] == "not_expired"
    assert synced_case["caseSla"]["expirationStatus"] == "already_expired"

    # Assert - execution data was saved
    saved_values = [json.loads(value) for value in job_context.values()]
    assert len(saved_values) == 1
    assert saved_values[0]["continuation_token"] == "token-123"
    assert saved_values[0]["execution_message"] == "Synced up to case 1"


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_sync_failure_does_not_save_execution_data(
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
    job_context: dict,
) -> None:
    # Arrange
    federation_cases.response.json.return_value = {
        "cases": [{"id": 1}],
        "continuationToken": "token-123",
    }
    mock_http_client.response.status_code = 500

    # Act
    FederationSyncJob.main()

    # Assert
    assert len(mock_http_client.requests) == 1  # sync was attempted
    assert not job_context  # previous execution data is kept


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_continuation_token_is_reused_on_next_run(
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
) -> None:
    # Arrange - first run returns a case and a continuation token
    federation_cases.response.json.return_value = {
        "cases": [{"id": 1}],
        "continuationToken": "token-123",
    }
    mock_http_client.response.status_code = 200

    # Act - two consecutive job executions
    FederationSyncJob.main()
    FederationSyncJob.main()

    # Assert - the second run fetched with the saved continuation token
    assert len(federation_cases.calls) == 2
    assert federation_cases.calls[0]["continuation_token"] is None
    assert federation_cases.calls[1]["continuation_token"] == "token-123"