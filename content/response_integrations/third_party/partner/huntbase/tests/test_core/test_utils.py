from __future__ import annotations

from types import SimpleNamespace

import pytest

from huntbase.core.utils import (
    entity_value,
    external_ref,
    guess_value_type,
    indicator_insight,
    is_http_url,
    prefixed,
    seed_values_from_entities,
)

from ..conftest import MockEntity


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("203.0.113.10", "ip"),
        ("2001:db8::1", "ip"),
        ("d41d8cd98f00b204e9800998ecf8427e", "hash"),
        ("a" * 64, "hash"),
        ("https://evil.example/x", "url"),
        ("alice@example.com", "email"),
        ("evil.example", "domain"),
        ("WS-0142", "hostname"),
    ],
)
def test_guess_value_type(value: str, expected: str) -> None:
    assert guess_value_type(value) == expected


def test_external_ref() -> None:
    assert external_ref(SimpleNamespace(case_id=None)) is None
    assert external_ref(SimpleNamespace(case_id=4821), "https://secops.example/cases/4821", "Case title") == {
        "source": "google_secops",
        "id": "4821",
        "url": "https://secops.example/cases/4821",
        "title": "Case title",
    }


def test_seed_values_dedupe_and_original_identifier() -> None:
    entities = [
        MockEntity("WS-0142", "HOSTNAME"),
        MockEntity("ws-0142", "HOSTNAME"),
        MockEntity("EVIL.EXAMPLE", "DOMAIN", {"OriginalIdentifier": "evil.example"}),
        MockEntity("ALICE", "USERUNIQNAME"),
        MockEntity("CVE-2026-1", "CVE"),
    ]
    assert entity_value(entities[2]) == "evil.example"
    assert seed_values_from_entities(entities) == [
        {"type": "hostname", "value": "WS-0142"},
        {"type": "domain", "value": "evil.example"},
        {"type": "user", "value": "ALICE"},
    ]


def test_prefixed_and_insight_escaping() -> None:
    assert prefixed({"status": "known"}) == {"HB_status": "known"}
    html = indicator_insight("<b>x</b>", {"status": "known", "link": "https://hb/x?a=1&b=2"})
    assert "&lt;b&gt;" in html
    assert 'href="https://hb/x?a=1&amp;b=2"' in html


def test_external_ref_trims_title_and_url_check() -> None:
    ref = external_ref(SimpleNamespace(case_id="1"), None, "t" * 400)
    assert len(ref["title"]) == 300
    assert "url" not in ref
    assert is_http_url("https://secops.example/cases/1")
    assert not is_http_url("secops.example/cases/1")
    assert not is_http_url(None)


@pytest.mark.parametrize(
    "link",
    ["javascript:alert(1)", "data:text/html,<script>alert(1)</script>", "  JavaScript:alert(1)", "//evil.example", 7],
)
def test_insight_drops_unsafe_links(link: object) -> None:
    html = indicator_insight("1.2.3.4", {"status": "known", "link": link})
    assert "<a " not in html
    assert "javascript" not in html.lower()


def test_insight_link_opens_safely() -> None:
    html = indicator_insight("1.2.3.4", {"status": "known", "link": "https://hb.example/i/1"})
    assert '<a href="https://hb.example/i/1" target="_blank" rel="noopener noreferrer">' in html


def test_prefixed_keeps_scalars_and_flattens_objects() -> None:
    props = prefixed({"status": "known", "score": 96, "sighted": False, "extra": {"b": 1, "a": 2}, "tags": ["x"]})
    assert props == {
        "HB_status": "known",
        "HB_score": 96,
        "HB_sighted": False,
        "HB_extra": '{"a": 2, "b": 1}',
        "HB_tags": '["x"]',
    }
