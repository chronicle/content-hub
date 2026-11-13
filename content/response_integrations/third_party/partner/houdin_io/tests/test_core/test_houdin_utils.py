from __future__ import annotations

import pytest

from houdin_io.core.houdin_utils import (
    enrichment_fields,
    insight_content,
    markdown_to_html,
    normalize_scanners,
    parse_scanners,
    parse_threshold,
    scan_link,
    verdict_line,
    verdict_of,
)
from houdin_io.tests.mock_session import EXAMPLE_DOCUMENT


def test_verdict_of_example_document() -> None:
    verdict = verdict_of(EXAMPLE_DOCUMENT)
    assert verdict["score"] == 8
    assert verdict["confidence"] == "high"
    assert verdict["tags"][0] == "Malicious hosting infrastructure"
    assert verdict["related"][0].startswith("46001fa9")
    assert "mesmer" not in verdict["sources"] and "vt" in verdict["sources"]
    assert verdict["unrecorded"] is False


def test_verdict_of_missing_or_failed_mesmer() -> None:
    assert verdict_of({})["score"] is None
    failed = {"scanResults": {"mesmer": {"result": {"error": "Rate limit"}}}}
    assert verdict_of(failed)["summary"] == ""
    assert verdict_line(failed) == "no MesmerAI verdict"


def test_verdict_line() -> None:
    assert verdict_line(EXAMPLE_DOCUMENT).startswith("8/10, high confidence: Malicious hosting infrastructure")
    unrecorded = {"scanResults": {"mesmer": {"result": {"globalScore": 0, "unrecorded": True}}}}
    assert verdict_line(unrecorded) == "0/10 (no source holds a record of it)"


def test_enrichment_fields_are_prefixed_and_non_empty() -> None:
    fields = enrichment_fields(EXAMPLE_DOCUMENT)
    assert all(key.startswith("Houdin-io_") for key in fields)
    assert fields["Houdin-io_Threat_Score"] == "8"
    assert fields["Houdin-io_Scan_Link"] == scan_link(EXAMPLE_DOCUMENT["scanID"])
    assert "Houdin-io_Unrecorded" not in fields
    assert "" not in fields.values()


def test_scan_link_strips_prefix() -> None:
    assert scan_link("houdin-abc") == "https://app.houdin.io/scans/abc"
    assert scan_link("abc") == "https://app.houdin.io/scans/abc"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("", None),
        ("[]", None),
        ('["vt", "urlscan"]', ["vt", "urlscan"]),
        ("vt, urlscan", ["vt", "urlscan"]),
        (["vt"], ["vt"]),
        ("[not json", None),
    ],
)
def test_parse_scanners(raw: object, expected: list[str] | None) -> None:
    assert parse_scanners(raw) == expected


def test_normalize_scanners_appends_mesmer_modules() -> None:
    assert normalize_scanners(None) is None
    assert normalize_scanners([" ", ""]) is None
    assert normalize_scanners([" vt ", "mesmer"]) == ["vt", "mesmer", "mesmer-summary"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, 7), ("", 7), ("9", 9), ("6.0", 6), ("off", None), ("none", None), ("0", 0), ("10", 10)],
)
def test_parse_threshold(raw: object, expected: int | None) -> None:
    assert parse_threshold(raw, 7) == expected


@pytest.mark.parametrize("raw", ["11", "-1", "high"])
def test_parse_threshold_rejects(raw: str) -> None:
    with pytest.raises(ValueError, match="Suspicious Threshold"):
        parse_threshold(raw, 7)


def test_markdown_to_html() -> None:
    text = "**Bad** host with `ssh` open, *maybe* C2.\n\n- one\n- two\n\nLine a\nLine b <script>"
    out = markdown_to_html(text)
    assert out.startswith("<b>Bad</b> host with <code>ssh</code> open, <i>maybe</i> C2.")
    assert "<ul><li>one</li><li>two</li></ul>" in out
    assert "Line a<br/>Line b &lt;script&gt;" in out


def test_insight_content_has_verdict_summary_and_link() -> None:
    out = insight_content(EXAMPLE_DOCUMENT)
    assert out.startswith("<b>Threat score: 8/10, high confidence")
    assert "HZ Hosting (UK) server" in out
    assert 'href="https://app.houdin.io/scans/e06656eb-0f92-4e2d-8442-f20bd9150885"' in out
