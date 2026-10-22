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
from unittest.mock import MagicMock, patch

import pytest

from sap_erp.core.constants import (
    CLOUD_PLATFORM_SCOPE,
    DEFAULT_TIMEOUT_SECONDS,
    PING_TIMEOUT_SECONDS,
)
from sap_erp.core.exceptions import SapErpAuthError
from sap_erp.core.sap_erp_manager import SapErpManager

if TYPE_CHECKING:
    from .conftest import ResponseFactory

BASE = "https://gw-abc.a.run.app"
INSTANCE = "S4H_SANDBOX_00"
SA_INFO = {"type": "service_account", "project_id": "test-project"}


@pytest.mark.parametrize("raw_url", [BASE, f"{BASE}/", f"  {BASE}  ", f"  {BASE}/ "])
def test_url_whitespace_and_trailing_slash_stripped(raw_url: str) -> None:
    manager = SapErpManager(cloud_run_url=raw_url)
    assert manager.cloud_run_url == BASE
    assert manager.audience == BASE


def test_path_is_kept_but_audience_is_origin() -> None:
    # Cloud Run ID tokens must be minted for the service origin, not the path.
    manager = SapErpManager(cloud_run_url=f"{BASE}/execute/")
    assert manager.cloud_run_url == f"{BASE}/execute"
    assert manager.audience == BASE


def test_audience_falls_back_to_raw_value_without_scheme() -> None:
    manager = SapErpManager(cloud_run_url="gw-abc.a.run.app")
    assert manager.audience == "gw-abc.a.run.app"


def test_defaults() -> None:
    manager = SapErpManager(cloud_run_url=BASE)
    assert manager.timeout == DEFAULT_TIMEOUT_SECONDS
    assert manager.verify_ssl is True
    assert manager.service_account_json is None
    assert manager.workload_identity_email is None


@patch("google.oauth2.id_token.fetch_id_token", return_value="tok")
@patch("requests.get")
@patch("requests.post")
def test_verify_ssl_false_is_passed_to_requests(
    mock_post: MagicMock, mock_get: MagicMock, mock_fetch: MagicMock
) -> None:
    manager = SapErpManager(cloud_run_url=BASE, verify_ssl=False)
    manager.execute_function("A", INSTANCE, "100", {})
    manager.ping()
    assert mock_post.call_args.kwargs["verify"] is False
    assert mock_get.call_args.kwargs["verify"] is False


@patch("google.oauth2.id_token.fetch_id_token", return_value="tok")
@patch("requests.post")
def test_execute_function_posts_envelope(
    mock_post: MagicMock, mock_fetch: MagicMock
) -> None:
    manager = SapErpManager(cloud_run_url=BASE, timeout=12)

    manager.execute_function(
        function_id="USER_LOCK",
        sap_instance=INSTANCE,
        sap_client="100",
        payload={"username": "JDOE"},
    )

    mock_fetch.assert_called_once()
    assert mock_fetch.call_args.args[1] == BASE
    mock_post.assert_called_once_with(
        BASE,
        json={
            "functionId": "USER_LOCK",
            "sap_instance": INSTANCE,
            "client": "100",
            "payload": {"username": "JDOE"},
        },
        headers={"Authorization": "Bearer tok"},
        timeout=12,
        verify=True,
    )


@patch(
    "google.oauth2.service_account.IDTokenCredentials.from_service_account_info"
)
@patch("requests.post")
def test_service_account_json_mints_id_token(
    mock_post: MagicMock, mock_from_sa: MagicMock
) -> None:
    mock_creds = MagicMock()
    mock_creds.token = "sa-id-tok"  # ruff: ignore[hardcoded-password-string]
    mock_from_sa.return_value = mock_creds

    manager = SapErpManager(
        cloud_run_url=BASE,
        service_account_json=json.dumps(SA_INFO),
    )
    manager.execute_function("USER_LOCK", INSTANCE, "100", {"username": "JDOE"})

    mock_from_sa.assert_called_once_with(SA_INFO, target_audience=BASE)
    mock_creds.refresh.assert_called_once()
    assert mock_post.call_args.kwargs["headers"] == {"Authorization": "Bearer sa-id-tok"}


def test_invalid_service_account_json_raises_auth_error() -> None:
    manager = SapErpManager(cloud_run_url=BASE, service_account_json="[]")
    with pytest.raises(SapErpAuthError, match="expected a JSON object"):
        manager.execute_function("A", INSTANCE, "100", {})


@patch("google.auth.impersonated_credentials.IDTokenCredentials")
@patch("google.auth.impersonated_credentials.Credentials")
@patch("google.auth.default")
@patch("requests.post")
def test_workload_identity_email_mints_impersonated_id_token(
    mock_post: MagicMock,
    mock_default: MagicMock,
    mock_imp_creds_cls: MagicMock,
    mock_id_creds_cls: MagicMock,
) -> None:
    source_creds = MagicMock()
    mock_default.return_value = (source_creds, "proj")
    imp_creds = MagicMock()
    mock_imp_creds_cls.return_value = imp_creds
    id_creds = MagicMock()
    id_creds.token = "wi-id-tok"  # ruff: ignore[hardcoded-password-string]
    mock_id_creds_cls.return_value = id_creds

    sa_email = "invoker@proj.iam.gserviceaccount.com"
    manager = SapErpManager(cloud_run_url=BASE, workload_identity_email=sa_email)
    manager.execute_function("USER_LOCK", INSTANCE, "100", {"username": "JDOE"})

    mock_default.assert_called_once_with(scopes=[CLOUD_PLATFORM_SCOPE])
    mock_imp_creds_cls.assert_called_once_with(
        source_credentials=source_creds,
        target_principal=sa_email,
        target_scopes=[CLOUD_PLATFORM_SCOPE],
    )
    mock_id_creds_cls.assert_called_once_with(
        imp_creds,
        target_audience=BASE,
        include_email=True,
    )
    id_creds.refresh.assert_called_once()
    assert mock_post.call_args.kwargs["headers"] == {"Authorization": "Bearer wi-id-tok"}


@patch("google.oauth2.id_token.fetch_id_token", return_value="tok")
@patch("requests.post")
def test_id_token_is_cached(mock_post: MagicMock, mock_fetch: MagicMock) -> None:
    manager = SapErpManager(cloud_run_url=BASE)
    manager.execute_function("A", INSTANCE, "100", {})
    manager.execute_function("B", INSTANCE, "100", {})
    assert mock_fetch.call_count == 1


@patch("google.oauth2.id_token.fetch_id_token", return_value="tok")
@patch("requests.get")
def test_ping_gets_configured_url(mock_get: MagicMock, mock_fetch: MagicMock) -> None:
    SapErpManager(cloud_run_url=f"{BASE}/").ping()
    mock_get.assert_called_once_with(
        BASE,
        headers={"Authorization": "Bearer tok"},
        timeout=PING_TIMEOUT_SECONDS,
        verify=True,
    )


@patch("google.oauth2.id_token.fetch_id_token", side_effect=RuntimeError("no creds"))
@patch("requests.post")
def test_token_failure_raises_auth_error(
    mock_post: MagicMock, mock_fetch: MagicMock
) -> None:
    manager = SapErpManager(cloud_run_url=BASE)
    with pytest.raises(SapErpAuthError, match="no creds"):
        manager.execute_function("A", INSTANCE, "100", {})
    mock_post.assert_not_called()


def test_extract_error_detail_json_error(make_response: ResponseFactory) -> None:
    response = make_response(500, json_body={"error": "Unsupported RFC function ID: X"})
    assert SapErpManager.extract_error_detail(response) == "Unsupported RFC function ID: X"


def test_extract_error_detail_json_without_error_key(
    make_response: ResponseFactory,
) -> None:
    response = make_response(500, json_body={"status": "ERROR"})
    assert SapErpManager.extract_error_detail(response) == '{"status": "ERROR"}'


def test_extract_error_detail_plain_text(make_response: ResponseFactory) -> None:
    response = make_response(500, text="Internal Server Error")
    assert SapErpManager.extract_error_detail(response) == "Internal Server Error"


def test_extract_error_detail_empty_body(make_response: ResponseFactory) -> None:
    response = make_response(502, text="")
    assert SapErpManager.extract_error_detail(response) == "HTTP 502"
