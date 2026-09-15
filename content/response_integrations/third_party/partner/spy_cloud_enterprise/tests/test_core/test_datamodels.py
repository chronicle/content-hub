"""Tests for the SpyCloud presentation data models."""

from __future__ import annotations

import json

from spy_cloud_enterprise.core import datamodels
from spy_cloud_enterprise.core.datamodels import SpyCloudExposure

CATALOG = {
    123: {"source_id": 123, "title": "ExampleForum Breach", "site": "exampleforum.com"},
}


def _credential_record() -> dict:
    """A high-severity record carrying secrets that must never be surfaced."""
    return {
        "document_id": "doc-1",
        "source_id": 123,
        "severity": 20,
        "email": "Victim@Example.com",
        "username": "victim",
        "ip_addresses": ["1.2.3.4"],
        "domain": "example.com",
        "password": "hashed-xyz",
        "password_plaintext": "hunter2",
        "password_type": "plaintext",
        "cookies": "sessioncookie=abc",
        "spycloud_publish_date": "2026-04-02T00:00:00Z",
    }


def _informational_record() -> dict:
    return {
        "document_id": "doc-2",
        "source_id": 999,
        "severity": 2,
        "email": "victim@example.com",
    }


class TestSpyCloudExposure:
    def test_severity_and_label(self) -> None:
        exposure = SpyCloudExposure(_credential_record(), CATALOG)
        assert exposure.severity == 20
        assert exposure.severity_label == "high"
        assert isinstance(exposure.risk_score, int)
        assert 0 < exposure.risk_score <= 100

    def test_secret_presence_flags(self) -> None:
        exposure = SpyCloudExposure(_credential_record(), CATALOG)
        assert exposure.has_plaintext_password is True
        assert exposure.has_password is True
        assert exposure.has_cookies is True

    def test_breach_metadata_from_catalog(self) -> None:
        exposure = SpyCloudExposure(_credential_record(), CATALOG)
        assert exposure.breach_title == "ExampleForum Breach"
        assert exposure.breach_site == "exampleforum.com"

    def test_matches_is_case_insensitive_across_identity_types(self) -> None:
        exposure = SpyCloudExposure(_credential_record(), CATALOG)
        assert exposure.matches("victim@example.com") is True
        assert exposure.matches("VICTIM@EXAMPLE.COM") is True
        assert exposure.matches("victim") is True
        assert exposure.matches("1.2.3.4") is True
        assert exposure.matches("EXAMPLE.COM") is True
        assert exposure.matches("someone-else@example.org") is False

    def test_to_json_never_contains_secrets(self) -> None:
        exposure = SpyCloudExposure(_credential_record(), CATALOG)
        result = exposure.to_json()

        assert "password" not in result
        assert "password_plaintext" not in result
        assert "password_type" not in result
        assert "cookies" not in result

        serialized = json.dumps(result)
        assert "hunter2" not in serialized
        assert "hashed-xyz" not in serialized
        assert "sessioncookie" not in serialized

        # Safe presence indicators are still reported.
        assert result["has_plaintext_password"] is True
        assert result["breach_title"] == "ExampleForum Breach"

    def test_to_table_summarizes_without_secrets(self) -> None:
        exposure = SpyCloudExposure(_credential_record(), CATALOG)
        row = exposure.to_table()

        assert row["Plaintext Password Exposed"] == "Yes"
        assert row["Password Present"] == "Yes"
        assert row["Cookies Present"] == "Yes"
        assert row["Breach Site"] == "exampleforum.com"

        serialized = json.dumps(row)
        assert "hunter2" not in serialized
        assert "hashed-xyz" not in serialized

    def test_informational_record_is_not_high_risk(self) -> None:
        exposure = SpyCloudExposure(_informational_record(), CATALOG)
        assert exposure.severity_label == "low"
        assert exposure.has_plaintext_password is False
        assert exposure.is_high_risk is False


class TestAggregations:
    def test_summarize(self) -> None:
        exposures = [
            SpyCloudExposure(_credential_record(), CATALOG),
            SpyCloudExposure(_informational_record(), CATALOG),
        ]
        summary = datamodels.summarize(exposures)

        assert summary["Exposure Count"] == 2
        assert summary["Breach Count"] == 2
        assert summary["Max Severity"] == 20
        assert summary["Max Severity Label"] == "high"
        assert summary["Plaintext Password Exposed"] == "Yes"
        assert summary["High Risk"] == "Yes"

    def test_is_high_risk(self) -> None:
        assert datamodels.is_high_risk([SpyCloudExposure(_credential_record(), CATALOG)]) is True
        assert datamodels.is_high_risk([SpyCloudExposure(_informational_record(), CATALOG)]) is False

    def test_build_insight_contains_identifier_and_no_secret(self) -> None:
        exposures = [SpyCloudExposure(_credential_record(), CATALOG)]
        html = datamodels.build_insight("victim@example.com", exposures)
        assert "victim@example.com" in html
        assert "SpyCloud Exposures" in html
        assert "hunter2" not in html


def _event_props() -> dict:
    """Flattened SpyCloud fields as the connector stores them on an event.

    SecOps returns ``additional_properties`` as strings, so booleans arrive as
    ``"true"`` / ``"false"``.
    """
    return {
        "device_vendor": "SpyCloud",
        "spycloud_document_id": "doc-1",
        "spycloud_source_id": "123",
        "spycloud_source_severity": "20",
        "spycloud_severity_label": "high",
        "spycloud_risk_score": "80",
        "spycloud_breach_title": "ExampleForum Breach",
        "spycloud_breach_site": "exampleforum.com",
        "spycloud_email": "victim@example.com",
        "spycloud_record_addition_date": "2026-04-02T00:00:00Z",
        "spycloud_has_password": "true",
        "spycloud_has_plaintext_password": "true",
        "spycloud_password_type": "plaintext",
    }


class TestInCaseEventPresentation:
    def test_is_spycloud_event_detects_prefixed_and_vendor(self) -> None:
        assert datamodels.is_spycloud_event(_event_props()) is True
        assert datamodels.is_spycloud_event({"device_vendor": "SpyCloud"}) is True
        assert datamodels.is_spycloud_event({"device_vendor": "EDR", "foo": "bar"}) is False
        assert datamodels.is_spycloud_event(None) is False

    def test_event_row_parses_string_booleans(self) -> None:
        row = datamodels.event_row("SpyCloud Credential Exposure", _event_props())
        assert row["Alert"] == "SpyCloud Credential Exposure"
        assert row["SpyCloud Severity"] == "20"
        assert row["Severity Label"] == "high"
        assert row["Breach Title"] == "ExampleForum Breach"
        assert row["Publish Date"] == "2026-04-02T00:00:00Z"
        assert row["Plaintext Password Exposed"] == "Yes"
        assert row["Password Present"] == "Yes"

    def test_event_row_has_password_implied_by_plaintext(self) -> None:
        props = _event_props()
        del props["spycloud_has_password"]
        row = datamodels.event_row("Alert", props)
        assert row["Password Present"] == "Yes"

    def test_event_json_drops_unprefixed_keys_but_keeps_persisted_secret(self) -> None:
        props = _event_props()
        props["spycloud_password_plaintext"] = "hunter2"
        result = datamodels.event_json(props)

        # Non-spycloud keys are still excluded.
        assert "device_vendor" not in result
        assert result["spycloud_breach_title"] == "ExampleForum Breach"
        # A persisted secret is surfaced verbatim (retention gated by the connector).
        assert result["spycloud_password_plaintext"] == "hunter2"


class TestCaseInsight:
    def test_insight_severity_error_for_plaintext_or_malware(self) -> None:
        plaintext = datamodels.event_row("Alert", _event_props())
        assert datamodels.insight_severity([plaintext]) == 2  # ERROR

        malware = {"Malware Family": "RedLine", "Plaintext Password Exposed": "No"}
        assert datamodels.insight_severity([malware]) == 2

    def test_insight_severity_warn_for_low_risk(self) -> None:
        low = {"Plaintext Password Exposed": "No", "Malware Family": ""}
        assert datamodels.insight_severity([low]) == 1  # WARN

    def test_build_case_insight_html_escapes_and_summarizes(self) -> None:
        row = datamodels.event_row("Alert", _event_props())
        row["Breach Title"] = "<script>Evil</script>"
        markup = datamodels.build_case_insight_html([row])

        assert "<table" in markup
        assert "1 exposure(s) on this case" in markup
        # Values are escaped so injected markup cannot render.
        assert "<script>Evil</script>" not in markup
        assert "&lt;script&gt;" in markup

    def test_build_case_insight_html_uses_labelled_badge_not_title_color(self) -> None:
        """Risk is shown by a text badge, and the title inherits theme color."""
        high = datamodels.event_row("Alert", _event_props())  # plaintext -> high risk
        low = {"Plaintext Password Exposed": "No", "Malware Family": ""}

        high_markup = datamodels.build_case_insight_html([high])
        low_markup = datamodels.build_case_insight_html([low])

        # Severity is conveyed by a word, legible without color perception.
        assert "HIGH RISK" in high_markup
        assert "REVIEW" in low_markup
        # The <h2> tag itself sets no color, so the title inherits the theme's
        # text color and stays readable on dark backgrounds. (The badge span
        # sets its own color, which is fine — it controls its own background.)
        h2_tag = high_markup.split(">", 1)[0]
        assert h2_tag.startswith("<h2")
        assert "color:" not in h2_tag

    def test_build_case_insight_html_caps_rows(self) -> None:
        rows = [datamodels.event_row("Alert", _event_props()) for _ in range(30)]
        markup = datamodels.build_case_insight_html(rows)

        assert f"Showing {datamodels.INSIGHT_MAX_ROWS} of 30 exposures" in markup
        # The compact summary table caps its body rows; count only its rows (the
        # collapsible "Show all fields" block below renders every row uncapped).
        summary = markup.split("<details", 1)[0]
        assert summary.count("<tr>") == datamodels.INSIGHT_MAX_ROWS + 1


class TestPasswordPolicy:
    """Policy helpers used by the Entra ID password-response playbook."""

    def test_has_symbol(self) -> None:
        assert datamodels.has_symbol("hunter2!")
        assert not datamodels.has_symbol("hunter2")
        assert not datamodels.has_symbol("")

    def test_matches_policy_length_and_symbol(self) -> None:
        # Long enough and has a symbol -> matches.
        assert datamodels.password_matches_policy("Sup3r$ecret", 8, True)

    def test_matches_policy_rejects_short(self) -> None:
        assert not datamodels.password_matches_policy("a$1", 8, True)

    def test_matches_policy_rejects_missing_symbol_when_required(self) -> None:
        assert not datamodels.password_matches_policy("longenough12", 8, True)

    def test_matches_policy_allows_missing_symbol_when_not_required(self) -> None:
        assert datamodels.password_matches_policy("longenough12", 8, False)

    def test_matches_policy_rejects_empty(self) -> None:
        assert not datamodels.password_matches_policy("", 0, False)

    def test_collect_plaintext_passwords_reads_password_fields(self) -> None:
        props = {
            "spycloud_password_plaintext": "hunter2!",
            "spycloud_password": "hunter2!",  # duplicate is de-duplicated
            "spycloud_old_password": "oldpass1$",
            "spycloud_cookies": "session=abc",  # not a password field
        }
        passwords = datamodels.collect_plaintext_passwords(props)
        assert passwords == ["hunter2!", "oldpass1$"]

    def test_collect_plaintext_passwords_empty_when_none_persisted(self) -> None:
        assert datamodels.collect_plaintext_passwords({"spycloud_email": "a@b.com"}) == []
        assert datamodels.collect_plaintext_passwords(None) == []

    def test_mask_password_hides_value_keeps_length(self) -> None:
        masked = datamodels.mask_password("hunter2!")
        assert "hunter2" not in masked
        assert "length 8" in masked


class TestTimestamps:
    """The rotation check compares timestamps from producers that disagree on format."""

    def test_parses_iso_with_z_and_milliseconds(self) -> None:
        """Okta's passwordChanged shape."""
        parsed = datamodels.parse_timestamp("2026-07-01T09:15:00.000Z")
        assert parsed is not None
        assert parsed.isoformat() == "2026-07-01T09:15:00+00:00"

    def test_parses_iso_with_offset(self) -> None:
        parsed = datamodels.parse_timestamp("2026-07-01T11:15:00+02:00")
        assert parsed is not None
        assert parsed.isoformat() == "2026-07-01T09:15:00+00:00"

    def test_parses_bare_date_as_utc_midnight(self) -> None:
        """SpyCloud publish dates are frequently date-only."""
        parsed = datamodels.parse_timestamp("2026-06-14")
        assert parsed is not None
        assert parsed.isoformat() == "2026-06-14T00:00:00+00:00"

    def test_parses_naive_timestamp_as_utc(self) -> None:
        parsed = datamodels.parse_timestamp("2026-06-14 08:30:00")
        assert parsed is not None
        assert parsed.isoformat() == "2026-06-14T08:30:00+00:00"

    def test_trims_over_long_fractional_seconds(self) -> None:
        """Nanosecond precision would otherwise raise inside fromisoformat."""
        assert datamodels.parse_timestamp("2026-07-01T09:15:00.123456789Z") is not None

    def test_parses_epoch_seconds_and_milliseconds(self) -> None:
        seconds = datamodels.parse_timestamp("1782810900")
        millis = datamodels.parse_timestamp("1782810900000")
        assert seconds is not None and millis is not None
        assert seconds == millis

    def test_returns_none_for_unusable_values(self) -> None:
        assert datamodels.parse_timestamp("") is None
        assert datamodels.parse_timestamp(None) is None
        assert datamodels.parse_timestamp("never") is None

    def test_event_publish_date_prefers_publish_over_record_dates(self) -> None:
        props = {
            "spycloud_publish_date": "2026-06-14",
            "spycloud_record_addition_date": "2026-01-01",
            "spycloud_infected_time": "2025-01-01",
        }
        assert datamodels.event_publish_date(props) == "2026-06-14"

    def test_event_publish_date_falls_back_through_record_dates(self) -> None:
        assert (
            datamodels.event_publish_date({"spycloud_record_addition_date": "2026-01-01"})
            == "2026-01-01"
        )
        assert (
            datamodels.event_publish_date({"spycloud_infected_time": "2025-01-01"})
            == "2025-01-01"
        )

    def test_event_publish_date_empty_when_absent(self) -> None:
        assert datamodels.event_publish_date({"spycloud_email": "a@b.com"}) == ""
        assert datamodels.event_publish_date(None) == ""
