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

from sap_erp.core.sap_erp_manager import (
    DEFAULT_TIMEOUT_SECONDS,
    PING_TIMEOUT_SECONDS,
    SapErpAuthError,
    SapErpManager,
)

if TYPE_CHECKING:
    from .conftest import ResponseFactory

BASE = "https://gw-abc.a.run.app"
INSTANCE = "S4H_SANDBOX_00"


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
