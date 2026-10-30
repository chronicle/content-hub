import pytest
from core.constants import GRAPHQL_PAGE_SIZE, MSG_BAD_REQUEST, MSG_INVALID_ACCESS_KEY_ID
from core.exceptions import VegaBadRequestException, VegaUnauthorizedException, VegaValidationException
from core.utils import (
    ConnectorConfig,
    format_test_connection_summary,
    format_user_facing_error,
    resolve_incident_filters,
    validate_connector_fields,
)
from core.VegaManager import VegaClientConfig, VegaManager


class DummySession:
    trust_env = False
    verify = True


def _valid_config(**overrides) -> ConnectorConfig:
    values = {
        "api_root": "https://api.vega.io",
        "access_key_id": "kid",
        "access_key": "secret",
        "entities_raw": "Alerts,Incidents",
        "lookback_minutes": "5",
        "backfill_days": "30",
        "alert_severities": "LOW,HIGH",
        "alert_statuses": "",
        "alert_verdicts": "",
        "has_related": "Yes,No",
        "incident_severities": "",
        "incident_user_statuses": "",
        "incident_investigation_statuses": "",
        "incident_verdicts": "",
        "python_timeout": "930",
    }
    values.update(overrides)
    return ConnectorConfig(**values)


def _manager() -> VegaManager:
    return VegaManager(
        VegaClientConfig(
            api_root="https://api.vega.io",
            access_key_id="kid",
            access_key="secret",
        ),
        session=DummySession(),
        sleeper=lambda _seconds: None,
    )


def test_validate_connector_fields_accepts_valid_values() -> None:
    validate_connector_fields(_valid_config())


def test_validate_connector_fields_lists_every_invalid_field() -> None:
    with pytest.raises(VegaValidationException) as exc:
        validate_connector_fields(
            _valid_config(
                api_root="http://not-https.example",
                access_key_id="",
                entities_raw="Foo",
                lookback_minutes="999",
                alert_severities="URGENT",
                has_related="Maybe",
                python_timeout="abc",
            )
        )
    text = str(exc.value)
    assert "Cannot run the Vega Alerts and Incidents Connector" in text
    assert "API Root" in text
    assert "Access Key ID" in text
    assert "Vega Entities to Fetch" in text
    assert "Fetch Lookback (minutes)" in text
    assert "Alert Severities to Fetch" in text
    assert "Has Related Incidents" in text
    assert "PythonProcessTimeout" in text
    assert "URGENT" in text
    assert "Maybe" in text


def test_format_test_connection_summary_lists_counts() -> None:
    text = format_test_connection_summary(
        incident_count=12,
        related_alert_count=34,
        unrelated_alert_count=8,
        total_alert_count=42,
        sample_count=3,
    )
    assert "Successfully connected to Vega." in text
    assert "- Vega incidents: 12" in text
    assert "- Vega related alerts: 34" in text
    assert "- Vega unrelated alerts: 8" in text
    assert "- Total Vega alerts: 42" in text
    assert "Showing 3 sample alert(s) below. Nothing was ingested." in text


def test_format_test_connection_summary_hides_unrelated_when_yes_only() -> None:
    text = format_test_connection_summary(
        incident_count=3,
        related_alert_count=1,
        unrelated_alert_count=105,
        total_alert_count=1,
        sample_count=1,
        include_incidents=True,
        include_related=True,
        include_unrelated=False,
    )
    assert "- Vega incidents: 3" in text
    assert "- Vega related alerts: 1" in text
    assert "unrelated" not in text.lower()
    assert "- Total Vega alerts: 1" in text
    assert "105" not in text


def test_test_connection_maps_graphql_400_to_invalid_access_key_id() -> None:
    manager = _manager()

    def _get_alerts(_variables, max_records=None):
        raise VegaBadRequestException(MSG_BAD_REQUEST)

    manager.get_alerts = _get_alerts
    with pytest.raises(VegaUnauthorizedException) as exc:
        manager.test_connection()
    assert str(exc.value) == MSG_INVALID_ACCESS_KEY_ID
    assert format_user_facing_error(exc.value) == MSG_INVALID_ACCESS_KEY_ID
    assert "Check filters and identifiers" not in format_user_facing_error(exc.value)


def test_count_alerts_uses_graphql_total() -> None:
    manager = _manager()
    manager._jwt = "token"

    def _graphql(_query, variables=None):
        assert variables["limit"] == 1
        return {"getAlerts": {"alerts": [{"id": "a-1"}], "total": 42}}

    manager.graphql = _graphql
    assert manager.count_alerts({"hasRelatedIncidents": True}) == 42


def test_get_incident_uses_uuid_or_vega_id_not_both() -> None:
    manager = _manager()
    calls: list[dict] = []

    def _get_incidents(variables, max_records=None):
        calls.append(dict(variables or {}))
        return [{"id": "inc-1"}]

    manager.get_incidents = _get_incidents
    uuid = "019e1b27-5119-7822-bde3-344b13e481cf"
    assert manager.get_incident(uuid)["id"] == "inc-1"
    assert calls == [{"incidentIds": [uuid]}]
    calls.clear()
    assert manager.get_incident("VINC-1")["id"] == "inc-1"
    assert calls == [{"vegaIncidentIds": ["VINC-1"]}]


def test_resolve_incident_filters_maps_user_and_investigation_status() -> None:
    filters = resolve_incident_filters({
        "incident_user_statuses": "OPEN, IN REVIEW",
        "incident_investigation_statuses": "NEW,INVESTIGATING",
    })
    assert filters["user_statuses"] == ["OPEN", "IN_REVIEW"]
    assert filters["investigation_statuses"] == ["NEW", "INVESTIGATING"]


def test_validate_rejects_swapped_incident_status_values() -> None:
    with pytest.raises(VegaValidationException) as exc:
        validate_connector_fields(
            _valid_config(
                incident_user_statuses="NEW",
                incident_investigation_statuses="ON HOLD",
            )
        )
    text = str(exc.value)
    assert "Incident User Statuses to Fetch" in text
    assert "Incident Investigation Statuses to Fetch" in text


def test_resolve_incidents_sends_user_status() -> None:
    manager = _manager()
    captured: list[dict] = []

    def _graphql(query, variables=None):
        captured.append({"query": query, "variables": dict(variables or {})})
        return {"updateIncidents": {"incidents": [{"incidentId": "inc-1"}]}}

    manager.graphql = _graphql
    uuid = "019eea19-551b-7b19-8582-faff640969ff"
    manager.resolve_incidents([uuid])
    assert captured[0]["variables"]["input"] == {
        "incidentIds": [uuid],
        "userStatus": "RESOLVED",
    }
    assert "userStatus" in captured[0]["query"]
    assert "status" not in captured[0]["variables"]["input"]


def test_resolve_incidents_looks_up_human_id() -> None:
    manager = _manager()
    captured: list[dict] = []
    uuid = "019eea19-551b-7b19-8582-faff640969ff"

    def _graphql(query, variables=None):
        captured.append({"query": query, "variables": dict(variables or {})})
        if "getIncidents" in query:
            return {"getIncidents": {"incidents": [{"id": uuid, "vegaUniqueIncidentId": "VINC-1"}]}}
        return {"updateIncidents": {"incidents": [{"incidentId": uuid}]}}

    manager.graphql = _graphql
    manager.resolve_incidents(["VINC-1"])
    update = [item for item in captured if "updateIncidents" in item["query"]][0]
    lookup = [item for item in captured if "getIncidents" in item["query"]][0]
    assert lookup["variables"]["vegaIncidentIds"] == ["VINC-1"]
    assert update["variables"]["input"] == {
        "incidentIds": [uuid],
        "userStatus": "RESOLVED",
    }


def test_get_incidents_stops_paging_when_deadline_passes() -> None:
    manager = _manager()
    manager._jwt = "token"
    calls: list[dict] = []

    def _graphql(_query, variables=None):
        variables = dict(variables or {})
        calls.append(variables)
        limit = int(variables.get("limit") or GRAPHQL_PAGE_SIZE)
        offset = int(variables.get("offset") or 0)
        return {
            "getIncidents": {
                "incidents": [{"id": f"i-{offset + index}"} for index in range(limit)],
                "total": GRAPHQL_PAGE_SIZE * 4,
                "limit": limit,
            }
        }

    manager.graphql = _graphql
    records = manager.get_incidents({}, deadline_monotonic=0)
    assert len(records) == GRAPHQL_PAGE_SIZE
    assert manager.last_fetch_truncated is True
    assert len(calls) == 1


def test_get_alerts_pages_alert_id_lookup() -> None:
    manager = _manager()
    manager._jwt = "token"
    calls: list[dict] = []

    def _graphql(_query, variables=None):
        variables = dict(variables or {})
        calls.append(variables)
        limit = int(variables.get("limit") or GRAPHQL_PAGE_SIZE)
        offset = int(variables.get("offset") or 0)
        return {
            "getAlerts": {
                "alerts": [{"id": f"a-{offset + index}"} for index in range(limit)],
                "total": 120,
                "limit": limit,
                "offset": offset,
            }
        }

    manager.graphql = _graphql
    records = manager.get_alerts({"alertIds": ["019e1b27-5119-7822-bde3-344b13e481cf"]}, 120)
    assert len(records) == 120
    assert [call["offset"] for call in calls] == [0, GRAPHQL_PAGE_SIZE, GRAPHQL_PAGE_SIZE * 2]
    assert [call["limit"] for call in calls] == [GRAPHQL_PAGE_SIZE, GRAPHQL_PAGE_SIZE, 20]
    assert all(call["alertIds"] == ["019e1b27-5119-7822-bde3-344b13e481cf"] for call in calls)
