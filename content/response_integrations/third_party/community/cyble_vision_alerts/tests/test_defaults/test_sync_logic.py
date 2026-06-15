from __future__ import annotations

from ...core.CybleAlertMapper import CybleAlertMapper
from ...core.constants import FIELD_ALERT_ID
from ...jobs import SyncAlertsJob


class _Logger:
    def info(self, *args: object, **kwargs: object) -> None:
        return None

    def error(self, *args: object, **kwargs: object) -> None:
        return None


class _StubSiemplify:
    """Minimal SiemplifyJob stand-in for dedup-lookup unit tests."""

    def __init__(self, case_ids: list[str], cases_by_id: dict[str, dict]) -> None:
        self._case_ids = case_ids
        self._cases_by_id = cases_by_id
        self.LOGGER = _Logger()

    def get_cases_by_filter(self, custom_fields: dict | None = None, limit: int | None = None) -> list[str]:
        return self._case_ids

    def _get_case_by_id(self, case_id: str) -> dict:
        return self._cases_by_id[case_id]


def test_build_idempotency_key_prefers_id() -> None:
    assert CybleAlertMapper.build_idempotency_key({"id": "abc", "data_id": "xyz"}) == "abc"


def test_build_idempotency_key_falls_back_to_data_id() -> None:
    assert CybleAlertMapper.build_idempotency_key({"data_id": "xyz"}) == "xyz"


def test_build_idempotency_key_empty_when_missing() -> None:
    assert CybleAlertMapper.build_idempotency_key({}) == ""


def test_is_newer_true_when_update_after_sync() -> None:
    assert SyncAlertsJob._is_newer(
        "2026-01-02T00:00:00+00:00", "2026-01-01T00:00:00+00:00"
    ) is True


def test_is_newer_false_when_not_after() -> None:
    assert SyncAlertsJob._is_newer(
        "2026-01-01T00:00:00+00:00", "2026-01-02T00:00:00+00:00"
    ) is False


def test_is_newer_false_when_missing_values() -> None:
    assert SyncAlertsJob._is_newer("", "2026-01-01T00:00:00+00:00") is False


def test_find_existing_alert_resolves_case_id_to_alert_dict() -> None:
    """Regression: ``get_cases_by_filter`` returns case IDs (not Case/Alert
    objects), so the matching alert must be located inside the resolved case's
    ``cyber_alerts`` and returned together with its case ID."""
    SyncAlertsJob._DEDUP_LOOKUP_AVAILABLE = None
    target = "cyble-123"
    case = {
        "cyber_alerts": [
            {"identifier": "ALERT-1", "additional_properties": {FIELD_ALERT_ID: "other"}},
            {"identifier": "ALERT-2", "additional_properties": {FIELD_ALERT_ID: target}},
        ]
    }
    siemplify = _StubSiemplify(case_ids=["CASE-1"], cases_by_id={"CASE-1": case})

    result = SyncAlertsJob._find_existing_alert(siemplify, target)

    assert result is not None
    case_id, alert = result
    assert case_id == "CASE-1"
    assert alert["identifier"] == "ALERT-2"


def test_find_existing_alert_returns_none_when_no_match() -> None:
    SyncAlertsJob._DEDUP_LOOKUP_AVAILABLE = None
    siemplify = _StubSiemplify(case_ids=[], cases_by_id={})

    assert SyncAlertsJob._find_existing_alert(siemplify, "missing") is None
