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
        "lookback_minutes": "5",
        "backfill_days": "30",
        "alert_severities": "LOW,HIGH",
        "alert_statuses": "",
        "alert_verdicts": "",
        "incident_severities": "",
        "incident_user_statuses": "",
        "incident_investigation_statuses": "",
        "incident_verdicts": "",
        "max_events_in_alert": "50",
        "max_alerts_in_case": "30",
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
                lookback_minutes="999",
                alert_severities="URGENT",
                max_events_in_alert="999",
                max_alerts_in_case="0",
                python_timeout="abc",
            )
        )
    text = str(exc.value)
    assert "Cannot run the Vega Alerts and Incidents Connector" in text
    assert "API Root" in text
    assert "Access Key ID" in text
    assert "Fetch Lookback Minutes" in text
    assert "Alert Severities to Fetch" in text
    assert "Max Events in Alert" in text
    assert "Max Alerts in Case" in text
    assert "PythonProcessTimeout" in text
    assert "URGENT" in text


def test_format_test_connection_summary_lists_counts() -> None:
    text = format_test_connection_summary(
        incident_count=12,
        related_alert_count=34,
        unrelated_alert_count=0,
        total_alert_count=34,
        sample_count=3,
    )
    assert "Successfully connected to Vega." in text
    assert "- Vega incidents: 12" in text
    assert "- Vega related alerts: 34" in text
    assert "unrelated" not in text.lower()
    assert "- Total Vega alerts: 34" in text
    assert "Showing 3 sample alert(s) below. Nothing was ingested." in text


def test_test_connection_maps_graphql_400_to_invalid_access_key_id() -> None:
    manager = _manager()

    def _get_alerts(_variables, max_records=None):
        raise VegaBadRequestException(MSG_BAD_REQUEST)

    manager.get_alerts = _get_alerts  # type: ignore[method-assign]
    with pytest.raises(VegaUnauthorizedException) as exc:
        manager.test_connection()
    assert MSG_INVALID_ACCESS_KEY_ID in str(exc.value)


def test_resolve_incident_filters_accepts_empty() -> None:
    filters = resolve_incident_filters(
        {
            "incident_severities": "",
            "incident_user_statuses": "",
            "incident_investigation_statuses": "",
            "incident_verdicts": "",
        }
    )
    assert filters["severities"] is None
