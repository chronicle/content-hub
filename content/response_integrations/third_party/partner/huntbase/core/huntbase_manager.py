from __future__ import annotations

import dataclasses
import time
import urllib.parse
import uuid
from typing import TYPE_CHECKING

import requests
from TIPCommon.base.utils import CreateSession

from . import constants
from .datamodels import (
    EntityMatch,
    Finding,
    Hunt,
    IndicatorResult,
    Insight,
    Proposal,
    ScoutJob,
    Watchlist,
)
from .huntbase_exceptions import (
    HuntbaseApiError,
    HuntbaseAuthError,
    HuntbaseConfigurationError,
    HuntbaseConnectionError,
    HuntbaseNotFoundError,
    HuntbasePermissionError,
    HuntbaseRateLimitError,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from TIPCommon.base.interfaces.logger import Logger
    from TIPCommon.types import JSON, SingleJson

    from .datamodels import (
        FindingsQuery,
        HuntbaseConfig,
        InsightsQuery,
        ScoutQuestionRequest,
        StartHuntRequest,
    )

    QueryParams = SingleJson | list[tuple[str, str | int]]


def _sleep(seconds: float) -> None:
    """Indirection so tests can skip real waits."""
    time.sleep(seconds)


def normalize_api_root(api_root: str) -> str:
    """Return the HTTPS API root without a trailing slash, adding /api/v1 when missing."""
    root = (api_root or "").strip().rstrip("/")
    if not root:
        msg = "The API Root is empty. Set it to https://<your Huntbase host>/api/v1."
        raise HuntbaseConfigurationError(msg)
    parsed = urllib.parse.urlparse(root)
    try:
        hostname = (parsed.hostname or "").lower()
        has_credentials = bool(parsed.username or parsed.password)
    except ValueError:
        hostname, has_credentials = "", False
    if parsed.scheme.lower() != "https" or not hostname or has_credentials:
        msg = f"The API Root '{_redact(parsed)}' must be a valid https:// URL without embedded credentials."
        raise HuntbaseConfigurationError(msg)
    if hostname in constants.BLOCKED_API_HOSTS or hostname.startswith(constants.LINK_LOCAL_PREFIX):
        msg = f"The API Root host '{hostname}' is not permitted."
        raise HuntbaseConfigurationError(msg)
    if not parsed.path or parsed.path == "/":
        root = f"{root}/api/v1"
    return root


def _redact(parsed: urllib.parse.ParseResult) -> str:
    """The URL for error messages, without any user:password@ part."""
    netloc = parsed.netloc.rsplit("@", 1)[-1]
    return urllib.parse.urlunparse(parsed._replace(netloc=netloc))


def app_root_from_api_root(api_root: str) -> str:
    """Derive the Huntbase web app root (used for deep links) from the API root."""
    root = api_root.rstrip("/")
    for suffix in ("/api/v1", "/api"):
        if root.endswith(suffix):
            return root[: -len(suffix)]
    return root


def _clean_api_key(api_key: str) -> str:
    key = (api_key or "").strip()
    if not key:
        msg = "The API Key is empty. Create a personal API key in Huntbase under Settings > API keys."
        raise HuntbaseConfigurationError(msg)
    if "\r" in key or "\n" in key:
        msg = "The API Key must not contain line breaks. Paste the key again as a single line."
        raise HuntbaseConfigurationError(msg)
    return key


def _error_detail(response: requests.Response) -> str:
    """Extract a readable message from an RFC 9457 problem or FastAPI error body."""
    try:
        body: object = response.json()
    except ValueError:
        text = (response.text or "").strip()
        return text[:300]
    if isinstance(body, dict):
        detail = body.get("detail")
        if isinstance(detail, str) and detail:
            return detail
        if isinstance(detail, list):
            parts = [str(item.get("msg", item)) if isinstance(item, dict) else str(item) for item in detail]
            return "; ".join(parts)[:300]
        for key in ("title", "message", "error"):
            if isinstance(body.get(key), str) and body.get(key):
                return body[key]
    return str(body)[:300]


def _items(data: JSON, key: str = "items") -> list[SingleJson]:
    """The list of items from a paged {"items": [...]} body or a bare list."""
    items = data.get(key) if isinstance(data, dict) else data
    return [item for item in items or [] if isinstance(item, dict)]


@dataclasses.dataclass(slots=True, frozen=True)
class _RequestSpec:
    """One logical API call; its attempts share every field, including the headers."""

    method: str
    endpoint: str
    path_params: Mapping[str, str] = dataclasses.field(default_factory=dict)
    params: QueryParams | None = None
    json_body: SingleJson | None = None
    headers: Mapping[str, str] = dataclasses.field(default_factory=dict)
    idempotent: bool = True

    @property
    def where(self) -> str:
        return f"{self.method} {constants.ENDPOINTS[self.endpoint]}"


def _should_retry(status_code: int, spec: _RequestSpec) -> bool:
    """GETs and idempotent POSTs retry on 429/5xx; other POSTs only when rate limited (never processed)."""
    if spec.idempotent:
        return status_code in constants.RETRYABLE_STATUS_CODES
    return status_code == constants.RATE_LIMIT_STATUS_CODE


def _retry_wait(response: requests.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After") if response.headers else None
    if retry_after:
        try:
            return min(float(retry_after), constants.MAX_RETRY_AFTER_SECONDS)
        except ValueError:
            pass
    return constants.RETRY_BACKOFF_SECONDS * attempt


def _raise_for_status(response: requests.Response, spec: _RequestSpec) -> None:
    status = response.status_code
    if status < 400:
        return
    detail = _error_detail(response)
    where = spec.where
    if status == 401:
        msg = "Huntbase rejected the API key (401). Check that the key is valid, not expired and not revoked."
        raise HuntbaseAuthError(msg, status)
    if status == 403:
        msg = (
            f"The API key is not allowed to call {where} (403): {detail}. "
            "Use a personal API key with the scopes listed in the integration documentation."
        )
        raise HuntbasePermissionError(msg, status)
    if status == 402:
        msg = f"Your Huntbase plan does not include this feature ({where}): {detail}"
        raise HuntbasePermissionError(msg, status)
    if status == 404:
        msg = f"Not found in Huntbase ({where}): {detail}"
        raise HuntbaseNotFoundError(msg, status)
    if status == constants.RATE_LIMIT_STATUS_CODE:
        msg = f"Huntbase rate limit reached on {where}. Try again later."
        raise HuntbaseRateLimitError(msg, status)
    msg = f"Huntbase returned {status} for {where}: {detail}"
    raise HuntbaseApiError(msg, status)


def _parse_body(response: requests.Response, spec: _RequestSpec) -> JSON:
    if response.status_code == 204 or not response.content:
        return {}
    try:
        body: JSON = response.json()
    except ValueError as error:
        msg = f"Huntbase returned a non-JSON response for {spec.where}"
        raise HuntbaseApiError(msg, response.status_code) from error
    return body


class HuntbaseManager:
    """Thin client for the Huntbase REST API, authenticated with a personal API key."""

    def __init__(
        self,
        config: HuntbaseConfig,
        logger: Logger | None = None,
        session: requests.Session | None = None,
    ) -> None:
        api_key = _clean_api_key(config.api_key)
        self.api_root = normalize_api_root(config.api_root)
        self.app_root = app_root_from_api_root(self.api_root)
        self.logger = logger
        self.session = session or CreateSession.create_session()
        self.session.verify = config.verify_ssl
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": constants.USER_AGENT,
        })

    def close(self) -> None:
        """Close the pooled connections of the HTTP session."""
        self.session.close()

    def __enter__(self) -> HuntbaseManager:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _url(self, endpoint: str, path_params: Mapping[str, str]) -> str:
        path = constants.ENDPOINTS[endpoint].format(**{
            key: urllib.parse.quote(str(value), safe="") for key, value in path_params.items()
        })
        return f"{self.api_root}{path}"

    def _log(self, message: str) -> None:
        if self.logger is not None:
            self.logger.info(message)

    def _get(
        self,
        endpoint: str,
        params: QueryParams | None = None,
        path_params: Mapping[str, str] | None = None,
    ) -> JSON:
        return self._send(_RequestSpec("GET", endpoint, path_params=path_params or {}, params=params))

    def _post(
        self,
        endpoint: str,
        body: SingleJson,
        path_params: Mapping[str, str] | None = None,
    ) -> JSON:
        headers: dict[str, str] = {}
        if endpoint in constants.IDEMPOTENCY_KEY_ENDPOINTS:
            # One key per logical call, reused by every retry of it
            headers[constants.IDEMPOTENCY_KEY_HEADER] = str(uuid.uuid4())
        spec = _RequestSpec(
            "POST",
            endpoint,
            path_params=path_params or {},
            json_body=body,
            headers=headers,
            idempotent=endpoint in constants.IDEMPOTENT_POST_ENDPOINTS,
        )
        return self._send(spec)

    def _send(self, spec: _RequestSpec) -> JSON:
        url = self._url(spec.endpoint, spec.path_params)
        max_attempts = constants.MAX_RETRIES + 1
        for attempt in range(1, max_attempts + 1):
            can_retry = attempt < max_attempts
            try:
                response = self.session.request(
                    spec.method,
                    url,
                    params=spec.params,
                    json=spec.json_body,
                    headers=dict(spec.headers) or None,
                    timeout=constants.REQUEST_TIMEOUT_SECONDS,
                )
            except (requests.ConnectionError, requests.Timeout) as error:
                if spec.idempotent and can_retry:
                    self._log(f"Huntbase unreachable ({type(error).__name__}); retry {attempt}")
                    _sleep(constants.RETRY_BACKOFF_SECONDS * attempt)
                    continue
                raise self._connection_error(spec, error) from error

            if can_retry and _should_retry(response.status_code, spec):
                wait = _retry_wait(response, attempt)
                self._log(f"Huntbase answered {response.status_code} on {spec.where}; retrying in {wait}s")
                _sleep(wait)
                continue

            _raise_for_status(response, spec)
            return _parse_body(response, spec)

        msg = f"Huntbase did not answer {spec.where} after {max_attempts} attempts."
        raise HuntbaseConnectionError(msg)

    def _connection_error(self, spec: _RequestSpec, error: Exception) -> HuntbaseConnectionError:
        msg = f"Could not reach Huntbase at {self.api_root}: {type(error).__name__}"
        if not spec.idempotent:
            msg += (
                f". {spec.where} was not retried because Huntbase may already have accepted it; "
                "check Huntbase before running the action again."
            )
        return HuntbaseConnectionError(msg)

    def app_link(self, kind: str, **values: str) -> str:
        path = constants.APP_PATHS[kind].format(**{k: urllib.parse.quote(str(v), safe="") for k, v in values.items()})
        separator = "&" if "?" in path else "?"
        return f"{self.app_root}{path}{separator}src={constants.LINK_SOURCE}"

    def ping(self) -> None:
        self._get("ping")

    def lookup_indicators(self, values: Iterable[str]) -> list[IndicatorResult]:
        unique: list[str] = list(dict.fromkeys(v for v in values if v))
        results: list[IndicatorResult] = []
        for start in range(0, len(unique), constants.INTEL_LOOKUP_BATCH_SIZE):
            batch = unique[start : start + constants.INTEL_LOOKUP_BATCH_SIZE]
            data = self._post("intel_lookup", {"values": batch, "include_unknown": True})
            for item in _items(data, "results") if isinstance(data, dict) else []:
                result = IndicatorResult.from_json(item)
                if not result.url and result.indicator_id:
                    result.url = self.app_link("indicator", indicator_id=result.indicator_id)
                results.append(result)
        return results

    def find_entities(self, value: str, entity_type: str | None = None) -> list[EntityMatch]:
        """Exact-value entity lookup (GET /entities/by-value), newest first."""
        params: SingleJson = {"value": value, "include": "summary", "limit": constants.ENTITY_SEARCH_LIMIT}
        if entity_type:
            params["entity_type"] = entity_type
        data = self._get("entity_by_value", params=params)
        items = (data.get("entities") or data.get("items")) if isinstance(data, dict) else data
        matches: list[EntityMatch] = []
        for item in items or []:
            match = EntityMatch.from_json(item)
            if not match.url and match.entity_id:
                match.url = self.app_link("entity", entity_id=match.entity_id)
            matches.append(match)
        return matches

    def start_hunt(self, request: StartHuntRequest) -> Hunt:
        if not request.seed_values:
            msg = "A hunt needs at least one seed value."
            raise HuntbaseConfigurationError(msg)
        body: SingleJson = {
            "seed_values": request.seed_values[: constants.MAX_HUNT_SEED_VALUES],
            "session_mode": request.session_mode,
        }
        if request.title:
            body["title"] = request.title
        if request.hypothesis:
            body["hypothesis"] = request.hypothesis
        if request.severity:
            body["severity"] = request.severity
        if request.external_ref:
            body["external_ref"] = request.external_ref
        # Huntbase matches an open hunt for the same case by external_ref.url
        if request.reuse_open and (request.external_ref or {}).get("url"):
            body["reuse_open"] = True
        hunt = Hunt.from_json(self._post("start_hunt", body))
        if not hunt.hunt_id:
            msg = "Huntbase accepted the hunt but returned no hunt id."
            raise HuntbaseApiError(msg)
        hunt.url = hunt.url or self.app_link("hunt", hunt_id=hunt.hunt_id)
        if request.title and not hunt.title:
            hunt.title = request.title
        return hunt

    def get_hunt(self, hunt_id: str) -> Hunt:
        hunt = Hunt.from_json(self._get("hunt", path_params={"hunt_id": hunt_id}))
        hunt.hunt_id = hunt.hunt_id or hunt_id
        hunt.url = hunt.url or self.app_link("hunt", hunt_id=hunt.hunt_id)
        return hunt

    def get_hunt_findings(self, hunt_id: str) -> list[Finding]:
        data = self._get("hunt_findings", path_params={"hunt_id": hunt_id})
        return [self._finding(item) for item in _items(data)]

    def _finding(self, item: SingleJson) -> Finding:
        finding = Finding.from_json(item)
        if not finding.url and finding.finding_id:
            finding.url = self.app_link("finding", finding_id=finding.finding_id)
        return finding

    def _insight(self, item: SingleJson) -> Insight:
        insight = Insight.from_json(item)
        if not insight.url and insight.insight_id:
            insight.url = self.app_link("insight", insight_id=insight.insight_id)
        return insight

    def list_findings(self, query: FindingsQuery) -> list[Finding]:
        params: list[tuple[str, str | int]] = [
            ("since", query.since),
            ("limit", query.limit or constants.CONNECTOR_PAGE_SIZE),
            ("offset", query.offset),
            ("order", "asc"),
        ]
        params.extend(("disposition", d) for d in query.dispositions)
        data = self._get("findings", params=params)
        return [self._finding(item) for item in _items(data)]

    def list_insights(self, query: InsightsQuery) -> list[Insight]:
        params: list[tuple[str, str | int]] = [
            ("from", query.since),
            ("limit", query.limit or constants.CONNECTOR_PAGE_SIZE),
            ("offset", query.offset),
            ("sort", "time"),
            ("order", "asc"),
        ]
        if query.severity:
            params.append(("severity", query.severity.capitalize()))
        data = self._get("insights", params=params)
        return [self._insight(item) for item in _items(data)]

    def ask_scout(self, request: ScoutQuestionRequest) -> ScoutJob:
        body: SingleJson = {"question": request.question}
        if request.hunt_id:
            body["hunt_id"] = request.hunt_id
        if request.initiative:
            body["initiative"] = request.initiative
        if request.external_ref:
            body["external_ref"] = request.external_ref
        job = ScoutJob.from_json(self._post("scout_jobs", body))
        if not job.job_id:
            msg = "Huntbase accepted the question but returned no job id."
            raise HuntbaseApiError(msg)
        return job

    def get_scout_job(self, job_id: str) -> ScoutJob:
        job = ScoutJob.from_json(self._get("scout_job", path_params={"job_id": job_id}))
        job.job_id = job.job_id or job_id
        return job

    def list_watchlists(self) -> list[Watchlist]:
        return [Watchlist.from_json(item) for item in _items(self._get("watchlists"))]

    def find_watchlist(self, name_or_id: str) -> Watchlist:
        wanted = name_or_id.strip()
        watchlists = self.list_watchlists()
        for watchlist in watchlists:
            if watchlist.watchlist_id == wanted:
                return watchlist
        for watchlist in watchlists:
            if watchlist.name.casefold() == wanted.casefold():
                return watchlist
        names = ", ".join(sorted(w.name for w in watchlists)) or "none"
        msg = f"No Huntbase watch list named '{wanted}'. Available watch lists: {names}."
        raise HuntbaseNotFoundError(msg, 404)

    def add_watchlist_values(self, watchlist_id: str, values: list[str]) -> SingleJson:
        data = self._post(
            "watchlist_values",
            {"values": values},
            path_params={"watchlist_id": watchlist_id},
        )
        return data if isinstance(data, dict) else {}

    def list_pending_approvals(self, limit: int) -> list[Proposal]:
        data = self._get("proposals", params={"limit": limit})
        proposals: list[Proposal] = []
        for item in _items(data):
            proposal = Proposal.from_json(item)
            if not proposal.url and proposal.proposal_id:
                proposal.url = self.app_link("approval", proposal_id=proposal.proposal_id)
            proposals.append(proposal)
        return proposals
