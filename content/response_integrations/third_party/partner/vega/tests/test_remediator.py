"""Tests for connector close-sync: status-only, exclusive incident vs alert paths."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from core.Remediator import (
    SoarRemediator,
    extract_sync_targets,
    ingest_skip_ids,
    ingest_sync_refs,
    ingest_ticket_ids,
    is_soar_case_closed,
)

PRIOR_STATE = {"last_check_ms": 1_700_000_000_000, "processed_ids": []}
AFTER_BASELINE_MS = PRIOR_STATE["last_check_ms"] + 60_000
BEFORE_BASELINE_MS = PRIOR_STATE["last_check_ms"] - 60_000


def _state(*tickets: str) -> dict:
    state = dict(PRIOR_STATE)
    if tickets:
        state["tracked_tickets"] = list(tickets)
    return state


def _closed(payload: dict) -> dict:
    updated = dict(payload)
    updated.setdefault("isClosed", True)
    return updated


class FakeManager:
    def __init__(self) -> None:
        self.resolved_incidents: list[list[str]] = []
        self.resolved_alerts: list[list[str]] = []

    def resolve_incidents(self, incident_ids):
        self.resolved_incidents.append(list(incident_ids))
        return {"incidents": [{"incidentId": item, "userStatus": "RESOLVED"} for item in incident_ids]}

    def resolve_alerts(self, alert_ids):
        self.resolved_alerts.append(list(alert_ids))
        return {"alerts": [{"id": item, "status": "RESOLVED"} for item in alert_ids]}


class FakeResponse:
    def __init__(self, payload, status=200) -> None:
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, results, details, recent=None) -> None:
        self.results = results
        self.recent = recent
        self.details = details
        self.posts: list[tuple] = []
        self.gets: list[str] = []

    def post(self, url, json=None, timeout=None):
        self.posts.append((url, json))
        payload = json or {}
        if payload.get("isCaseClosed") and "title" not in payload:
            rows = self.recent if self.recent is not None else self.results
            return FakeResponse({"results": rows})
        return FakeResponse({"results": self.results})

    def get(self, url, timeout=None):
        self.gets.append(url)
        case_id = url.split("GetCaseFullDetails/")[-1].split("?")[0]
        return FakeResponse(self.details.get(case_id) or {})


def _siemplify(ticket_cases: dict) -> SimpleNamespace:
    def _tickets(_since_ms):
        return list(ticket_cases)

    def _case(ticket_id):
        return ticket_cases.get(ticket_id) or {}

    return SimpleNamespace(
        get_alerts_ticket_ids_from_cases_closed_since_timestamp=_tickets,
        get_cases_by_ticket_id=_case,
    )


def _rest_siemplify(results, details, environment="Default Environment") -> SimpleNamespace:
    return SimpleNamespace(
        API_ROOT="https://soar.example",
        session=FakeSession(results, details),
        context=SimpleNamespace(connector_info=SimpleNamespace(environment=environment)),
    )


def test_first_run_baselines_without_syncing_history() -> None:
    manager = FakeManager()
    siemplify = _siemplify({"Vega:alert-3": _closed({"events": [{"vega_entity_type": "Alert", "vega_id": "alert-3"}]})})
    result = SoarRemediator(manager, siemplify).run_once({})
    assert manager.resolved_alerts == []
    assert manager.resolved_incidents == []
    assert "baseline" in result["message"].lower()
    assert int(result["state"]["last_check_ms"]) > 0


def test_close_unrelated_alert_resolves_that_alert_only() -> None:
    manager = FakeManager()
    siemplify = _siemplify({"Vega:alert-3": _closed({"events": [{"vega_entity_type": "Alert", "vega_id": "alert-3"}]})})
    result = SoarRemediator(manager, siemplify).run_once(_state("Vega:alert-3"))
    assert manager.resolved_alerts == [["alert-3"]]
    assert manager.resolved_incidents == []
    assert "Synced 1" in result["message"]
    assert "case:" not in "".join(result["state"]["processed_ids"])
    assert "alert-3" in result["state"]["processed_ids"]


def test_close_incident_case_resolves_incident_not_related_alerts() -> None:
    manager = FakeManager()
    siemplify = _siemplify({
        "Vega:inc-1": _closed({
            "events": [
                {"vega_entity_type": "Incident", "vega_id": "inc-1"},
                {
                    "vega_entity_type": "Alert",
                    "vega_id": "alert-1",
                    "vega_incident_id": "inc-1",
                },
            ]
        })
    })
    SoarRemediator(manager, siemplify).run_once(_state("Vega:inc-1"))
    assert manager.resolved_incidents == [["inc-1"]]
    assert manager.resolved_alerts == []


def test_close_related_batch_resolves_alerts_not_incident() -> None:
    manager = FakeManager()
    payload = {
        "events": [
            {
                "vega_entity_type": "Alert",
                "vega_id": "alert-4",
                "vega_incident_id": "inc-1",
            },
            {
                "vega_entity_type": "Alert",
                "vega_id": "alert-5",
                "vega_incident_id": "inc-1",
            },
        ]
    }
    siemplify = _siemplify({"Vega:alert-4": _closed(payload), "Vega:alert-5": _closed(payload)})
    SoarRemediator(manager, siemplify).run_once(_state("Vega:alert-4", "Vega:alert-5"))
    assert manager.resolved_incidents == []
    assert manager.resolved_alerts == [["alert-4", "alert-5"]]


def test_close_sync_falls_back_to_rest_without_sdk() -> None:
    manager = FakeManager()
    siemplify = SimpleNamespace(
        get_alerts_ticket_ids_from_cases_closed_since_timestamp=lambda _since: ["Vega:alert-3"],
        get_cases_by_ticket_id=None,
        API_ROOT="",
        session=None,
    )
    result = SoarRemediator(manager, siemplify).run_once(dict(PRIOR_STATE))
    assert manager.resolved_alerts == []
    assert manager.resolved_incidents == []
    assert "Synced 0" in result["message"]


def test_job_sdk_two_arg_signature_uses_rest_search() -> None:
    manager = FakeManager()

    def _job_sdk(_since, _rule_generator):
        raise AssertionError("must not guess a Vega rule generator")

    session = FakeSession(
        [{"id": "7", "title": "Vega Alert - alert-3 - brute force"}],
        {
            "7": {
                "id": 7,
                "isClosed": True,
                "closedTime": AFTER_BASELINE_MS,
                "cyberAlerts": [
                    {
                        "ticketId": "Vega:alert-3",
                        "securityEvents": [
                            {"additionalProperties": json.dumps({"vega_id": "alert-3", "vega_entity_type": "Alert"})}
                        ],
                    }
                ],
            }
        },
    )
    siemplify = SimpleNamespace(
        get_alerts_ticket_ids_from_cases_closed_since_timestamp=_job_sdk,
        get_cases_by_ticket_id=lambda _ticket: {},
        API_ROOT="https://soar.example",
        session=session,
        context=SimpleNamespace(connector_info=SimpleNamespace(environment="Default Environment")),
    )
    SoarRemediator(manager, siemplify).run_once(_state("Vega:alert-3"))
    assert manager.resolved_alerts == [["alert-3"]]
    assert manager.resolved_incidents == []
    assert session.posts
    assert "CaseSearchEverything" in session.posts[0][0]


def test_rest_search_resolves_incident_from_nested_case_details() -> None:
    manager = FakeManager()
    siemplify = _rest_siemplify(
        [{"id": "42", "title": "Vega Incident - INC-1 - phishing"}],
        {
            "42": {
                "id": 42,
                "isClosed": True,
                "closedTime": AFTER_BASELINE_MS,
                "title": "Vega Incident - INC-1 - phishing",
                "cyberAlerts": [
                    {
                        "ticketId": "Vega:inc-1",
                        "securityEvents": [
                            {
                                "additionalProperties": json.dumps({
                                    "vega_id": "inc-1",
                                    "vega_entity_type": "Incident",
                                })
                            },
                            {
                                "additionalProperties": json.dumps({
                                    "vega_id": "alert-1",
                                    "vega_entity_type": "Alert",
                                    "vega_incident_id": "inc-1",
                                })
                            },
                        ],
                    }
                ],
            }
        },
    )
    result = SoarRemediator(manager, siemplify).run_once(_state("Vega:inc-1"))
    assert manager.resolved_incidents == [["inc-1"]]
    assert manager.resolved_alerts == []
    assert "case:42" in result["state"]["processed_ids"]
    assert "inc-1" in result["state"]["processed_ids"]
    posted = siemplify.session.posts[0][1]
    assert posted.get("isCaseClosed") is True
    assert posted.get("title") == "Vega"
    assert posted.get("timeRangeFilter") == 1
    assert posted["environments"] == ["Default Environment"]


def test_rest_camel_case_incident_resolves_uuid_not_vinc() -> None:
    uuid = "019eea19-551b-7b19-8582-faff640969ff"
    manager = FakeManager()
    siemplify = _rest_siemplify(
        [{"id": "42", "title": "Vega Incident - VINC-1 - phishing"}],
        {
            "42": {
                "id": 42,
                "isClosed": True,
                "closedTime": AFTER_BASELINE_MS,
                "title": "Vega Incident - VINC-1 - phishing",
                "cyberAlerts": [
                    {
                        "ticketId": f"Vega:{uuid}",
                        "additionalProperties": {
                            "vegaId": uuid,
                            "vegaEntityType": "Incident",
                            "vegaUniqueIncidentId": "VINC-1",
                        },
                    }
                ],
            }
        },
    )
    result = SoarRemediator(manager, siemplify).run_once(_state(f"Vega:{uuid}"))
    assert manager.resolved_incidents == [[uuid]]
    assert manager.resolved_alerts == []
    assert "Synced 1" in result["message"]


def test_rest_incident_ticket_only_when_events_dropped() -> None:
    uuid = "019eea19-551b-7b19-8582-faff640969ff"
    manager = FakeManager()
    siemplify = _rest_siemplify(
        [{"id": "42", "title": "Vega Incident - VINC-1 - phishing"}],
        {
            "42": {
                "id": 42,
                "isClosed": True,
                "closedTime": AFTER_BASELINE_MS,
                "title": "Vega Incident - VINC-1 - phishing",
                "cyberAlerts": [{"ticketId": f"Vega:{uuid}"}],
            }
        },
    )
    result = SoarRemediator(manager, siemplify).run_once(
        _state(f"Vega:{uuid}"),
        ingest_refs=[
            {
                "ticket": f"Vega:{uuid}",
                "tokens": [uuid, "VINC-1"],
                "title": "Vega Incident - VINC-1 - phishing",
            }
        ],
    )
    assert manager.resolved_incidents == [[uuid]]
    assert manager.resolved_alerts == []
    assert "Synced 1" in result["message"]


def test_extract_sync_targets_skips_child_events_on_related_batch() -> None:
    targets = extract_sync_targets({
        "events": [
            {
                "vega_entity_type": "Alert",
                "vega_id": "alert-1",
                "vega_incident_id": "inc-1",
            },
            {
                "vega_entity_type": "Alert Event",
                "vega_id": "alert-1:event:0",
                "vega_incident_id": "inc-1",
            },
        ]
    })
    assert targets["mode"] == "alerts"
    assert targets["alert_ids"] == ["alert-1"]
    assert targets["incident_ids"] == []


def test_extract_sync_targets_reads_json_additional_properties() -> None:
    targets = extract_sync_targets({
        "cyberAlerts": [
            {
                "securityEvents": [
                    {
                        "additionalProperties": json.dumps({
                            "vega_id": "alert-9",
                            "vega_entity_type": "Alert",
                        })
                    }
                ]
            }
        ]
    })
    assert targets["mode"] == "alerts"
    assert targets["alert_ids"] == ["alert-9"]


def test_resolve_helpers_are_used_not_full_update() -> None:
    manager = MagicMock()
    manager.resolve_incidents = MagicMock(return_value={})
    manager.resolve_alerts = MagicMock(return_value={})
    manager.update_incidents = MagicMock()
    manager.update_alerts = MagicMock()
    siemplify = _siemplify({"Vega:inc-1": _closed({"events": [{"vega_entity_type": "Incident", "vega_id": "inc-1"}]})})
    SoarRemediator(manager, siemplify).run_once(_state("Vega:inc-1"))
    manager.resolve_incidents.assert_called_once_with(["inc-1"])
    manager.update_incidents.assert_not_called()
    manager.update_alerts.assert_not_called()
    manager.resolve_alerts.assert_not_called()


def test_open_ingested_case_does_not_resolve_vega() -> None:
    manager = FakeManager()
    siemplify = _siemplify({
        "Vega:alert-3": {
            "isClosed": False,
            "lastUpdateTime": 1_800_000_000_000,
            "events": [{"vega_entity_type": "Alert", "vega_id": "alert-3"}],
        }
    })
    SoarRemediator(manager, siemplify).run_once(dict(PRIOR_STATE))
    assert manager.resolved_alerts == []
    assert manager.resolved_incidents == []


def test_rest_open_case_with_update_time_does_not_resolve() -> None:
    manager = FakeManager()
    siemplify = _rest_siemplify(
        [
            {
                "id": "9",
                "title": "Vega Alert - alert-3 - Noise",
                "isClosed": False,
                "lastUpdateTime": 1_800_000_000_000,
            }
        ],
        {
            "9": {
                "id": 9,
                "isClosed": False,
                "lastUpdateTime": 1_800_000_000_000,
                "title": "Vega Alert - alert-3 - Noise",
                "events": [{"vega_entity_type": "Alert", "vega_id": "alert-3"}],
            }
        },
    )
    SoarRemediator(manager, siemplify).run_once(_state("Vega:alert-3"))
    assert manager.resolved_alerts == []
    assert manager.resolved_incidents == []


def test_is_soar_case_closed_requires_explicit_closed_flag() -> None:
    assert is_soar_case_closed({"isClosed": True})
    assert is_soar_case_closed({"isCaseClosed": True})
    assert is_soar_case_closed({"statusName": "CLOSED"})
    assert is_soar_case_closed({"status": 2})
    assert not is_soar_case_closed({"status": "RESOLVED"})
    assert not is_soar_case_closed({"status": "RESOLVED", "vega_id": "alert-3", "vega_entity_type": "Alert"})
    assert not is_soar_case_closed({"status": 2, "vega_id": "alert-3", "vega_entity_type": "Alert"})
    assert not is_soar_case_closed({"isClosed": False, "lastUpdateTime": 1})
    assert not is_soar_case_closed({"status": 1, "updateTime": 1})
    assert not is_soar_case_closed({"lastUpdateTime": 1_800_000_000_000})
    assert not is_soar_case_closed({})


def test_vega_status_on_ingested_case_does_not_resolve() -> None:
    manager = FakeManager()
    siemplify = _siemplify({
        "Vega:alert-3": {
            "status": "RESOLVED",
            "lastUpdateTime": 1_800_000_000_000,
            "events": [
                {
                    "vega_entity_type": "Alert",
                    "vega_id": "alert-3",
                    "status": "RESOLVED",
                }
            ],
        }
    })
    SoarRemediator(manager, siemplify).run_once(dict(PRIOR_STATE))
    assert manager.resolved_alerts == []
    assert manager.resolved_incidents == []


def test_rest_search_ignores_vega_status_on_open_case() -> None:
    manager = FakeManager()
    siemplify = _rest_siemplify(
        [{"id": "9", "title": "Vega Alert - alert-3 - Noise", "status": "RESOLVED"}],
        {
            "9": {
                "id": 9,
                "status": "RESOLVED",
                "lastUpdateTime": 1_800_000_000_000,
                "title": "Vega Alert - alert-3 - Noise",
                "events": [
                    {
                        "vega_entity_type": "Alert",
                        "vega_id": "alert-3",
                        "status": "RESOLVED",
                    }
                ],
            }
        },
    )
    SoarRemediator(manager, siemplify).run_once(_state("Vega:alert-3"))
    assert manager.resolved_alerts == []
    assert manager.resolved_incidents == []


def test_connector_with_sdk_prefers_rest_closed_search() -> None:
    manager = FakeManager()
    session = FakeSession(
        [
            {
                "id": "9",
                "title": "Vega Alert - alert-3 - Noise",
                "isClosed": False,
                "lastUpdateTime": 1_800_000_000_000,
            }
        ],
        {
            "9": {
                "id": 9,
                "isClosed": False,
                "status": "RESOLVED",
                "events": [{"vega_entity_type": "Alert", "vega_id": "alert-3"}],
            }
        },
    )
    siemplify = SimpleNamespace(
        get_alerts_ticket_ids_from_cases_closed_since_timestamp=lambda _since: ["Vega:alert-3"],
        get_cases_by_ticket_id=lambda _ticket: _closed({
            "events": [{"vega_entity_type": "Alert", "vega_id": "alert-3"}]
        }),
        API_ROOT="https://soar.example",
        session=session,
        context=SimpleNamespace(connector_info=SimpleNamespace(environment="Default Environment")),
    )
    SoarRemediator(manager, siemplify).run_once(_state("Vega:alert-3"))
    assert manager.resolved_alerts == []
    assert manager.resolved_incidents == []
    assert session.posts


def test_skip_ids_does_not_resolve_current_ingest() -> None:
    manager = FakeManager()
    siemplify = _siemplify({
        "Vega:alert-3": _closed({"id": "9", "events": [{"vega_entity_type": "Alert", "vega_id": "alert-3"}]})
    })
    result = SoarRemediator(manager, siemplify).run_once(dict(PRIOR_STATE), skip_ids={"alert-3"})
    assert manager.resolved_alerts == []
    assert manager.resolved_incidents == []
    assert "case:9" not in result["state"]["processed_ids"]
    assert "alert-3" not in result["state"]["processed_ids"]


def test_previous_ingest_ids_are_resolved_on_next_poll() -> None:
    manager = FakeManager()
    siemplify = _siemplify({
        "Vega:alert-3": _closed({"id": "9", "events": [{"vega_entity_type": "Alert", "vega_id": "alert-3"}]})
    })
    state = _state("Vega:alert-3")
    state["recent_ingest_ids"] = ["alert-3"]
    result = SoarRemediator(manager, siemplify).run_once(state)
    assert manager.resolved_alerts == [["alert-3"]]
    assert result["state"]["recent_ingest_ids"] == []


def test_ingest_skip_ids_collects_alert_and_incident_ids() -> None:
    records = [
        ("Incident", {"id": "inc-1", "nested_related_alerts": [{"id": "alert-9"}]}),
        ("Alert", {"id": "uuid-1", "vegaAlertId": "ALRT-1"}),
    ]
    assert ingest_skip_ids(records) == {"inc-1", "alert-9", "uuid-1", "ALRT-1"}
    assert ingest_ticket_ids(records) == ["Vega:inc-1", "Vega:uuid-1"]
    refs = ingest_sync_refs(records)
    assert refs[1]["ticket"] == "Vega:uuid-1"
    assert "ALRT-1" in refs[1]["tokens"]
    assert "Vega Alert" in refs[1]["title"]


def test_rest_untracked_dump_does_not_resolve() -> None:
    manager = FakeManager()
    siemplify = _rest_siemplify(
        [{"id": "9", "title": "Vega Alert - alert-3 - Noise", "isCaseClosed": True}],
        {
            "9": {
                "id": 9,
                "isClosed": True,
                "status": 2,
                "title": "Vega Alert - alert-3 - Noise",
                "events": [{"vega_entity_type": "Alert", "vega_id": "alert-3"}],
            }
        },
    )
    result = SoarRemediator(manager, siemplify).run_once(dict(PRIOR_STATE))
    assert manager.resolved_alerts == []
    assert manager.resolved_incidents == []
    assert "Synced 0" in result["message"]
    assert siemplify.session.posts == []
    assert siemplify.session.gets == []


def test_rest_search_closed_flag_does_not_override_open_details() -> None:
    manager = FakeManager()
    siemplify = _rest_siemplify(
        [{"id": "9", "title": "Vega Alert - alert-3", "isCaseClosed": True}],
        {
            "9": {
                "id": 9,
                "isClosed": False,
                "events": [{"vega_entity_type": "Alert", "vega_id": "alert-3"}],
            }
        },
    )
    SoarRemediator(manager, siemplify).run_once(_state("Vega:alert-3"))
    assert manager.resolved_alerts == []
    assert manager.resolved_incidents == []


def test_rest_closed_without_close_time_resolves() -> None:
    manager = FakeManager()
    siemplify = _rest_siemplify(
        [{"id": "9", "title": "Vega Alert - alert-3"}],
        {
            "9": {
                "id": 9,
                "isClosed": True,
                "events": [{"vega_entity_type": "Alert", "vega_id": "alert-3"}],
            }
        },
    )
    result = SoarRemediator(manager, siemplify).run_once(_state("Vega:alert-3"))
    assert manager.resolved_alerts == [["alert-3"]]
    assert "Synced 1" in result["message"]


def test_rest_status_2_on_details_resolves() -> None:
    manager = FakeManager()
    siemplify = _rest_siemplify(
        [{"id": "9", "title": "Vega Alert - alert-3"}],
        {
            "9": {
                "id": 9,
                "status": 2,
                "events": [{"vega_entity_type": "Alert", "vega_id": "alert-3"}],
            }
        },
    )
    result = SoarRemediator(manager, siemplify).run_once(_state("Vega:alert-3"))
    assert manager.resolved_alerts == [["alert-3"]]
    assert "Synced 1" in result["message"]


def test_rest_unfiltered_dump_still_syncs_matching_ticket() -> None:
    manager = FakeManager()
    results = [
        {
            "id": str(index),
            "title": f"Vega Alert {index}",
            "isCaseClosed": True,
            "updateTime": BEFORE_BASELINE_MS,
        }
        for index in range(50)
    ]
    results.append({
        "id": "9",
        "title": "Vega Alert - alert-3",
        "ticketId": "Vega:alert-3",
        "isCaseClosed": True,
        "updateTime": AFTER_BASELINE_MS,
    })
    session = FakeSession(
        results,
        {
            "9": {
                "id": 9,
                "status": 2,
                "closedTime": AFTER_BASELINE_MS,
                "events": [{"vega_entity_type": "Alert", "vega_id": "alert-3"}],
            }
        },
    )
    siemplify = SimpleNamespace(
        API_ROOT="https://soar.example",
        session=session,
        context=SimpleNamespace(connector_info=SimpleNamespace(environment="Default Environment")),
    )
    result = SoarRemediator(manager, siemplify).run_once(_state("Vega:alert-3"))
    assert manager.resolved_alerts == [["alert-3"]]
    assert "Synced 1" in result["message"]
    assert session.gets == ["https://soar.example/external/v1/cases/GetCaseFullDetails/9?format=camel"]


def test_rest_dump_of_old_ingested_closes_does_not_sync() -> None:
    results = [
        {
            "id": str(index),
            "title": "Vega Alert - alert-3 - old",
            "isCaseClosed": True,
            "updateTime": BEFORE_BASELINE_MS,
        }
        for index in range(50)
    ]
    siemplify = _rest_siemplify(
        results,
        {
            "0": {
                "id": 0,
                "isClosed": True,
                "closedTime": BEFORE_BASELINE_MS,
                "events": [{"vega_entity_type": "Alert", "vega_id": "alert-3"}],
            }
        },
    )
    result = SoarRemediator(FakeManager(), siemplify).run_once(_state("Vega:alert-3"))
    assert result["message"].startswith("Synced 0")
    assert siemplify.session.gets == []


def test_rest_dump_without_timestamps_does_not_sync() -> None:
    results = [{"id": str(index), "title": f"Vega Alert {index}", "isCaseClosed": True} for index in range(50)]
    results[0] = {
        "id": "9",
        "title": "Vega Alert - alert-3 - old",
        "isCaseClosed": True,
    }
    siemplify = _rest_siemplify(
        results,
        {
            "9": {
                "id": 9,
                "isClosed": True,
                "events": [{"vega_entity_type": "Alert", "vega_id": "alert-3"}],
            }
        },
    )
    remediator = SoarRemediator(FakeManager(), siemplify)
    result = remediator.run_once(_state("Vega:alert-3"))
    assert result["message"].startswith("Synced 0")
    assert siemplify.session.gets == ["https://soar.example/external/v1/cases/GetCaseFullDetails/9?format=camel"]
    assert "case:9" in result["state"]["processed_ids"]

    siemplify.session.gets.clear()
    again = remediator.run_once(result["state"])
    assert again["message"].startswith("Synced 0")
    assert siemplify.session.gets == []


def test_rest_dump_without_summary_time_syncs_recent_details() -> None:
    results = [{"id": str(index), "title": f"Vega Alert {index}", "isCaseClosed": True} for index in range(50)]
    results[0] = {
        "id": "9",
        "title": "Vega Alert - alert-3",
        "isCaseClosed": True,
    }
    manager = FakeManager()
    siemplify = _rest_siemplify(
        results,
        {
            "9": {
                "id": 9,
                "isClosed": True,
                "closedTime": AFTER_BASELINE_MS,
                "events": [{"vega_entity_type": "Alert", "vega_id": "alert-3"}],
            }
        },
    )
    result = SoarRemediator(manager, siemplify).run_once(_state("Vega:alert-3"))
    assert manager.resolved_alerts == [["alert-3"]]
    assert "Synced 1" in result["message"]
    assert siemplify.session.gets == ["https://soar.example/external/v1/cases/GetCaseFullDetails/9?format=camel"]


def test_rest_dump_matching_old_details_does_not_sync() -> None:
    results = [{"id": str(index), "title": f"Vega Alert {index}", "isCaseClosed": True} for index in range(50)]
    results[0] = {
        "id": "9",
        "title": "Vega Alert - alert-3 - old",
        "isCaseClosed": True,
    }
    manager = FakeManager()
    siemplify = _rest_siemplify(
        results,
        {
            "9": {
                "id": 9,
                "isClosed": True,
                "closedTime": BEFORE_BASELINE_MS,
                "events": [{"vega_entity_type": "Alert", "vega_id": "alert-3"}],
            }
        },
    )
    result = SoarRemediator(manager, siemplify).run_once(_state("Vega:alert-3"))
    assert manager.resolved_alerts == []
    assert result["message"].startswith("Synced 0")
    assert siemplify.session.gets == ["https://soar.example/external/v1/cases/GetCaseFullDetails/9?format=camel"]
    assert "case:9" in result["state"]["processed_ids"]


def test_rest_uuid_ticket_matches_closed_case_events() -> None:
    uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    manager = FakeManager()
    siemplify = _rest_siemplify(
        [
            {"id": "1", "title": "Vega Alert - ALRT-99 - old close", "isCaseClosed": True},
            {"id": "9", "title": "Vega Alert - ALRT-1 - brute force", "isCaseClosed": True},
        ],
        {
            "1": {
                "id": 1,
                "isClosed": True,
                "events": [{"vega_entity_type": "Alert", "vega_id": "other-uuid"}],
            },
            "9": {
                "id": 9,
                "status": 2,
                "events": [{"vega_entity_type": "Alert", "vega_id": uuid}],
            },
        },
    )
    result = SoarRemediator(manager, siemplify).run_once(_state(f"Vega:{uuid}"))
    assert manager.resolved_alerts == [[uuid]]
    assert manager.resolved_incidents == []
    assert "Synced 1" in result["message"]


def test_rest_pascal_case_search_row_and_nested_details() -> None:
    uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    manager = FakeManager()
    siemplify = _rest_siemplify(
        [{"Id": "9", "Title": "Vega Alert - ALRT-1 - brute force", "IsCaseClosed": True}],
        {
            "9": {
                "Id": 9,
                "Status": 2,
                "involvedRelations": [{"eventClassId": uuid, "vega_entity_type": "Alert"}],
            }
        },
    )
    result = SoarRemediator(manager, siemplify).run_once(_state(f"Vega:{uuid}"))
    assert manager.resolved_alerts == [[uuid]]
    assert "Synced 1" in result["message"]


def test_rest_dump_skips_untracked_historical_closes() -> None:
    uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    historical = [{"id": str(index), "title": f"Vega Alert {index}", "isCaseClosed": True} for index in range(50)]
    historical[0] = {
        "id": "99",
        "title": "Vega Alert - ALRT-1 - brute force",
        "isCaseClosed": True,
        "updateTime": AFTER_BASELINE_MS,
    }
    session = FakeSession(
        historical,
        {
            "99": {
                "id": 99,
                "isClosed": True,
                "closedTime": AFTER_BASELINE_MS,
                "events": [{"vega_entity_type": "Alert", "vega_id": uuid}],
            }
        },
    )
    siemplify = SimpleNamespace(
        API_ROOT="https://soar.example",
        session=session,
        context=SimpleNamespace(connector_info=SimpleNamespace(environment="Default Environment")),
    )
    manager = FakeManager()
    result = SoarRemediator(manager, siemplify).run_once(
        _state(f"Vega:{uuid}"),
        ingest_refs=[
            {
                "ticket": f"Vega:{uuid}",
                "tokens": [uuid, "ALRT-1"],
                "title": "Vega Alert - ALRT-1 - brute force",
            }
        ],
    )
    assert manager.resolved_alerts == [[uuid]]
    assert "Synced 1" in result["message"]
    assert session.gets == ["https://soar.example/external/v1/cases/GetCaseFullDetails/99?format=camel"]


def test_rest_empty_closed_search_does_not_sync() -> None:
    class ClosedEmptySession(FakeSession):
        def post(self, url, json=None, timeout=None):
            self.posts.append((url, json))
            return FakeResponse({"results": []})

    session = ClosedEmptySession(
        [],
        {
            "9": {
                "id": 9,
                "isClosed": True,
                "events": [
                    {
                        "vega_entity_type": "Alert",
                        "vega_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    }
                ],
            }
        },
    )
    siemplify = SimpleNamespace(
        API_ROOT="https://soar.example",
        session=session,
        context=SimpleNamespace(connector_info=SimpleNamespace(environment="Default Environment")),
    )
    manager = FakeManager()
    result = SoarRemediator(manager, siemplify).run_once(_state("Vega:a1b2c3d4-e5f6-7890-abcd-ef1234567890"))
    assert manager.resolved_alerts == []
    assert "Synced 0" in result["message"]


def test_ingest_refs_enrich_existing_uuid_tickets() -> None:
    manager = FakeManager()
    result = SoarRemediator(manager, _siemplify({})).run_once(
        _state("Vega:uuid-1"),
        ingest_refs=[
            {
                "ticket": "Vega:uuid-1",
                "tokens": ["uuid-1", "ALRT-1"],
                "title": "Vega Alert - ALRT-1 - brute force",
            }
        ],
    )
    refs = result["state"]["tracked_refs"]
    assert refs[0]["ticket"] == "Vega:uuid-1"
    assert "ALRT-1" in refs[0]["tokens"]
    assert "ALRT-1" in refs[0]["title"]
    assert manager.resolved_alerts == []


def test_first_run_stores_ingest_tickets() -> None:
    manager = FakeManager()
    result = SoarRemediator(manager, _siemplify({})).run_once({}, ingest_tickets=["Vega:alert-3"])
    assert "baseline" in result["message"].lower()
    assert result["state"]["tracked_tickets"] == ["Vega:alert-3"]
    assert manager.resolved_alerts == []
