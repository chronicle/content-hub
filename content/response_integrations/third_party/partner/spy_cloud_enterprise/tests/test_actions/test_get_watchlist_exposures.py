"""Tests for the SpyCloud Enterprise Get Watchlist Exposures action.

The action presents the SpyCloud exposures that already live on the current
case. It reads every alert in the case, pulls the ``spycloud_*`` fields the
connector flattened onto each security event, and renders one case-wall table.
It makes no SpyCloud API call, so these tests inject a fake case object rather
than mocking the vendor SDK.
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any
from unittest.mock import MagicMock, patch

from spy_cloud_enterprise.actions import GetWatchlistExposures


@dataclasses.dataclass
class _Event:
    additional_properties: dict = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class _Alert:
    name: str = ""
    security_events: list = dataclasses.field(default_factory=list)


def _credential_event() -> _Event:
    """A high-severity credential exposure that carries no secret value."""
    return _Event(
        additional_properties={
            "device_vendor": "SpyCloud",
            "spycloud_document_id": "doc-1",
            "spycloud_source_id": "123",
            "spycloud_source_severity": "20",
            "spycloud_severity_label": "high",
            "spycloud_risk_score": "80",
            "spycloud_breach_title": "ExampleForum Breach",
            "spycloud_breach_site": "exampleforum.com",
            "spycloud_email": "victim@example.com",
            "spycloud_domain": "example.com",
            "spycloud_record_addition_date": "2026-04-02T00:00:00Z",
            "spycloud_has_password": "true",
            "spycloud_has_plaintext_password": "true",
            "spycloud_password_type": "plaintext",
            "spycloud_collection_source": "breach",
        }
    )


def _malware_event() -> _Event:
    return _Event(
        additional_properties={
            "device_vendor": "SpyCloud",
            "spycloud_document_id": "doc-2",
            "spycloud_source_severity": "25",
            "spycloud_severity_label": "critical",
            "spycloud_malware_family": "RedLine",
            "spycloud_infected_machine_id": "abc123",
            "spycloud_email": "victim@example.com",
        }
    )


def _make_siemplify(alerts: list[_Alert]) -> tuple[MagicMock, list[dict[str, Any]]]:
    """Build a SiemplifyAction double whose case exposes the given alerts."""
    siemplify = MagicMock(name="SiemplifyAction")
    siemplify.case.alerts = alerts
    siemplify.result = MagicMock(name="result")

    end_calls: list[dict[str, Any]] = []

    def _end(message: str = "", result_value: Any = None, status: Any = None) -> None:
        end_calls.append(
            {"message": message, "result_value": result_value, "status": status}
        )

    siemplify.end.side_effect = _end
    return siemplify, end_calls


def _run(siemplify: MagicMock) -> None:
    with patch.object(GetWatchlistExposures, "SiemplifyAction", return_value=siemplify):
        GetWatchlistExposures.main()


class TestGetWatchlistExposures:
    def test_presents_exposures_from_all_alerts_in_case(self) -> None:
        """Exposure events from every alert in the case land in one table."""
        alerts = [
            _Alert("SpyCloud Plaintext Credential Exposure", [_credential_event()]),
            _Alert("SpyCloud Malware Infection", [_malware_event()]),
        ]
        siemplify, end_calls = _make_siemplify(alerts)

        _run(siemplify)

        siemplify.result.add_data_table.assert_called_once()
        table_name = siemplify.result.add_data_table.call_args.args[0]
        assert table_name == GetWatchlistExposures.EXPOSURES_TABLE_NAME

        assert end_calls[0]["result_value"] == 2
        assert "2 SpyCloud" in end_calls[0]["message"]

    def test_creates_case_wall_insight(self) -> None:
        """The exposures are surfaced as an HTML insight on the case wall."""
        alerts = [_Alert("SpyCloud Plaintext Credential Exposure", [_credential_event()])]
        siemplify, _ = _make_siemplify(alerts)

        _run(siemplify)

        siemplify.create_case_insight.assert_called_once()
        kwargs = siemplify.create_case_insight.call_args.kwargs
        assert kwargs["title"] == GetWatchlistExposures.EXPOSURES_TABLE_NAME
        assert "<table" in kwargs["content"]
        # A plaintext-password exposure is high risk -> ERROR severity (2).
        assert kwargs["severity"] == 2

    def test_no_insight_when_no_exposures(self) -> None:
        """No insight panel is created for a case with no SpyCloud exposures."""
        other = _Event(additional_properties={"device_vendor": "SomeEDR", "foo": "bar"})
        siemplify, _ = _make_siemplify([_Alert("EDR Alert", [other])])

        _run(siemplify)

        siemplify.create_case_insight.assert_not_called()

    def test_surfaces_persisted_plaintext_secret(self) -> None:
        """When the connector persisted a secret, it is surfaced in the JSON result.

        Secret retention is gated at collection time by the connector's "Include
        Plaintext Secrets" option; once a raw value is on the event, this action
        reports it verbatim rather than stripping it.
        """
        event = _credential_event()
        event.additional_properties["spycloud_password_plaintext"] = "hunter2"
        siemplify, _ = _make_siemplify([_Alert("Alert", [event])])

        _run(siemplify)

        json_payload = siemplify.result.add_result_json.call_args.args[0]
        serialized = json.dumps(json_payload)
        assert "hunter2" in serialized

    def test_omits_secret_when_not_persisted(self) -> None:
        """With secret retention off, no secret column carries a value."""
        siemplify, _ = _make_siemplify(
            [_Alert("Alert", [_credential_event()])]
        )

        _run(siemplify)

        json_payload = siemplify.result.add_result_json.call_args.args[0]
        exposure = json_payload["exposures"][0]
        # The secret keys are present but empty when nothing was persisted.
        assert not exposure.get("spycloud_password_plaintext")
        assert not exposure.get("spycloud_password")

    def test_ignores_non_spycloud_events(self) -> None:
        """Alerts from other products in the case are skipped."""
        other = _Event(additional_properties={"device_vendor": "SomeEDR", "foo": "bar"})
        siemplify, end_calls = _make_siemplify([_Alert("EDR Alert", [other])])

        _run(siemplify)

        siemplify.result.add_data_table.assert_not_called()
        assert end_calls[0]["result_value"] == 0
        assert "No SpyCloud Watchlist exposures" in end_calls[0]["message"]

    def test_empty_case_completes_with_message(self) -> None:
        """A case with no alerts completes cleanly with a 'none found' message."""
        siemplify, end_calls = _make_siemplify([])

        _run(siemplify)

        assert end_calls[0]["result_value"] == 0
        assert "No SpyCloud Watchlist exposures" in end_calls[0]["message"]
