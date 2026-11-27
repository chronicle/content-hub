"""Unit tests for case dedup helpers and incident batch indexing."""

from __future__ import annotations

from core.case_dedup import can_merge_cases, remaining_ingest_slots
from core.VegaManager import VegaClientConfig, VegaManager


class _BatchManager(VegaManager):
    def __init__(self) -> None:
        super().__init__(
            VegaClientConfig(api_root="https://example.test", access_key_id="id", access_key="key"),
            logger_instance=None,
        )
        self.calls: list[dict] = []
        self.rows: list[dict] = []

    def get_incidents(self, variables, max_records=None, deadline_monotonic=None):
        self.calls.append(dict(variables or {}))
        ids = set(variables.get("incidentIds") or []) | set(variables.get("vegaIncidentIds") or [])
        rows = [
            row
            for row in self.rows
            if str(row.get("id") or "") in ids or str(row.get("vegaUniqueIncidentId") or "") in ids
        ]
        if max_records is not None:
            return rows[: int(max_records)]
        return rows


def test_can_merge_and_slots() -> None:
    assert can_merge_cases(15, 15, 30) is True
    assert can_merge_cases(20, 15, 30) is False
    assert remaining_ingest_slots("inc-1", {"inc-1:a", "inc-1:b"}, 2) == 0


def test_get_incidents_by_ids_batches() -> None:
    manager = _BatchManager()
    manager.rows = [
        {"id": "11111111-1111-1111-1111-111111111111", "name": "A"},
        {"id": "22222222-2222-2222-2222-222222222222", "vegaUniqueIncidentId": "VINC-2", "name": "B"},
    ]
    found = manager.get_incidents_by_ids(
        [
            "11111111-1111-1111-1111-111111111111",
            "VINC-2",
            "11111111-1111-1111-1111-111111111111",
        ],
        batch_size=10,
    )
    assert "11111111-1111-1111-1111-111111111111" in found
    assert "VINC-2" in found
    assert any("incidentIds" in call for call in manager.calls)
    assert any("vegaIncidentIds" in call for call in manager.calls)
    assert len(manager.calls) == 2
