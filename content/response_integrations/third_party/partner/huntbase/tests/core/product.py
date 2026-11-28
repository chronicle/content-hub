from __future__ import annotations

import copy
import dataclasses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from TIPCommon.types import JSON, SingleJson


@dataclasses.dataclass
class Failure:
    status: int
    body: JSON | None = None
    times: int = 1
    headers: dict[str, str] | None = None


class Huntbase:
    """In-memory stand-in for the Huntbase API used by the mocked session."""

    def __init__(self) -> None:
        self.indicators: dict[str, SingleJson] = {}
        self.entities: list[SingleJson] = []
        self.hunts: dict[str, SingleJson] = {}
        self.hunt_findings: dict[str, list[SingleJson]] = {}
        self.findings: list[SingleJson] = []
        self.insights: list[SingleJson] = []
        self.scout_jobs: dict[str, list[SingleJson]] = {}
        self.next_job_id = "job_1"
        self.watchlists: list[SingleJson] = []
        self.watchlist_values: dict[str, list[str]] = {}
        self.proposals: list[SingleJson] = []
        self.started_hunts: list[SingleJson] = []
        self.open_hunt_for_case: str | None = None
        self.scout_questions: list[SingleJson] = []
        self._failures: dict[str, Failure] = {}

    def fail(
        self,
        route: str,
        status: int,
        body: JSON | None = None,
        times: int = 1,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._failures[route] = Failure(status, body, times, headers)

    def take_failure(self, route: str) -> Failure | None:
        failure = self._failures.get(route)
        if failure is None or failure.times == 0:
            return None
        failure.times -= 1
        return failure

    def add_indicator(self, value: str, **best: object) -> None:
        self.indicators[value.lower()] = {
            "id": best.pop("id", f"ind-{value}"),
            "type": best.pop("type", "ip"),
            "value": value,
            "source": {"id": "src-1", "slug": "huntbase-intel", "name": "Huntbase Intel"},
            "confidence": 85,
            "effective_confidence": best.pop("effective_confidence", 80),
            "score": 80,
            "tlp": "amber",
            "state": "active",
            "revoked": False,
            "first_seen": "2026-10-02T08:14:00Z",
            "last_seen": "2026-11-20T17:40:00Z",
            **best,
        }

    def lookup(self, values: list[str]) -> SingleJson:
        results = []
        for value in values:
            best = self.indicators.get(value.lower())
            results.append({
                "input": value,
                "type": best["type"] if best else "ip",
                "value": value,
                "status": "known" if best else "unknown",
                "best": copy.deepcopy(best),
                "matches": [copy.deepcopy(best)] if best else [],
                "sighted": bool(best),
                "sightings_count": 2 if best else 0,
            })
        return {"summary": {"submitted": len(values)}, "results": results}

    def add_hunt(self, hunt_id: str, status: str = "active", **fields: object) -> SingleJson:
        hunt = {
            "id": hunt_id,
            "title": fields.pop("title", f"Hunt {hunt_id}"),
            "status": status,
            "severity": "high",
            "disposition": None,
            "scout_summary": None,
            "latest_verdict": None,
            "created_at": "2026-11-21T14:10:00Z",
            "updated_at": "2026-11-21T14:42:00Z",
            **fields,
        }
        self.hunts[hunt_id] = hunt
        return hunt

    def add_scout_job(self, job_id: str, *states: SingleJson) -> None:
        self.scout_jobs[job_id] = list(states)

    def next_scout_state(self, job_id: str) -> SingleJson | None:
        states = self.scout_jobs.get(job_id)
        if not states:
            return None
        return states.pop(0) if len(states) > 1 else states[0]
