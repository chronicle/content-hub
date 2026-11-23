from __future__ import annotations

import datetime
import json
from typing import TYPE_CHECKING

import pytest
from integration_testing.platform.external_context import MockExternalContext
from integration_testing.set_meta import set_metadata

from huntbase.connectors import huntbase_findings_connector as connector
from huntbase.core import constants

from .. import common

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockConnectorOutput

    from ..core.product import Huntbase
    from ..core.session import HuntbaseSession


def _iso(minutes_ago: int) -> str:
    stamp = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(minutes=minutes_ago)
    return stamp.isoformat().replace("+00:00", "Z")


def _params(**extra: str) -> dict:
    return {
        "API Root": common.API_ROOT,
        "API Key": "hb_pat_test_key",
        "Verify SSL": "true",
        "Source": "Findings",
        "Finding Dispositions": "confirmed",
        "Lowest Insight Severity": "high",
        "Max Hours Backwards": "24",
        "Max Alerts Per Cycle": "50",
        "DeviceProductField": "device_product",
        "EventClassId": "event_type",
        "PythonProcessTimeout": "180",
        **extra,
    }


def _finding(finding_id: str, minutes_ago: int, disposition: str = "confirmed", severity: str = "high") -> dict:
    return {
        "id": finding_id,
        "session_id": "h1",
        "session_title": "Beacon hunt",
        "title": f"Finding {finding_id}",
        "summary": "Regular HTTPS beacon",
        "disposition": disposition,
        "severity": severity,
        "entities": [
            {"type": "host", "value": "WS-0142", "role": "source"},
            {"type": "ip", "value": "203.0.113.10", "role": "destination"},
            {"type": "sha256", "value": "a" * 64},
            {"type": "unknown-kind", "value": "ignored"},
        ],
        "created_at": _iso(minutes_ago),
        "updated_at": _iso(max(minutes_ago - 1, 0)),
    }


def _insight(insight_id: str, minutes_ago: int, severity: str) -> dict:
    return {
        "event_id": insight_id,
        "message": f"Insight {insight_id}",
        "severity": severity,
        "status": "new",
        "time": _iso(minutes_ago),
        "normalized_at": _iso(minutes_ago),
        "watcher_name": "Suspicious PowerShell",
        "evidences": [{"device_hostname": "ws-9", "user": "bob"}],
    }


@pytest.fixture(autouse=True)
def no_overflow(monkeypatch: pytest.MonkeyPatch) -> list:
    seen: list = []

    def fake(_siemplify: object, alert_info: object, _is_test_run: bool) -> bool:
        seen.append(alert_info)
        return getattr(alert_info, "ticket_id", "") == "overflow"

    monkeypatch.setattr(connector, "is_overflowed", fake)
    return seen


def _alerts(output: MockConnectorOutput) -> list:
    return output.results.json_output.alerts


def _context(ec: MockExternalContext, key: str) -> object:
    for stored_key, value in ec._rows.items():  # noqa: SLF001
        if stored_key.endswith(key):
            return json.loads(value)
    return None


@set_metadata(
    connector_def_file_path=common.CONNECTOR_DEF_PATH, parameters=_params(), external_context=MockExternalContext()
)
def test_findings_become_alerts(
    huntbase: Huntbase,
    script_session: HuntbaseSession,
    connector_output: MockConnectorOutput,
    external_context: MockExternalContext,
) -> None:
    huntbase.findings = [_finding("f1", 30), _finding("f2", 20), _finding("f3", 10, disposition="benign")]

    connector.main(is_test_run=False)

    alerts = _alerts(connector_output)
    assert [a.ticket_id for a in alerts] == ["f1", "f2"]
    first = alerts[0]
    assert first.display_id == "HB-finding-f1"
    assert first.name == "Finding f1"
    assert first.rule_generator == constants.RULE_GENERATOR_FINDING
    assert first.priority == constants.PRIORITY_HIGH
    assert first.device_product == "Huntbase"
    assert first.start_time <= first.end_time
    events = first.events
    assert events[0]["event_type"] == "Huntbase Finding"
    assert events[0]["url"] == f"{common.APP_ROOT}/findings/f1?src=google_secops"
    entity_events = {k: v for e in events[1:] for k, v in e.items() if k in {"hostname", "ip", "file_hash"}}
    assert entity_events == {"hostname": "WS-0142", "ip": "203.0.113.10", "file_hash": "a" * 64}
    assert len(events) == 4
    assert all(isinstance(v, str) for e in events for v in e.values())

    assert _context(external_context, constants.PROCESSED_IDS_KEY) == ["finding:f1", "finding:f2"]
    watermarks = _context(external_context, constants.WATERMARK_KEY)
    assert watermarks["finding"].startswith(huntbase.findings[1]["created_at"][:19])
    params = dict(script_session.request_history[0].request.kwargs["params"])
    assert params["disposition"] == "confirmed"


@set_metadata(
    connector_def_file_path=common.CONNECTOR_DEF_PATH, parameters=_params(), external_context=MockExternalContext()
)
def test_second_run_dedupes(
    huntbase: Huntbase, connector_output: MockConnectorOutput, external_context: MockExternalContext
) -> None:
    huntbase.findings = [_finding("f1", 30)]
    connector.main(is_test_run=False)
    assert [a.ticket_id for a in _alerts(connector_output)] == ["f1"]

    connector_output.flush()
    huntbase.findings.append(_finding("f2", 5))
    connector.main(is_test_run=False)
    assert [a.ticket_id for a in _alerts(connector_output)] == ["f2"]
    assert _context(external_context, constants.PROCESSED_IDS_KEY) == ["finding:f1", "finding:f2"]


@set_metadata(
    connector_def_file_path=common.CONNECTOR_DEF_PATH,
    parameters=_params(**{"Max Alerts Per Cycle": "2"}),
    external_context=MockExternalContext(),
)
def test_max_alerts_and_paging(
    huntbase: Huntbase,
    script_session: HuntbaseSession,
    connector_output: MockConnectorOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(constants, "CONNECTOR_PAGE_SIZE", 1)
    huntbase.findings = [_finding(f"f{i}", 60 - i) for i in range(5)]

    connector.main(is_test_run=False)

    assert [a.ticket_id for a in _alerts(connector_output)] == ["f0", "f1"]
    assert len(script_session.request_history) == 2


@set_metadata(
    connector_def_file_path=common.CONNECTOR_DEF_PATH,
    parameters=_params(Source="Findings and Insights", **{"Lowest Insight Severity": "high"}),
    external_context=MockExternalContext(),
)
def test_findings_and_insights(huntbase: Huntbase, connector_output: MockConnectorOutput) -> None:
    huntbase.findings = [_finding("f1", 30, severity="medium")]
    huntbase.insights = [
        _insight("i-low", 40, "low"),
        _insight("i-high", 35, "high"),
        _insight("i-crit", 5, "critical"),
    ]

    connector.main(is_test_run=False)

    alerts = _alerts(connector_output)
    assert [a.ticket_id for a in alerts] == ["i-high", "f1", "i-crit"]
    insight_alert = alerts[0]
    assert insight_alert.rule_generator == "Suspicious PowerShell"
    assert insight_alert.priority == constants.PRIORITY_HIGH
    assert alerts[1].priority == constants.PRIORITY_MEDIUM
    assert alerts[2].priority == constants.PRIORITY_CRITICAL
    fields = {k: v for e in insight_alert.events[1:] for k, v in e.items() if k in {"hostname", "user"}}
    assert fields == {"hostname": "ws-9", "user": "bob"}


@set_metadata(
    connector_def_file_path=common.CONNECTOR_DEF_PATH, parameters=_params(), external_context=MockExternalContext()
)
def test_overflow_is_skipped_but_remembered(
    huntbase: Huntbase, connector_output: MockConnectorOutput, external_context: MockExternalContext
) -> None:
    huntbase.findings = [_finding("overflow", 30), _finding("f2", 20)]

    connector.main(is_test_run=False)

    assert [a.ticket_id for a in _alerts(connector_output)] == ["f2"]
    assert _context(external_context, constants.PROCESSED_IDS_KEY) == ["finding:overflow", "finding:f2"]


@set_metadata(
    connector_def_file_path=common.CONNECTOR_DEF_PATH, parameters=_params(), external_context=MockExternalContext()
)
def test_test_run_does_not_save_state(
    huntbase: Huntbase, connector_output: MockConnectorOutput, external_context: MockExternalContext
) -> None:
    huntbase.findings = [_finding(f"f{i}", 60 - i) for i in range(8)]

    connector.main(is_test_run=True)

    assert len(_alerts(connector_output)) == constants.CONNECTOR_TEST_RUN_MAX_ALERTS
    assert _context(external_context, constants.PROCESSED_IDS_KEY) is None


@set_metadata(
    connector_def_file_path=common.CONNECTOR_DEF_PATH, parameters=_params(), external_context=MockExternalContext()
)
def test_api_error_returns_empty_package(
    huntbase: Huntbase, connector_output: MockConnectorOutput, external_context: MockExternalContext
) -> None:
    huntbase.fail("findings", 401)

    connector.main(is_test_run=False)

    assert _alerts(connector_output) == []
    assert _context(external_context, constants.WATERMARK_KEY) is None


@set_metadata(
    connector_def_file_path=common.CONNECTOR_DEF_PATH, parameters=_params(), external_context=MockExternalContext()
)
def test_api_error_raises_in_test_run(huntbase: Huntbase, connector_output: MockConnectorOutput) -> None:
    huntbase.fail("findings", 401)

    with pytest.raises(Exception, match="rejected the API key"):
        connector.main(is_test_run=True)


@set_metadata(
    connector_def_file_path=common.CONNECTOR_DEF_PATH,
    parameters=_params(Source="Everything"),
    external_context=MockExternalContext(),
)
def test_invalid_source(script_session: HuntbaseSession, connector_output: MockConnectorOutput) -> None:
    connector.main(is_test_run=False)

    assert _alerts(connector_output) == []
    assert script_session.request_history == []


def test_insight_overlap_moves_since_back() -> None:
    saved = _iso(30)
    since = connector.initial_watermark({"insight": saved}, "insight", 24, overlap_minutes=60)
    assert since < saved


@set_metadata(
    connector_def_file_path=common.CONNECTOR_DEF_PATH,
    parameters=_params(Source="Insights"),
    external_context=MockExternalContext(),
)
def test_insights_second_run_dedupes_overlap(huntbase: Huntbase, connector_output: MockConnectorOutput) -> None:
    huntbase.insights = [_insight("i1", 20, "high")]
    connector.main(is_test_run=False)
    assert [a.ticket_id for a in _alerts(connector_output)] == ["i1"]

    connector_output.flush()
    huntbase.insights.append(_insight("i2", 10, "critical"))
    connector.main(is_test_run=False)
    assert [a.ticket_id for a in _alerts(connector_output)] == ["i2"]


def test_initial_watermark_respects_floor() -> None:
    old = "2020-01-01T00:00:00Z"
    recent = _iso(5)
    floor = connector.initial_watermark({"finding": old}, "finding", 1)
    assert floor > old
    assert connector.initial_watermark({"finding": recent}, "finding", 1).startswith(recent[:19])
