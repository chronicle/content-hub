from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession

from .product import Huntbase

if TYPE_CHECKING:
    from collections.abc import Iterable

    from integration_testing.requests.session import RouteFunction
    from TIPCommon.types import SingleJson

PREFIX = r"/api/v1"


def _params(request: MockRequest) -> dict[str, list[str]]:
    raw = request.kwargs.get("params") or {}
    items = raw.items() if isinstance(raw, dict) else raw
    params: dict[str, list[str]] = {}
    for key, value in items:
        params.setdefault(key, []).append(str(value))
    return params


def _json(request: MockRequest) -> SingleJson:
    return request.kwargs.get("json") or {}


def _page(items: list[dict], params: dict[str, list[str]]) -> list[dict]:
    offset = int(params.get("offset", ["0"])[0])
    limit = int(params.get("limit", ["50"])[0])
    return items[offset : offset + limit]


class HuntbaseSession(MockSession[MockRequest, MockResponse, Huntbase]):
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            self.ping,
            self.intel_lookup,
            self.entity_by_value,
            self.start_hunt,
            self.get_hunt,
            self.hunt_findings,
            self.list_findings,
            self.list_insights,
            self.scout_submit,
            self.scout_status,
            self.list_watchlists,
            self.add_watchlist_values,
            self.list_proposals,
        ]

    def _failure(self, route: str) -> MockResponse | None:
        failure = self._product.take_failure(route)
        if failure is None:
            return None
        body = failure.body if failure.body is not None else {"status": failure.status, "detail": "mock failure"}
        return MockResponse(content=body, status_code=failure.status, headers=failure.headers)

    @router.get(PREFIX + r"/access/vocabulary")
    def ping(self, _: MockRequest) -> MockResponse:
        if (failure := self._failure("ping")) is not None:
            return failure
        return MockResponse(content={"capabilities": []}, status_code=200)

    @router.post(PREFIX + r"/intel/lookup")
    def intel_lookup(self, request: MockRequest) -> MockResponse:
        if (failure := self._failure("intel_lookup")) is not None:
            return failure
        return MockResponse(content=self._product.lookup(_json(request).get("values", [])), status_code=200)

    @router.get(PREFIX + r"/entities/by-value")
    def entity_by_value(self, request: MockRequest) -> MockResponse:
        if (failure := self._failure("entity_by_value")) is not None:
            return failure
        params = _params(request)
        value = params.get("value", [""])[0].lower()
        kind = params.get("entity_type", [None])[0]
        items = [
            e
            for e in self._product.entities
            if e["attributes"]["name"].lower() == value and (kind is None or e["type"] == kind)
        ]
        return MockResponse(content={"entities": items, "total": len(items)}, status_code=200)

    @router.post(PREFIX + r"/hunts/auto")
    def start_hunt(self, request: MockRequest) -> MockResponse:
        if (failure := self._failure("start_hunt")) is not None:
            return failure
        body = _json(request)
        self._product.started_hunts.append(copy.deepcopy(body))
        reopened = bool(body.get("reuse_open")) and self._product.open_hunt_for_case is not None
        hunt_id = self._product.open_hunt_for_case if reopened else "hunt-new-1"
        return MockResponse(
            content={
                "status": "reopened" if reopened else "accepted",
                "hunt_session_id": hunt_id,
                "url": f"https://huntbase.example.com/hunts/{hunt_id}?org=o1&src=api",
                "title": body.get("title"),
                "seed_entity_count": len(body.get("seed_values", [])),
                "seed_values": {"resolved": [], "unresolved": body.get("seed_values", [])},
                "session_mode": body.get("session_mode"),
                "planning": "queued",
            },
            status_code=202,
        )

    @router.get(PREFIX + r"/sessions/[^/]+")
    def get_hunt(self, request: MockRequest) -> MockResponse:
        if (failure := self._failure("hunt")) is not None:
            return failure
        hunt_id = request.url.path.rsplit("/", 1)[-1]
        hunt = self._product.hunts.get(hunt_id)
        if hunt is None:
            return MockResponse(content={"status": 404, "detail": "Session not found"}, status_code=404)
        return MockResponse(content=hunt, status_code=200)

    @router.get(PREFIX + r"/sessions/[^/]+/findings")
    def hunt_findings(self, request: MockRequest) -> MockResponse:
        if (failure := self._failure("hunt_findings")) is not None:
            return failure
        hunt_id = request.url.path.split("/")[-2]
        return MockResponse(content=self._product.hunt_findings.get(hunt_id, []), status_code=200)

    @router.get(PREFIX + r"/findings")
    def list_findings(self, request: MockRequest) -> MockResponse:
        if (failure := self._failure("findings")) is not None:
            return failure
        params = _params(request)
        wanted = set(params.get("disposition", []))
        since = params.get("since", [""])[0]
        items = [
            f
            for f in self._product.findings
            if (not wanted or f.get("disposition") in wanted) and f.get("created_at", "") > since
        ]
        items.sort(key=lambda f: (f.get("created_at", ""), f.get("id", "")))
        page = _page(items, params)
        return MockResponse(content={"items": page, "total": len(items)}, status_code=200)

    @router.get(PREFIX + r"/insights")
    def list_insights(self, request: MockRequest) -> MockResponse:
        if (failure := self._failure("insights")) is not None:
            return failure
        params = _params(request)
        severity = params.get("severity", [None])[0]
        since = params.get("from", [""])[0]
        items = [
            i
            for i in self._product.insights
            if (severity is None or i.get("severity", "").lower() == severity.lower()) and i.get("time", "") >= since
        ]
        items.sort(key=lambda i: i.get("time", ""))
        return MockResponse(content=_page(items, params), status_code=200)

    @router.post(PREFIX + r"/agents/scout/jobs")
    def scout_submit(self, request: MockRequest) -> MockResponse:
        if (failure := self._failure("scout_jobs")) is not None:
            return failure
        self._product.scout_questions.append(copy.deepcopy(_json(request)))
        job_id = self._product.next_job_id
        state = self._product.next_scout_state(job_id) or {"state": "queued"}
        return MockResponse(content={"job_id": job_id, "poll_after_seconds": 5, **state}, status_code=202)

    @router.get(PREFIX + r"/agents/scout/jobs/[^/]+")
    def scout_status(self, request: MockRequest) -> MockResponse:
        if (failure := self._failure("scout_job")) is not None:
            return failure
        job_id = request.url.path.rsplit("/", 1)[-1]
        state = self._product.next_scout_state(job_id)
        if state is None:
            return MockResponse(content={"status": 404, "detail": "Job not found"}, status_code=404)
        return MockResponse(content={"job_id": job_id, **state}, status_code=200)

    @router.get(PREFIX + r"/intel/watchlists")
    def list_watchlists(self, _: MockRequest) -> MockResponse:
        if (failure := self._failure("watchlists")) is not None:
            return failure
        return MockResponse(content={"items": self._product.watchlists}, status_code=200)

    @router.post(PREFIX + r"/intel/watchlists/[^/]+/values")
    def add_watchlist_values(self, request: MockRequest) -> MockResponse:
        if (failure := self._failure("watchlist_values")) is not None:
            return failure
        watchlist_id = request.url.path.split("/")[-2]
        stored = self._product.watchlist_values.setdefault(watchlist_id, [])
        added, existing, rejected = 0, 0, []
        for value in _json(request).get("values", []):
            if value.startswith("bad:"):
                rejected.append({"input": value, "reason": "unsupported value"})
            elif value in stored:
                existing += 1
            else:
                stored.append(value)
                added += 1
        return MockResponse(content={"added": added, "existing": existing, "rejected": rejected}, status_code=200)

    @router.get(PREFIX + r"/agents/scout/proposals")
    def list_proposals(self, request: MockRequest) -> MockResponse:
        if (failure := self._failure("proposals")) is not None:
            return failure
        limit = int(_params(request).get("limit", ["50"])[0])
        return MockResponse(content={"items": self._product.proposals[:limit]}, status_code=200)


CASE_ID = 4821


class SoarSdkSession(MockSession[MockRequest, MockResponse, None]):
    """The SOAR platform API the SDK calls (case metadata for actions that run in a case)."""

    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [self.case_metadata]

    @router.get(r".*/CaseMetadata.*")
    def case_metadata(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content={
                "identifier": str(CASE_ID),
                "creation_time": 1763700000000,
                "modification_time": 1763700000000,
                "alert_count": 1,
                "priority": 80,
                "is_touched": False,
                "is_merged": False,
                "is_important": False,
                "environment": "Default Environment",
                "assigned_user": "@Tier1",
                "title": "Beaconing from WS-0142",
                "description": "",
                "status": 1,
                "is_incident": False,
                "stage": "Triage",
                "has_suspicious_entity": True,
                "high_risk_products": [],
                "is_locked": False,
                "has_workflow": False,
                "sla_expiration_unix_time": 0,
                "additional_properties": {},
            },
            status_code=200,
        )
