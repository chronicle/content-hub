from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from core.auth_provider_v1 import AuthProviderV1
from core.auth_provider_v2 import AuthProviderV2
from core.constants import DOPPEL_CLIENT_HEADER
from core.exceptions import DoppelHttpError
from core.http_client import HttpClient
from core.token_cache import TokenCache


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, headers: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.headers = headers or {}
        self.content = b"{}" if payload is not None else b""
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._payload


def test_v1_401_does_not_refresh() -> None:
    session = MagicMock()
    session.request.return_value = FakeResponse(401, {"message": "nope"})
    client = HttpClient(AuthProviderV1("key"), session=session, sleep=lambda _seconds: None)
    with pytest.raises(DoppelHttpError) as exc_info:
        client.request("GET", "https://api.doppel.com/v1/alerts")
    assert exc_info.value.status_code == 401
    assert session.request.call_count == 1


def test_v2_401_refreshes_token_and_retries() -> None:
    cache = TokenCache(now=lambda: 1_000)
    cache.set_token("expired", 86400)
    session = MagicMock()
    session.request.side_effect = [
        FakeResponse(401, {"message": "expired"}),
        FakeResponse(200, {"alerts": []}),
    ]
    session.post.return_value = MagicMock(
        ok=True,
        status_code=200,
        content=b"{}",
        json=lambda: {"access_token": "fresh", "expires_in": 86400},
    )
    provider = AuthProviderV2("id", "secret", token_cache=cache, session=session)
    client = HttpClient(provider, session=session, sleep=lambda _seconds: None)
    payload = client.request("GET", "https://api.doppel.com/v2/alerts")
    assert payload == {"alerts": []}
    assert session.request.call_count == 2
    assert session.request.call_args.kwargs["headers"]["Authorization"] == "Bearer fresh"
    assert session.request.call_args.kwargs["headers"]["x-doppel-client"] == DOPPEL_CLIENT_HEADER


def test_retries_429_then_succeeds() -> None:
    session = MagicMock()
    session.request.side_effect = [
        FakeResponse(429, {"message": "slow down"}, headers={"Retry-After": "0"}),
        FakeResponse(200, {"ok": True}),
    ]
    client = HttpClient(AuthProviderV1("key"), session=session, sleep=lambda _seconds: None)
    assert client.request("GET", "https://api.doppel.com/v1/alerts") == {"ok": True}
    assert session.request.call_count == 2
    assert session.request.call_args.kwargs["headers"]["x-doppel-client"] == DOPPEL_CLIENT_HEADER


def test_retries_5xx_then_raises() -> None:
    session = MagicMock()
    session.request.return_value = FakeResponse(500, {"message": "boom"})
    client = HttpClient(AuthProviderV1("key"), session=session, sleep=lambda _seconds: None)
    with pytest.raises(DoppelHttpError) as exc_info:
        client.request("GET", "https://api.doppel.com/v1/alerts")
    assert exc_info.value.status_code == 500
    assert session.request.call_count == 3
