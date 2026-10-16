from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from core.alert_models import normalize_alert, normalize_alert_list
from core.auth_provider_v1 import AuthProviderV1
from core.auth_provider_v2 import AuthProviderV2
from core.constants import DOPPEL_CLIENT_HEADER, OAUTH_AUDIENCE, OAUTH_TOKEN_URL
from core.exceptions import DoppelConfigError, DoppelHttpError
from core.token_cache import TokenCache


def test_v1_headers_match_existing_auth() -> None:
    headers = AuthProviderV1(
        api_key="org-key",
        user_api_key="user-key",
        org_code="ACM",
    ).get_auth_headers()
    assert headers == {
        "accept": "application/json",
        "x-api-key": "org-key",
        "x-user-api-key": "user-key",
        "x-organization-code": "ACM",
    }


def test_v1_requires_api_key() -> None:
    with pytest.raises(DoppelConfigError):
        AuthProviderV1(api_key="")


def test_v2_mints_and_caches_token() -> None:
    cache = TokenCache(now=lambda: 1_000)
    session = MagicMock()
    session.post.return_value = MagicMock(
        ok=True,
        status_code=200,
        content=b"{}",
        json=lambda: {"access_token": "tok-1", "expires_in": 86400},
    )
    provider = AuthProviderV2(
        client_id="id",
        client_secret="secret",
        token_cache=cache,
        session=session,
    )
    headers = provider.get_auth_headers()
    assert headers["Authorization"] == "Bearer tok-1"
    session.post.assert_called_once()
    _, kwargs = session.post.call_args
    assert kwargs["json"]["audience"] == OAUTH_AUDIENCE
    assert kwargs["json"]["grant_type"] == "client_credentials"
    assert kwargs["headers"]["x-doppel-client"] == DOPPEL_CLIENT_HEADER
    assert session.post.call_args[0][0] == OAUTH_TOKEN_URL

    session.post.reset_mock()
    cached = provider.get_auth_headers()
    assert cached["Authorization"] == "Bearer tok-1"
    session.post.assert_not_called()


def test_v2_force_refresh_mints_new_token() -> None:
    cache = TokenCache(now=lambda: 1_000)
    cache.set_token("stale", 86400)
    session = MagicMock()
    session.post.return_value = MagicMock(
        ok=True,
        status_code=200,
        content=b"{}",
        json=lambda: {"access_token": "tok-2", "expires_in": 86400},
    )
    provider = AuthProviderV2("id", "secret", token_cache=cache, session=session)
    headers = provider.get_auth_headers(force_refresh=True)
    assert headers["Authorization"] == "Bearer tok-2"
    session.post.assert_called_once()


def test_v2_oauth_error_does_not_include_secret() -> None:
    session = MagicMock()
    session.post.return_value = MagicMock(
        ok=False,
        status_code=401,
        content=b"{}",
        json=lambda: {"error": "access_denied", "error_description": "Unauthorized"},
    )
    provider = AuthProviderV2("id", "secret", token_cache=TokenCache(), session=session)
    with pytest.raises(DoppelHttpError, match="OAuth token request failed") as exc_info:
        provider.get_auth_headers()
    assert "secret" not in str(exc_info.value)


def test_normalize_alert_maps_v1_and_v2_aliases() -> None:
    v2 = normalize_alert(
        {
            "id": "ACM-1",
            "notes": "Analyst note",
            "last_activity": "2026-01-01T00:00:00",
            "assignee": "a@x.com",
        },
    )
    v1 = normalize_alert(
        {
            "id": "ACM-1",
            "note": "Legacy note",
            "last_activity_timestamp": "2026-01-02T00:00:00",
        },
    )
    assert v2["notes"] == "Analyst note"
    assert v2["last_activity_timestamp"] == "2026-01-01T00:00:00"
    assert v2["assignee"] == "a@x.com"
    assert v1["notes"] == "Legacy note"
    assert v1["last_activity_timestamp"] == "2026-01-02T00:00:00"
    assert normalize_alert_list([{"id": "ACM-1"}, None]) == [
        normalize_alert({"id": "ACM-1"}),
    ]
