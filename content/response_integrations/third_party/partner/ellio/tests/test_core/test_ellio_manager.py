from __future__ import annotations

import json

import pytest
import requests

from ...core.ellio_manager import EllioManager, EllioManagerError


class FakeResponse:
    def __init__(self, status_code: int = 200, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.content = json.dumps(self._payload).encode()

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)


class FakeSession:
    """Records the last request and returns a canned response."""

    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.last_url: str | None = None
        self.last_params: dict | None = None
        self.last_json: dict | None = None

    def get(self, url, params=None, timeout=None):
        self.last_url = url
        self.last_params = params
        return self.response

    def post(self, url, json=None, timeout=None):
        self.last_url = url
        self.last_json = json
        return self.response


def make_manager(response: FakeResponse, **kwargs) -> tuple[EllioManager, FakeSession]:
    manager = EllioManager("https://api.example.com/", "test-key", **kwargs)
    session = FakeSession(response)
    manager.session = session
    return manager, session


# ---------- lookup_ip ----------

def test_lookup_ip_returns_none_on_404():
    manager, _ = make_manager(FakeResponse(404))
    assert manager.lookup_ip("27.43.204.10") is None


def test_lookup_ip_returns_none_when_not_seen():
    manager, _ = make_manager(FakeResponse(200, {"seen": False}))
    assert manager.lookup_ip("27.43.204.10") is None


def test_lookup_ip_raises_on_http_error():
    manager, _ = make_manager(FakeResponse(500, {"error": "boom"}))
    with pytest.raises(EllioManagerError):
        manager.lookup_ip("27.43.204.10")


class BadJsonResponse(FakeResponse):
    def json(self) -> dict:
        raise ValueError("not json")


def test_lookup_ip_raises_on_non_json_body():
    manager, _ = make_manager(BadJsonResponse(200))
    with pytest.raises(EllioManagerError):
        manager.lookup_ip("27.43.204.10")


def test_lookup_ip_strips_trailing_slash_from_api_root():
    manager, session = make_manager(FakeResponse(200, {"seen": False}))
    manager.lookup_ip("27.43.204.10")
    assert session.last_url == "https://api.example.com/v1/cti/extended_lookup/27.43.204.10"


def test_lookup_ip_normalizes_record():
    payload = {
        "seen": True,
        "rdns": "host.example.net",
        "classification": "malicious",
        "actor": "censys",
        "spoofable": False,
        "cve": ["CVE-2018-10561", "", "  "],
        "tags": ["Exploit Attempt"],
        "tag_ids": ["exploit_attempt"],
        "src": {"geo": {"country": {"code": "NL", "name": "Netherlands"},
                        "continent": {"code": "EU"}}},
        "network": {"ports": [23, 80], "non_spoofable_ports": [80]},
        "fingerprints": {"muonfp": ["64240:2-4-8-1-3:1379:10"], "ja3": [], "ja4": []},
        "http": {"path": ["/"], "user_agent": ["curl"]},
        "first_seen": "2026-01-08",
        "last_seen": "2026-06-24",
    }
    manager, _ = make_manager(FakeResponse(200, payload))
    record = manager.lookup_ip("27.43.204.10")
    assert record["classification"] == "malicious"
    assert record["cve"] == "CVE-2018-10561"          # empty strings filtered
    assert record["country"] == "NL"
    assert record["country_name"] == "Netherlands"
    assert record["continent"] == "EU"
    assert record["ports"] == "23|80"
    assert record["non_spoofable_ports"] == "80"
    assert record["muonfp"] == "64240:2-4-8-1-3:1379:10"
    assert record["http_user_agent"] == "curl"
    assert record["spoofable"] is False


def test_lookup_ip_drops_unknown_actor_placeholder():
    manager, _ = make_manager(FakeResponse(200, {"seen": True, "actor": "Unknown"}))
    assert manager.lookup_ip("27.43.204.10")["actor"] == ""


def test_lookup_ip_keeps_real_actor():
    manager, _ = make_manager(FakeResponse(200, {"seen": True, "actor": "censys"}))
    assert manager.lookup_ip("27.43.204.10")["actor"] == "censys"


def test_lookup_ip_caps_long_lists_with_sentinel():
    payload = {"seen": True, "network": {"ports": list(range(1, 31))}}
    manager, _ = make_manager(FakeResponse(200, payload))
    ports = manager.lookup_ip("27.43.204.10")["ports"]
    assert ports.endswith("|(+5 more)")               # 30 ports, capped at 25
    assert ports.count("|") == 25


# ---------- cbs_lookup ----------

def test_cbs_lookup_returns_record_when_found():
    payload = {"ip": "13.107.42.14", "found": True, "providers": ["azure"]}
    manager, session = make_manager(FakeResponse(200, payload))
    assert manager.cbs_lookup("13.107.42.14") == payload
    assert session.last_url == "https://api.example.com/v1/cbs/lookup"
    assert session.last_params == {"ip": "13.107.42.14"}


def test_cbs_lookup_returns_none_when_not_found():
    manager, _ = make_manager(FakeResponse(200, {"found": False}))
    assert manager.cbs_lookup("27.43.204.10") is None


def test_cbs_lookup_returns_none_on_404():
    manager, _ = make_manager(FakeResponse(404))
    assert manager.cbs_lookup("27.43.204.10") is None


# ---------- add_ip_to_blocklist ----------

def test_blocklist_requires_ruleset_id():
    manager, _ = make_manager(FakeResponse(200))
    with pytest.raises(EllioManagerError):
        manager.add_ip_to_blocklist("27.43.204.10")


def test_blocklist_payload_omits_expiry_for_permanent_rule():
    manager, session = make_manager(FakeResponse(200, {"status": "added"}),
                                    blocklist_ruleset_id="rs-1")
    manager.add_ip_to_blocklist("27.43.204.10", name="case-1", expires_in_days=0)
    assert session.last_url == "https://api.example.com/v1/edl/ip-rulesets/rs-1/rules"
    assert session.last_json == {"ip": "27.43.204.10", "conflict_resolution": "extend",
                                 "name": "case-1"}


def test_blocklist_payload_includes_positive_expiry():
    manager, session = make_manager(FakeResponse(200, {"status": "added"}),
                                    blocklist_ruleset_id="rs-1")
    manager.add_ip_to_blocklist("27.43.204.10", conflict_resolution="skip",
                                expires_in_days=14)
    assert session.last_json["expires_in_days"] == 14
    assert session.last_json["conflict_resolution"] == "skip"
    assert "name" not in session.last_json


def test_blocklist_surfaces_permission_error():
    manager, _ = make_manager(FakeResponse(403, {"detail": "Permission Denied"}),
                              blocklist_ruleset_id="rs-1")
    with pytest.raises(EllioManagerError):
        manager.add_ip_to_blocklist("27.43.204.10")
