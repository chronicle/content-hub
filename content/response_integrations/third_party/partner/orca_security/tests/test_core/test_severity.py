"""Pins the alert severity contract: which field is filtered and how it maps."""

from __future__ import annotations

from typing import Any

from ...core.constants import POSSIBLE_SEVERITIES, SEVERITY_MAPPING
from ...core.OrcaSecurityParser import OrcaSecurityParser
from ...core.query_builder import AlertQueryBuilder
from ..common import HOUR_MS, NOW_MS, build_alert_row, build_response


def _conditions(payload: dict[str, Any]) -> dict[str, Any]:
    """Extracts query conditions keyed by their target field name."""
    return {condition["key"]: condition for condition in payload["query"]["with"]["values"] if "key" in condition}


def test_severity_filter_targets_risk_level() -> None:
    """Severity holds the product's own wording, RiskLevel the standard one."""
    payload = AlertQueryBuilder(NOW_MS - HOUR_MS, 100).with_severity("medium").build()
    conditions = _conditions(payload)

    assert "Severity" not in conditions
    assert conditions["RiskLevel"]["values"] == ["critical", "high", "medium"]
    assert conditions["RiskLevel"]["operator"] == "in"


def test_severity_filter_is_a_lower_bound() -> None:
    """The parameter selects its own level and everything more severe."""
    payload = AlertQueryBuilder(NOW_MS - HOUR_MS, 100).with_severity("critical").build()

    assert _conditions(payload)["RiskLevel"]["values"] == ["critical"]


def test_severity_filter_accepts_mixed_case() -> None:
    """The documented values are title-cased, so the filter normalises them."""
    payload = AlertQueryBuilder(NOW_MS - HOUR_MS, 100).with_severity("Critical").build()

    assert _conditions(payload)["RiskLevel"]["values"] == ["critical"]


def test_no_severity_filter_when_the_parameter_is_empty() -> None:
    """An empty parameter must not narrow the query at all."""
    payload = AlertQueryBuilder(NOW_MS - HOUR_MS, 100).with_severity("").build()

    assert "RiskLevel" not in _conditions(payload)


def test_parser_reads_risk_level() -> None:
    """The alert severity comes from RiskLevel, not from Severity."""
    row = build_alert_row("orca-1", NOW_MS - HOUR_MS, NOW_MS, risk_level="high")

    alert = OrcaSecurityParser().build_alert_objects(build_response([row]))[0]

    assert alert.severity == "high"


def test_parser_tolerates_an_explicit_null_risk_level() -> None:
    """An explicit null in the payload must not break the whole fetch cycle."""
    row = build_alert_row("orca-1", NOW_MS - HOUR_MS, NOW_MS)
    row["data"]["RiskLevel"] = None

    alert = OrcaSecurityParser().build_alert_objects(build_response([row]))[0]

    assert alert.severity is None


def test_every_supported_severity_maps_to_a_case_priority() -> None:
    """A severity missing from the mapping silently becomes -1 (Informative)."""
    assert set(POSSIBLE_SEVERITIES) <= set(SEVERITY_MAPPING)

    priorities = [SEVERITY_MAPPING[severity] for severity in POSSIBLE_SEVERITIES]

    assert priorities == [100, 80, 60, 40, -1]


def test_case_priority_follows_the_alert_risk_level() -> None:
    """Each severity produces its own case priority, none falls back to -1."""
    for risk_level, expected in [
        ("critical", 100),
        ("high", 80),
        ("medium", 60),
        ("low", 40),
        ("informational", -1),
    ]:
        row = build_alert_row("orca-1", NOW_MS - HOUR_MS, NOW_MS, risk_level=risk_level)

        alert = OrcaSecurityParser().build_alert_objects(build_response([row]))[0]

        assert alert.get_siemplify_severity() == expected
