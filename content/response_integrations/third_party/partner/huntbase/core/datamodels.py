from __future__ import annotations

import dataclasses
import datetime
from typing import TYPE_CHECKING

from . import constants

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


def parse_timestamp(value: object) -> datetime.datetime | None:
    """Parse an ISO 8601 string (or epoch seconds/ms) into an aware UTC datetime."""
    if value in (None, "") or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 10**11 else value
        return datetime.datetime.fromtimestamp(seconds, tz=datetime.UTC)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.UTC)
    return parsed.astimezone(datetime.UTC)


def to_unix_ms(value: object) -> int | None:
    parsed = parse_timestamp(value)
    return int(parsed.timestamp() * 1000) if parsed else None


def to_iso(value: datetime.datetime) -> str:
    return value.astimezone(datetime.UTC).isoformat().replace("+00:00", "Z")


def severity_to_priority(severity: object) -> int:
    return constants.SEVERITY_TO_PRIORITY.get(str(severity or "").lower(), constants.PRIORITY_MEDIUM)


def severity_rank(severity: object) -> int:
    value = str(severity or "").lower()
    if value == "info":
        value = "informational"
    try:
        return constants.SEVERITY_ORDER.index(value)
    except ValueError:
        return -1


def _count(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        for key in ("count", "total"):
            count = value.get(key)
            if isinstance(count, int) and not isinstance(count, bool):
                return count
    return None


def _source_name(source: object) -> str | None:
    """The indicator source as text: the API returns an object (id, slug, name)."""
    if isinstance(source, dict):
        name = source.get("name") or source.get("slug") or source.get("id")
        return str(name) if name else None
    return str(source) if source not in (None, "") else None


def _clean(values: SingleJson) -> SingleJson:
    return {key: value for key, value in values.items() if value not in (None, "", [], {})}


@dataclasses.dataclass(slots=True, frozen=True)
class HuntbaseConfig:
    """Connection settings shared by the actions and the connector."""

    api_root: str
    api_key: str
    verify_ssl: bool = True


@dataclasses.dataclass(slots=True, frozen=True)
class StartHuntRequest:
    """Body options for POST /hunts/auto."""

    seed_values: list[SingleJson]
    title: str | None = None
    hypothesis: str | None = None
    session_mode: str = constants.DEFAULT_HUNT_SESSION_MODE
    severity: str | None = None
    external_ref: SingleJson | None = None
    reuse_open: bool = False


@dataclasses.dataclass(slots=True, frozen=True)
class ScoutQuestionRequest:
    """Body options for POST /agents/scout/jobs."""

    question: str
    hunt_id: str | None = None
    external_ref: SingleJson | None = None
    initiative: str | None = None


@dataclasses.dataclass(slots=True, frozen=True)
class FindingsQuery:
    """Filters and paging for GET /findings."""

    since: str
    dispositions: tuple[str, ...] = constants.DEFAULT_FINDING_DISPOSITIONS
    limit: int | None = None
    offset: int = 0


@dataclasses.dataclass(slots=True, frozen=True)
class InsightsQuery:
    """Filters and paging for GET /insights."""

    since: str
    severity: str | None = None
    limit: int | None = None
    offset: int = 0


@dataclasses.dataclass(slots=True)
class IndicatorResult:
    """One value from POST /intel/lookup."""

    raw_data: SingleJson
    input: str
    type: str | None
    value: str | None
    status: str
    sighted: bool
    sightings_count: int
    best: SingleJson
    url: str | None = None

    @classmethod
    def from_json(cls, data: SingleJson) -> IndicatorResult:
        return cls(
            raw_data=data,
            input=str(data.get("input") or data.get("value") or ""),
            type=data.get("type"),
            value=data.get("value"),
            status=str(data.get("status") or "unknown").lower(),
            sighted=bool(data.get("sighted")),
            sightings_count=int(data.get("sightings_count") or 0),
            best=data.get("best") or {},
            url=data.get("url") or (data.get("best") or {}).get("url"),
        )

    @property
    def is_known(self) -> bool:
        return self.status == "known"

    @property
    def indicator_id(self) -> str | None:
        return self.best.get("id")

    @property
    def score(self) -> float | None:
        for key in ("effective_confidence", "score", "confidence"):
            value: object = self.best.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
        return None

    def is_suspicious(self, threshold: int) -> bool:
        if not self.is_known or self.best.get("revoked"):
            return False
        score = self.score
        return score is not None and score >= threshold

    def enrichment(self) -> SingleJson:
        best = self.best
        return _clean({
            "status": self.status,
            "type": self.type,
            "confidence": best.get("effective_confidence", best.get("confidence")),
            "score": best.get("score"),
            "tlp": best.get("tlp"),
            "source": _source_name(best.get("source")),
            "state": best.get("state"),
            "first_seen": best.get("first_seen"),
            "last_seen": best.get("last_seen"),
            "sighted": self.sighted,
            "sightings_count": self.sightings_count,
            "link": self.url,
        })


@dataclasses.dataclass(slots=True)
class EntityMatch:
    """One item from GET /entities/search."""

    raw_data: SingleJson
    entity_id: str
    type: str | None
    key: str | None
    label: str | None
    tags: list[str]
    url: str | None = None

    attributes: SingleJson = dataclasses.field(default_factory=dict)

    @classmethod
    def from_json(cls, data: SingleJson) -> EntityMatch:
        tags = data.get("tags") or []
        attributes = data.get("attributes") if isinstance(data.get("attributes"), dict) else {}
        return cls(
            raw_data=data,
            entity_id=str(data.get("id") or ""),
            type=data.get("type"),
            key=data.get("key") or attributes.get("name"),
            label=(
                data.get("label")
                or data.get("display_name")
                or data.get("name")
                or attributes.get("title")
                or attributes.get("name")
            ),
            tags=[str(t.get("name", t)) if isinstance(t, dict) else str(t) for t in tags],
            # by-value entities carry their page link in attributes.url
            url=data.get("url") or attributes.get("url"),
            attributes=attributes,
        )

    def enrichment(self) -> SingleJson:
        summary = self.attributes.get("summary") if isinstance(self.attributes.get("summary"), dict) else {}
        return _clean({
            "status": "known",
            "entity_id": self.entity_id,
            "type": self.type,
            "label": self.label,
            "tags": ", ".join(self.tags) if self.tags else None,
            "first_seen": self.attributes.get("first_seen"),
            "last_seen": summary.get("last_seen") or self.attributes.get("last_seen"),
            "findings": _count(summary.get("findings")),
            "hunts": _count(summary.get("hunts")),
            "link": self.url,
        })


@dataclasses.dataclass(slots=True)
class Hunt:
    """A Huntbase hunt (workbench session)."""

    raw_data: SingleJson
    hunt_id: str
    title: str | None
    status: str
    severity: str | None
    disposition: str | None
    scout_summary: str | None
    latest_verdict: SingleJson
    created_at: str | None
    updated_at: str | None
    url: str | None = None

    @classmethod
    def from_json(cls, data: SingleJson) -> Hunt:
        hunt_id = data.get("id") or data.get("hunt_session_id") or data.get("session_id") or ""
        return cls(
            raw_data=data,
            hunt_id=str(hunt_id),
            title=data.get("title"),
            status=str(data.get("status") or data.get("planning") or "unknown").lower(),
            severity=data.get("severity"),
            disposition=data.get("disposition"),
            scout_summary=data.get("scout_summary"),
            latest_verdict=data.get("latest_verdict") or {},
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            url=data.get("url"),
        )

    @property
    def verdict(self) -> str | None:
        return self.latest_verdict.get("disposition") or self.disposition

    @property
    def summary(self) -> str | None:
        verdict = self.latest_verdict
        return verdict.get("summary") or verdict.get("reason") or self.scout_summary

    @property
    def is_finished(self) -> bool:
        """Closed, or a verdict has been recorded (drafts don't count)."""
        if self.status in constants.HUNT_TERMINAL_STATUSES:
            return True
        verdict = self.latest_verdict
        return bool(verdict.get("disposition")) and verdict.get("kind", "recorded") == "recorded"

    def to_json(self, findings: list[Finding] | None = None) -> SingleJson:
        result: SingleJson = {
            "id": self.hunt_id,
            "title": self.title,
            "status": self.status,
            "severity": self.severity,
            "verdict": self.verdict,
            "summary": self.summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "url": self.url,
        }
        if findings is not None:
            result["findings"] = [finding.to_json() for finding in findings]
        return result


@dataclasses.dataclass(slots=True)
class Finding:
    """A Huntbase finding (GET /findings, GET /sessions/{id}/findings)."""

    raw_data: SingleJson
    finding_id: str
    hunt_id: str | None
    hunt_title: str | None
    title: str
    summary: str | None
    disposition: str | None
    severity: str | None
    entities: list[SingleJson]
    created_at: str | None
    updated_at: str | None
    url: str | None = None

    @classmethod
    def from_json(cls, data: SingleJson) -> Finding:
        return cls(
            raw_data=data,
            finding_id=str(data.get("id") or ""),
            hunt_id=data.get("session_id") or data.get("hunt_id"),
            hunt_title=data.get("session_title") or data.get("hunt_title"),
            title=str(data.get("title") or "Huntbase finding"),
            summary=data.get("summary"),
            disposition=data.get("disposition"),
            severity=data.get("severity"),
            entities=[e for e in data.get("entities") or [] if isinstance(e, dict)],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            url=data.get("url"),
        )

    def to_json(self) -> SingleJson:
        return {
            "id": self.finding_id,
            "hunt_id": self.hunt_id,
            "title": self.title,
            "summary": self.summary,
            "disposition": self.disposition,
            "severity": self.severity,
            "entities": self.entities,
            "created_at": self.created_at,
            "url": self.url,
        }


@dataclasses.dataclass(slots=True)
class Insight:
    """A Huntbase insight (GET /insights)."""

    raw_data: SingleJson
    insight_id: str
    title: str
    severity: str | None
    status: str | None
    time: str | int | float | None
    created_at: str | int | float | None
    source_product: str | None
    watcher_name: str | None
    url: str | None = None

    @classmethod
    def from_json(cls, data: SingleJson) -> Insight:
        return cls(
            raw_data=data,
            insight_id=str(data.get("event_id") or data.get("id") or ""),
            title=str(data.get("message") or data.get("title") or "Huntbase insight"),
            severity=data.get("severity"),
            status=data.get("status"),
            time=data.get("time"),
            created_at=data.get("normalized_at") or data.get("created_at") or data.get("time"),
            source_product=data.get("source_product"),
            watcher_name=data.get("watcher_name"),
            url=data.get("url"),
        )

    def entities(self) -> list[SingleJson]:
        """Best-effort list of {type, value} pairs from the insight's evidences."""
        found: list[SingleJson] = []
        for evidence in self.raw_data.get("evidences") or []:
            if not isinstance(evidence, dict):
                continue
            for key, kind in (
                ("src_ip", "ip"),
                ("dst_ip", "ip"),
                ("ip", "ip"),
                ("hostname", "host"),
                ("device_hostname", "host"),
                ("user", "user"),
                ("user_name", "user"),
                ("domain", "domain"),
                ("url", "url"),
                ("file_hash", "hash"),
                ("hash", "hash"),
            ):
                value = evidence.get(key)
                if isinstance(value, str) and value:
                    found.append({"type": kind, "value": value})
        return found


@dataclasses.dataclass(slots=True)
class ScoutJob:
    """An Ask Scout job."""

    raw_data: SingleJson
    job_id: str
    status: str
    answer: str | None
    summary: str | None
    error: str | None
    poll_after_seconds: int | None
    url: str | None = None

    @classmethod
    def from_json(cls, data: SingleJson) -> ScoutJob:
        result = data.get("result") if isinstance(data.get("result"), dict) else {}
        return cls(
            raw_data=data,
            job_id=str(data.get("job_id") or data.get("id") or data.get("run_id") or ""),
            status=str(data.get("state") or data.get("status") or "queued").lower(),
            answer=data.get("answer") or result.get("answer"),
            summary=data.get("summary") or result.get("summary"),
            error=data.get("error") or result.get("error"),
            poll_after_seconds=data.get("poll_after_seconds"),
            url=data.get("url") or result.get("url"),
        )

    @property
    def is_done(self) -> bool:
        return self.status in constants.SCOUT_TERMINAL_OK

    @property
    def is_failed(self) -> bool:
        return self.status in constants.SCOUT_TERMINAL_FAILED

    def to_json(self) -> SingleJson:
        data = self.raw_data
        return _clean({
            "job_id": self.job_id,
            "status": self.status,
            "answer": self.answer,
            "answer_truncated": data.get("answer_truncated"),
            "summary": self.summary,
            "clarification_question": data.get("clarification_question"),
            "references": data.get("references"),
            "pending_approvals": data.get("pending_approvals"),
            "suggested_next_questions": data.get("suggested_next_questions"),
            "hunt_ids": data.get("hunt_ids"),
            "links": data.get("links"),
            "url": self.url,
        })


@dataclasses.dataclass(slots=True)
class Watchlist:
    raw_data: SingleJson
    watchlist_id: str
    name: str
    value_count: int | None

    @classmethod
    def from_json(cls, data: SingleJson) -> Watchlist:
        return cls(
            raw_data=data,
            watchlist_id=str(data.get("id") or ""),
            name=str(data.get("name") or ""),
            value_count=data.get("value_count"),
        )


@dataclasses.dataclass(slots=True)
class Proposal:
    raw_data: SingleJson
    proposal_id: str
    title: str | None
    status: str | None
    created_at: str | None
    values_count: int | None
    url: str | None = None

    @classmethod
    def from_json(cls, data: SingleJson) -> Proposal:
        return cls(
            raw_data=data,
            proposal_id=str(data.get("id") or data.get("proposal_id") or ""),
            title=data.get("summary") or data.get("title") or data.get("action"),
            status=data.get("state") or data.get("status"),
            created_at=data.get("created_at"),
            values_count=data.get("values_count"),
            url=data.get("url"),
        )

    def to_json(self) -> SingleJson:
        return {
            "id": self.proposal_id,
            "title": self.title,
            "action": self.raw_data.get("action"),
            "status": self.status,
            "created_at": self.created_at,
            "values_count": self.values_count,
            "url": self.url,
        }
