"""getAlertsEvents alertIds batching keeps each alert's events separate."""

from __future__ import annotations

from core.constants import ALERT_EVENTS_ID_BATCH, GET_ALERT_EVENTS_QUERY
from core.rate_limit import RateLimitController
from core.VegaManager import VegaClientConfig, VegaManager, events_for_alert_bucket


class _DummySession:
    trust_env = False
    verify = True


def _manager():
    manager = VegaManager(
        VegaClientConfig(
            api_root="https://api.vega.io",
            access_key_id="kid",
            access_key="secret",
        ),
        session=_DummySession(),
        rate_limiter=RateLimitController(sleeper=lambda _seconds: None),
        sleeper=lambda _seconds: None,
    )
    manager._jwt = "token"
    return manager


def _uuid(index: int) -> str:
    return f"019e1b27-5119-7822-bde3-{index:012d}"


def test_events_for_alert_bucket_drops_other_alert_rows() -> None:
    kept, dropped = events_for_alert_bucket(
        [
            {"name": "mine", "alertId": _uuid(1)},
            {"name": "untagged"},
            {"name": "theirs", "alertId": _uuid(2)},
        ],
        _uuid(1),
    )
    assert [item["name"] for item in kept] == ["mine", "untagged"]
    assert dropped == 1


def test_alert_events_batch_assigns_each_alert_only_its_rows() -> None:
    manager = _manager()
    calls: list[dict] = []
    store = {
        _uuid(1): [{"name": "a1", "alertId": _uuid(1)}, {"name": "a2"}],
        _uuid(2): [{"name": "b1", "alertId": _uuid(2)}],
        _uuid(3): [{"name": "c1"}],
    }

    def graphql(_query, variables):
        assert _query == GET_ALERT_EVENTS_QUERY
        calls.append(dict(variables))
        alert_ids = list(variables.get("alertIds") or [])
        assert "alertId" not in variables
        assert 1 <= len(alert_ids) <= ALERT_EVENTS_ID_BATCH
        offset = int(variables["offset"])
        limit = int(variables["limit"])
        alerts = []
        for alert_id in reversed(alert_ids):
            rows = store[alert_id]
            alerts.append({
                "alertId": alert_id,
                "total": len(rows),
                "results": rows[offset : offset + limit],
                "error": {},
            })
        mixed = [row for rows in store.values() for row in rows]
        return {
            "getAlertsEvents": {
                "total": 999,
                "results": mixed,
                "alerts": alerts,
                "error": {},
            }
        }

    manager.graphql = graphql
    fetched = manager.get_all_alerts_events(
        [_uuid(1), _uuid(2), _uuid(3)],
        page_size=1,
        max_records=10,
    )
    assert [item["name"] for item in fetched[_uuid(1)]] == ["a1", "a2"]
    assert [item["name"] for item in fetched[_uuid(2)]] == ["b1"]
    assert [item["name"] for item in fetched[_uuid(3)]] == ["c1"]
    assert calls[0]["alertIds"] == [_uuid(1), _uuid(2), _uuid(3)]
    assert calls[0]["offset"] == 0
    assert calls[1]["alertIds"] == [_uuid(1)]
    assert calls[1]["offset"] == 1
    assert all(len(call["alertIds"]) <= 10 for call in calls)


def test_alert_events_batch_never_sends_more_than_ten_ids() -> None:
    manager = _manager()
    calls: list[list[str]] = []
    ids = [_uuid(index) for index in range(1, 13)]

    def graphql(_query, variables):
        alert_ids = list(variables["alertIds"])
        calls.append(alert_ids)
        assert len(alert_ids) <= 10
        return {
            "getAlertsEvents": {
                "results": [{"name": "mixed-should-not-attach"}],
                "alerts": [
                    {
                        "alertId": alert_id,
                        "total": 1,
                        "results": [{"name": alert_id[-2:]}],
                        "error": {},
                    }
                    for alert_id in alert_ids
                ],
            }
        }

    manager.graphql = graphql
    fetched = manager.get_all_alerts_events(ids, page_size=100, max_records=5)
    assert [len(batch) for batch in calls] == [10, 2]
    for alert_id in ids:
        assert [item["name"] for item in fetched[alert_id]] == [alert_id[-2:]]
        assert "mixed-should-not-attach" not in {item["name"] for item in fetched[alert_id]}


def test_foreign_alert_bucket_is_not_attached() -> None:
    manager = _manager()

    def graphql(_query, variables):
        return {
            "getAlertsEvents": {
                "results": [{"name": "top-level"}],
                "alerts": [
                    {
                        "alertId": _uuid(9),
                        "total": 1,
                        "results": [{"name": "stolen"}],
                        "error": {},
                    }
                ],
            }
        }

    manager.graphql = graphql
    fetched = manager.get_all_alerts_events([_uuid(1)], page_size=10, max_records=10)
    assert fetched[_uuid(1)] == []


def test_single_non_uuid_uses_alert_id_variable() -> None:
    manager = _manager()
    calls: list[dict] = []

    def graphql(_query, variables):
        calls.append(dict(variables))
        return {
            "getAlertsEvents": {
                "total": 1,
                "results": [{"name": "legacy"}],
                "error": {},
            }
        }

    manager.graphql = graphql
    events = manager.get_all_alert_events("VEGA-123", page_size=10, max_records=10)
    assert calls == [{"limit": 10, "offset": 0, "alertId": "VEGA-123"}]
    assert [item["name"] for item in events] == ["legacy"]


def test_one_alert_error_does_not_drop_the_other_alerts_events() -> None:
    manager = _manager()

    def graphql(_query, variables):
        return {
            "getAlertsEvents": {
                "alerts": [
                    {
                        "alertId": _uuid(1),
                        "total": 0,
                        "results": [],
                        "error": {"code": "NOT_FOUND", "message": "missing"},
                    },
                    {
                        "alertId": _uuid(2),
                        "total": 1,
                        "results": [{"name": "kept"}],
                        "error": {},
                    },
                ]
            }
        }

    manager.graphql = graphql
    fetched = manager.get_all_alerts_events([_uuid(1), _uuid(2)])
    assert fetched[_uuid(1)] == []
    assert [item["name"] for item in fetched[_uuid(2)]] == ["kept"]
