from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from core.DoppelManager import DoppelManager
from core.exceptions import DoppelConfigError, DoppelHttpError


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.headers = {}
        self.content = b"{}"
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._payload


def _manager(api_version: str = "v1", session: MagicMock | None = None) -> DoppelManager:
    session = session or MagicMock()
    if api_version == "v1":
        return DoppelManager(api_key="key", session=session, sleep=lambda _seconds: None)
    session.post.return_value = MagicMock(
        ok=True,
        status_code=200,
        content=b"{}",
        json=lambda: {"access_token": "tok", "expires_in": 86400},
    )
    return DoppelManager(
        api_version="v2",
        client_id="id",
        client_secret="secret",
        session=session,
        sleep=lambda _seconds: None,
    )


def test_v1_constructor_backward_compatible() -> None:
    manager = DoppelManager(api_key="key", user_api_key="user", org_code="ACM")
    assert manager.api_version == "v1"
    assert manager.base_url == "https://api.doppel.com/v1"
    headers = manager.auth_provider.get_auth_headers()
    assert headers["x-api-key"] == "key"
    assert headers["x-user-api-key"] == "user"
    assert headers["x-organization-code"] == "ACM"


def test_v2_uses_oauth_base_url() -> None:
    session = MagicMock()
    session.post.return_value = MagicMock(
        ok=True,
        status_code=200,
        content=b"{}",
        json=lambda: {"access_token": "tok", "expires_in": 86400},
    )
    manager = _manager("v2", session)
    assert manager.base_url == "https://api.doppel.com/v2"
    assert manager.auth_provider.get_auth_headers()["Authorization"] == "Bearer tok"


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_get_alerts_per_version(version: str) -> None:
    session = MagicMock()
    manager = _manager(version, session)
    session.request.return_value = FakeResponse(200, {"alerts": [{"id": "ACM-1"}]})
    alerts = manager.get_alerts(filters={"page": 0})
    assert alerts == [{"id": "ACM-1"}]
    assert session.request.call_args.kwargs["url"] == f"https://api.doppel.com/{version}/alerts"


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_get_alert_per_version(version: str) -> None:
    session = MagicMock()
    manager = _manager(version, session)
    session.request.return_value = FakeResponse(200, {"id": "ACM-1", "entity": "https://x.test"})
    alert = manager.get_alert(alert_id="ACM-1")
    assert alert["id"] == "ACM-1"
    assert session.request.call_args.kwargs["url"] == f"https://api.doppel.com/{version}/alert"
    assert session.request.call_args.kwargs["params"] == {"id": "ACM-1"}


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_create_alert_per_version(version: str) -> None:
    session = MagicMock()
    manager = _manager(version, session)
    session.request.return_value = FakeResponse(201, {"id": "ACM-2"})
    created = manager.create_alert("https://evil.test")
    assert created["id"] == "ACM-2"
    assert session.request.call_args.kwargs["json"] == {"entity": "https://evil.test"}
    assert session.request.call_args.kwargs["url"] == f"https://api.doppel.com/{version}/alert"


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_update_alert_sends_comment_not_notes(version: str) -> None:
    session = MagicMock()
    manager = _manager(version, session)
    session.request.return_value = FakeResponse(200, {"id": "ACM-1", "notes": "from jira"})
    updated = manager.update_alert(alert_id="ACM-1", comment="from jira")
    assert updated["notes"] == "from jira"
    body = session.request.call_args.kwargs["json"]
    assert body == {"comment": "from jira"}
    assert "notes" not in body


def test_connection_test_uses_small_page() -> None:
    session = MagicMock()
    manager = _manager("v1", session)
    session.request.return_value = FakeResponse(200, {"alerts": [], "metadata": {"count": 0}})
    assert manager.connection_test() is True
    assert session.request.call_args.kwargs["params"] == {"page": 0, "page_size": 1}


def test_repeated_get_alert_is_idempotent() -> None:
    session = MagicMock()
    manager = _manager("v1", session)
    session.request.return_value = FakeResponse(200, {"id": "ACM-1"})
    first = manager.get_alert(alert_id="ACM-1")
    second = manager.get_alert(alert_id="ACM-1")
    assert first == second
    assert session.request.call_count == 2


def test_update_requires_at_least_one_field() -> None:
    manager = _manager("v1")
    with pytest.raises(ValueError, match="At least one"):
        manager.update_alert(alert_id="ACM-1")


def test_v2_without_credentials_fails() -> None:
    with pytest.raises(DoppelConfigError):
        DoppelManager(api_version="v2")


def test_http_error_on_failed_fetch() -> None:
    session = MagicMock()
    manager = _manager("v1", session)
    session.request.return_value = FakeResponse(403, {"message": "Forbidden"})
    with pytest.raises(DoppelHttpError) as exc_info:
        manager.get_alert(alert_id="ACM-1")
    assert exc_info.value.status_code == 403
