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

import pytest
from integration_testing.set_meta import set_metadata

from ...core.constants import FEDERATION_SYNC_JOB_SCRIPT_NAME, LAST_EXECUTION_DATA_KEY
from ...core.exceptions import InvalidParameterError, MissingParameterError
from ...jobs import federation_sync_job
from ..common import CONFIG_PATH

if TYPE_CHECKING:
    from ..core.mocks import GetFederationCasesStub, MockHttpClient, PatchFederationCasesStub

CHRONICLE_API_URL: str = "https://us-chronicle.googleapis.com/projects/p/locations/us/instances/i"
NORMALIZED_CHRONICLE_API_URL: str = "https://us-chronicle.googleapis.com/v1alpha/projects/p/locations/us/instances/i"
LEGACY_TARGET_PLATFORM: str = "primary.siemplify-soar.com"
LEGACY_API_KEY: str = "secret-api-key"
DEFAULT_PARAMETERS: dict[str, str] = {"Chronicle API URL": CHRONICLE_API_URL, "Verify SSL": "True"}
SYNC_URL: str = f"{NORMALIZED_CHRONICLE_API_URL}/legacyFederatedCases:legacyBatchPatchFederatedCases"
DEFAULT_CONTINUATION: str = "blabla"


@pytest.mark.parametrize(
    ("chronicle_api_url", "target_platform", "api_key"),
    [
        ("", "", ""),
        ("", LEGACY_TARGET_PLATFORM, ""),
        ("", "", LEGACY_API_KEY),
    ],
)
@set_metadata(integration_config_file_path=CONFIG_PATH, parameters={"Chronicle API URL": ""})
def test_missing_parameters_fails(
    chronicle_api_url: str,
    target_platform: str,
    api_key: str,
    federation_cases: GetFederationCasesStub,
) -> None:
    job = federation_sync_job.CaseFederationSyncJob(FEDERATION_SYNC_JOB_SCRIPT_NAME)
    job.params.chronicle_apiurl = chronicle_api_url
    job.params.target_platform = target_platform
    job.params.api_key = api_key

    with pytest.raises(MissingParameterError):
        job._validate_params()


@pytest.mark.parametrize(
    "invalid_url",
    [
        "primary.siemplify-soar.com",
        "https://primary.siemplify-soar.com",
        "https://us-chronicle.googleapis.com/projects/p",
        "https://us-chronicle.googleapis.com/projects/p/locations/us",
        "http://us-chronicle.googleapis.com/projects/p/locations/us/instances/i",
    ],
)
@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_invalid_chronicle_api_url_format_fails(invalid_url: str, federation_cases: GetFederationCasesStub) -> None:
    job = federation_sync_job.CaseFederationSyncJob(FEDERATION_SYNC_JOB_SCRIPT_NAME)
    job.params.chronicle_apiurl = invalid_url

    with pytest.raises(InvalidParameterError):
        job._validate_params()


@pytest.mark.parametrize(
    ("raw_url", "expected_root"),
    [
        (
            "https://us-chronicle.googleapis.com/projects/p/locations/us/instances/i",
            NORMALIZED_CHRONICLE_API_URL,
        ),
        (
            NORMALIZED_CHRONICLE_API_URL,
            NORMALIZED_CHRONICLE_API_URL,
        ),
        (
            f"{NORMALIZED_CHRONICLE_API_URL}/",
            NORMALIZED_CHRONICLE_API_URL,
        ),
        (
            "https://us-chronicle.googleapis.com/v1/projects/p/locations/us/instances/i",
            NORMALIZED_CHRONICLE_API_URL,
        ),
        (
            "https://us-chronicle.googleapis.com/v1beta/projects/p/locations/us/instances/i",
            NORMALIZED_CHRONICLE_API_URL,
        ),
    ],
)
def test_build_sync_api_root_normalizes_url(raw_url: str, expected_root: str) -> None:
    assert federation_sync_job.build_sync_api_root(raw_url) == expected_root


@pytest.mark.parametrize(
    "chronicle_api_url_param",
    [
        "https://us-chronicle.googleapis.com/projects/p/locations/us/instances/i",
        NORMALIZED_CHRONICLE_API_URL,
        f"{NORMALIZED_CHRONICLE_API_URL}/",
        "https://us-chronicle.googleapis.com/v1/projects/p/locations/us/instances/i",
        "https://us-chronicle.googleapis.com/v1beta/projects/p/locations/us/instances/i",
    ],
)
def test_chronicle_api_url_variants_send_to_normalized_sync_url(
    chronicle_api_url_param: str,
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
    job_context: dict[tuple[str, str], str],
) -> None:
    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Chronicle API URL": chronicle_api_url_param, "Verify SSL": "True"},
    )
    def run_job() -> None:
        federation_sync_job.main()

    federation_cases.response.json.return_value = {
        "cases": [{"id": 1}],
        "continuationToken": DEFAULT_CONTINUATION,
    }
    mock_http_client.response.status_code = 200

    run_job()

    assert len(mock_http_client.requests) == 1
    assert mock_http_client.requests[0]["url"] == SYNC_URL


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_first_run_without_cases_does_not_save_execution_data(
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
    job_context: dict[tuple[str, str], str],
) -> None:
    # Arrange
    federation_cases.response.json.return_value = {
        "cases": [],
        "continuationToken": None,
    }

    # Act
    federation_sync_job.main()

    # Assert
    assert len(federation_cases.calls) == 1
    assert federation_cases.calls[0]["continuation_token"] is None
    assert not mock_http_client.requests  # nothing to sync
    assert not job_context  # previous execution data is kept (none)


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_sync_success_sends_cases_and_saves_execution_data(
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
    job_context: dict[tuple[str, str], str],
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
        "continuationToken": DEFAULT_CONTINUATION,
        "executionMessage": "Synced up to case 1",
    }
    mock_http_client.response.status_code = 200

    # Act
    federation_sync_job.main()

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
    assert saved_values[0]["continuation_token"] == DEFAULT_CONTINUATION
    assert saved_values[0]["execution_message"] == "Synced up to case 1"


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_sync_failure_does_not_save_execution_data(
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
    job_context: dict[tuple[str, str], str],
) -> None:
    # Arrange
    federation_cases.response.json.return_value = {
        "cases": [{"id": 1}],
        "continuationToken": DEFAULT_CONTINUATION,
    }
    mock_http_client.response.status_code = 500

    # Act
    federation_sync_job.main()

    # Assert
    assert len(mock_http_client.requests) == 1  # sync was attempted
    assert LAST_EXECUTION_DATA_KEY not in {key for _, key in job_context}


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_first_failed_run_logs_cases_payload_once_and_suppresses_consecutive_failures(
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
    job_context: dict[tuple[str, str], str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Arrange
    federation_cases.response.json.return_value = {
        "cases": [{"id": 1}, {"id": 2}],
        "continuationToken": DEFAULT_CONTINUATION,
    }
    mock_http_client.response.status_code = 500
    mock_http_client.response.text = '{"error": "Internal Server Error"}'
    expected_payload_log = f"Failed cases payload: {json.dumps([{'id': 1}, {'id': 2}])}"
    expected_response_log = 'Failed sync response: {"error": "Internal Server Error"}'

    # Act - first failed run
    federation_sync_job.main()

    # Assert - payload and response text logged on first failure
    assert expected_payload_log in caplog.text
    assert expected_response_log in caplog.text

    # Act - second consecutive failed run
    caplog.clear()
    federation_sync_job.main()

    # Assert - payload and response text are not logged again on consecutive failure
    assert expected_payload_log not in caplog.text
    assert expected_response_log not in caplog.text


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_failed_run_logs_cases_payload_again_after_recovery(
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
    job_context: dict[tuple[str, str], str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Arrange
    federation_cases.response.json.return_value = {
        "cases": [{"id": 1}],
        "continuationToken": DEFAULT_CONTINUATION,
    }
    mock_http_client.response.text = '{"error": "Bad Gateway"}'
    expected_payload_log = f"Failed cases payload: {json.dumps([{'id': 1}])}"
    expected_response_log = 'Failed sync response: {"error": "Bad Gateway"}'

    # Act 1 - first failure logs payload and response text
    mock_http_client.response.status_code = 500
    federation_sync_job.main()
    assert expected_payload_log in caplog.text
    assert expected_response_log in caplog.text

    # Act 2 - successful run resets failure flag
    caplog.clear()
    mock_http_client.response.status_code = 200
    federation_sync_job.main()
    assert expected_payload_log not in caplog.text
    assert expected_response_log not in caplog.text

    # Act 3 - subsequent failure logs payload and response text again
    caplog.clear()
    mock_http_client.response.status_code = 500
    federation_sync_job.main()
    assert expected_payload_log in caplog.text
    assert expected_response_log in caplog.text


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_continuation_token_is_reused_on_next_run(
    federation_cases: GetFederationCasesStub,
    mock_http_client: MockHttpClient,
    job_context: dict[tuple[str, str], str],
) -> None:
    # Arrange - first run returns a case and a continuation token
    federation_cases.response.json.return_value = {
        "cases": [{"id": 1}],
        "continuationToken": DEFAULT_CONTINUATION,
    }
    mock_http_client.response.status_code = 200

    # Act - two consecutive job executions
    federation_sync_job.main()
    federation_sync_job.main()

    # Assert - the second run fetched with the saved continuation token
    assert len(federation_cases.calls) == 2
    assert federation_cases.calls[0]["continuation_token"] is None
    assert federation_cases.calls[1]["continuation_token"] == DEFAULT_CONTINUATION


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "Chronicle API URL": "",
        "Target Platform": LEGACY_TARGET_PLATFORM,
        "API Key": LEGACY_API_KEY,
        "Verify SSL": "True",
    },
)
def test_legacy_target_platform_and_api_key_sync_cases(
    federation_cases: GetFederationCasesStub,
    patch_cases: PatchFederationCasesStub,
    mock_http_client: MockHttpClient,
    job_context: dict[tuple[str, str], str],
) -> None:
    # Arrange
    federation_cases.response.json.return_value = {
        "cases": [{"id": 1}],
        "continuationToken": DEFAULT_CONTINUATION,
        "executionMessage": "Synced up to case 1",
    }
    patch_cases.response.status_code = 200

    # Act
    federation_sync_job.main()

    # Assert
    assert not mock_http_client.requests
    assert len(patch_cases.calls) == 1
    assert patch_cases.calls[0]["cases_payload"] == [{"id": 1}]
    assert patch_cases.calls[0]["api_root"] == f"https://{LEGACY_TARGET_PLATFORM}/api"
    assert patch_cases.calls[0]["api_key"] == LEGACY_API_KEY
    saved_values = [json.loads(value) for value in job_context.values()]
    assert len(saved_values) == 1
    assert saved_values[0]["continuation_token"] == DEFAULT_CONTINUATION


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "Chronicle API URL": CHRONICLE_API_URL,
        "Target Platform": LEGACY_TARGET_PLATFORM,
        "API Key": LEGACY_API_KEY,
        "Verify SSL": "True",
    },
)
def test_chronicle_api_url_takes_precedence_over_legacy_params(
    federation_cases: GetFederationCasesStub,
    patch_cases: PatchFederationCasesStub,
    mock_http_client: MockHttpClient,
    job_context: dict[tuple[str, str], str],
) -> None:
    # Arrange
    federation_cases.response.json.return_value = {
        "cases": [{"id": 1}],
        "continuationToken": DEFAULT_CONTINUATION,
    }
    mock_http_client.response.status_code = 200

    # Act
    federation_sync_job.main()

    # Assert
    assert not patch_cases.calls
    assert len(mock_http_client.requests) == 1
    assert mock_http_client.requests[0]["url"] == SYNC_URL
