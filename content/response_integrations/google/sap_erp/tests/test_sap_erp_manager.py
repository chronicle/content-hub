from unittest.mock import patch

import pytest

from sap_erp.core.sap_erp_manager import (
    DEFAULT_TIMEOUT_SECONDS,
    PING_TIMEOUT_SECONDS,
    SapErpAuthError,
    SapErpManager,
)

BASE = "https://gw-abc.a.run.app"


@pytest.mark.parametrize("raw_url", [BASE, f"{BASE}/", f"  {BASE}  ", f"  {BASE}/ "])
def test_url_whitespace_and_trailing_slash_stripped(raw_url):
    manager = SapErpManager(cloud_run_url=raw_url)
    assert manager.cloud_run_url == BASE
    assert manager.audience == BASE


def test_path_is_kept_but_audience_is_origin():
    # Cloud Run ID tokens must be minted for the service origin, not the path.
    manager = SapErpManager(cloud_run_url=f"{BASE}/execute/")
    assert manager.cloud_run_url == f"{BASE}/execute"
    assert manager.audience == BASE


def test_audience_falls_back_to_raw_value_without_scheme():
    manager = SapErpManager(cloud_run_url="gw-abc.a.run.app")
    assert manager.audience == "gw-abc.a.run.app"


def test_default_timeout():
    assert SapErpManager(cloud_run_url=BASE).timeout == DEFAULT_TIMEOUT_SECONDS


@patch("google.oauth2.id_token.fetch_id_token", return_value="tok")
@patch("requests.post")
def test_execute_function_posts_envelope(mock_post, mock_fetch):
    manager = SapErpManager(cloud_run_url=BASE, timeout=12)

    manager.execute_function(
        function_id="USER_LOCK",
        sap_instance="S4H_SANDBOX_00",
        sap_client="100",
        payload={"username": "JDOE"},
    )

    mock_fetch.assert_called_once()
    assert mock_fetch.call_args.args[1] == BASE
    mock_post.assert_called_once_with(
        BASE,
        json={
            "functionId": "USER_LOCK",
            "sap_instance": "S4H_SANDBOX_00",
            "client": "100",
            "payload": {"username": "JDOE"},
        },
        headers={"Authorization": "Bearer tok"},
        timeout=12,
    )


@patch("google.oauth2.id_token.fetch_id_token", return_value="tok")
@patch("requests.post")
def test_id_token_is_cached(mock_post, mock_fetch):
    manager = SapErpManager(cloud_run_url=BASE)
    manager.execute_function("A", "I", "100", {})
    manager.execute_function("B", "I", "100", {})
    assert mock_fetch.call_count == 1


@patch("google.oauth2.id_token.fetch_id_token", return_value="tok")
@patch("requests.get")
def test_ping_gets_configured_url(mock_get, mock_fetch):
    SapErpManager(cloud_run_url=f"{BASE}/").ping()
    mock_get.assert_called_once_with(
        BASE,
        headers={"Authorization": "Bearer tok"},
        timeout=PING_TIMEOUT_SECONDS,
    )


@patch("google.oauth2.id_token.fetch_id_token", side_effect=RuntimeError("no creds"))
@patch("requests.post")
def test_token_failure_raises_auth_error(mock_post, mock_fetch):
    manager = SapErpManager(cloud_run_url=BASE)
    with pytest.raises(SapErpAuthError, match="no creds"):
        manager.execute_function("A", "I", "100", {})
    mock_post.assert_not_called()


def test_extract_error_detail_json_error(make_response):
    response = make_response(500, json_body={"error": "Unsupported RFC function ID: X"})
    assert SapErpManager.extract_error_detail(response) == "Unsupported RFC function ID: X"


def test_extract_error_detail_json_without_error_key(make_response):
    response = make_response(500, json_body={"status": "ERROR"})
    assert SapErpManager.extract_error_detail(response) == '{"status": "ERROR"}'


def test_extract_error_detail_plain_text(make_response):
    response = make_response(500, text="Internal Server Error")
    assert SapErpManager.extract_error_detail(response) == "Internal Server Error"


def test_extract_error_detail_empty_body(make_response):
    response = make_response(502, text="")
    assert SapErpManager.extract_error_detail(response) == "HTTP 502"
