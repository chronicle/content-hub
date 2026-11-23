from __future__ import annotations

import time
import urllib.parse
from typing import TYPE_CHECKING, Any

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
    from collections.abc import Iterable

    SingleJson = dict[str, Any]


def _sleep(seconds: float) -> None:
    """Indirection so tests can skip real waits."""
    time.sleep(seconds)


def normalize_api_root(api_root: str) -> str:
    """Return the API root without a trailing slash, adding /api/v1 when missing."""
    root = (api_root or "").strip().rstrip("/")
    if not root:
        msg = "The API Root is empty. Set it to https://<your Huntbase host>/api/v1."
        raise HuntbaseConfigurationError(msg)
    parsed = urllib.parse.urlparse(root)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        msg = f"The API Root '{root}' is not a valid http(s) URL."
        raise HuntbaseConfigurationError(msg)
    if not parsed.path or parsed.path == "/":
        root = f"{root}/api/v1"
    return root


def app_root_from_api_root(api_root: str) -> str:
    """Derive the Huntbase web app root (used for deep links) from the API root."""
    root = api_root.rstrip("/")
    for suffix in ("/api/v1", "/api"):
        if root.endswith(suffix):
            return root[: -len(suffix)]
    return root


def _error_detail(response: requests.Response) -> str:
    """Extract a readable message from an RFC 9457 problem or FastAPI error body."""
    try:
        body = response.json()
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


class HuntbaseManager:
    """Thin client for the Huntbase REST API, authenticated with a personal API key."""

    def __init__(
        self,
        api_root: str,
        api_key: str,
        verify_ssl: bool = True,
        logger: Any = None,  # noqa: ANN401
        session: requests.Session | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            msg = "The API Key is empty. Create a personal API key in Huntbase under Settings > API keys."
            raise HuntbaseConfigurationError(msg)
        self.api_root = normalize_api_root(api_root)
        self.app_root = app_root_from_api_root(self.api_root)
        self.logger = logger
        self.session = session or CreateSession.create_session()
        self.session.verify = verify_ssl
        self.session.headers.update({
            "Authorization": f"Bearer {api_key.strip()}",
            "Accept": "application/json",
            "User-Agent": constants.USER_AGENT,
        })

    # ------------------------------------------------------------------ HTTP

    def _url(self, endpoint: str, **path_params: str) -> str:
        path = constants.ENDPOINTS[endpoint].format(**{
            key: urllib.parse.quote(str(value), safe="") for key, value in path_params.items()
        })
        return f"{self.api_root}{path}"

    def _log(self, message: str) -> None:
        if self.logger is not None:
            self.logger.info(message)

    def _request(
        self,
        method: str,
        endpoint: str,
        path_params: dict[str, str] | None = None,
        params: Any = None,  # noqa: ANN401
        json_body: Any = None,  # noqa: ANN401
    ) -> Any:  # noqa: ANN401
        url = self._url(endpoint, **(path_params or {}))
        attempt = 0
        while True:
            attempt += 1
            try:
                response = self.session.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    timeout=constants.REQUEST_TIMEOUT_SECONDS,
                )
            except (requests.ConnectionError, requests.Timeout) as error:
                if attempt <= constants.MAX_RETRIES:
                    self._log(f"Huntbase unreachable ({type(error).__name__}); retry {attempt}")
                    _sleep(constants.RETRY_BACKOFF_SECONDS * attempt)
                    continue
                msg = f"Could not reach Huntbase at {self.api_root}: {type(error).__name__}"
                raise HuntbaseConnectionError(msg) from error

            if response.status_code in constants.RETRYABLE_STATUS_CODES and attempt <= constants.MAX_RETRIES:
                wait = self._retry_wait(response, attempt)
                self._log(f"Huntbase answered {response.status_code} on {method} {endpoint}; retrying in {wait}s")
                _sleep(wait)
                continue

            self._raise_for_status(response, method, endpoint)
            if response.status_code == 204 or not response.content:
                return {}
            try:
                return response.json()
            except ValueError as error:
                msg = f"Huntbase returned a non-JSON response for {method} {endpoint}"
                raise HuntbaseApiError(msg, response.status_code) from error

    @staticmethod
    def _retry_wait(response: requests.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After") if response.headers else None
        if retry_after:
            try:
                return min(float(retry_after), constants.MAX_RETRY_AFTER_SECONDS)
            except ValueError:
                pass
        return constants.RETRY_BACKOFF_SECONDS * attempt

    @staticmethod
    def _raise_for_status(response: requests.Response, method: str, endpoint: str) -> None:
        status = response.status_code
        if status < 400:
            return
        detail = _error_detail(response)
        where = f"{method} {constants.ENDPOINTS[endpoint]}"
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
        if status == 429:
            msg = f"Huntbase rate limit reached on {where}. Try again later."
            raise HuntbaseRateLimitError(msg, status)
        msg = f"Huntbase returned {status} for {where}: {detail}"
        raise HuntbaseApiError(msg, status)

    # ---------------------------------------------------------------- links

    def app_link(self, kind: str, **values: str) -> str:
        path = constants.APP_PATHS[kind].format(**{k: urllib.parse.quote(str(v), safe="") for k, v in values.items()})
        separator = "&" if "?" in path else "?"
        return f"{self.app_root}{path}{separator}src={constants.LINK_SOURCE}"

    # ------------------------------------------------------------- actions

    def ping(self) -> None:
        self._request("GET", "ping")

    def lookup_indicators(self, values: Iterable[str]) -> list[IndicatorResult]:
        unique = list(dict.fromkeys(v for v in values if v))
        results: list[IndicatorResult] = []
        for start in range(0, len(unique), constants.INTEL_LOOKUP_BATCH_SIZE):
            batch = unique[start : start + constants.INTEL_LOOKUP_BATCH_SIZE]
            data = self._request("POST", "intel_lookup", json_body={"values": batch, "include_unknown": True})
            for item in data.get("results") or []:
                result = IndicatorResult.from_json(item)
                if not result.url and result.indicator_id:
                    result.url = self.app_link("indicator", indicator_id=result.indicator_id)
                results.append(result)
        return results

    def find_entities(self, value: str, entity_type: str | None = None) -> list[EntityMatch]:
        """Exact-value entity lookup (GET /entities/by-value), newest first."""
        params: dict[str, Any] = {"value": value, "include": "summary", "limit": constants.ENTITY_SEARCH_LIMIT}
        if entity_type:
            params["entity_type"] = entity_type
        data = self._request("GET", "entity_by_value", params=params)
        items = (data.get("entities") or data.get("items")) if isinstance(data, dict) else data
        matches = []
        for item in items or []:
            match = EntityMatch.from_json(item)
            if not match.url and match.entity_id:
                match.url = self.app_link("entity", entity_id=match.entity_id)
            matches.append(match)
        return matches

    def start_hunt(
        self,
        seed_values: list[SingleJson],
        title: str | None = None,
        hypothesis: str | None = None,
        session_mode: str = constants.DEFAULT_HUNT_SESSION_MODE,
        severity: str | None = None,
        external_ref: SingleJson | None = None,
        reuse_open: bool = False,
    ) -> Hunt:
        if not seed_values:
            msg = "A hunt needs at least one seed value."
            raise HuntbaseConfigurationError(msg)
        body: SingleJson = {
            "seed_values": seed_values[: constants.MAX_HUNT_SEED_VALUES],
            "session_mode": session_mode,
        }
        if title:
            body["title"] = title
        if hypothesis:
            body["hypothesis"] = hypothesis
        if severity:
            body["severity"] = severity
        if external_ref:
            body["external_ref"] = external_ref
        # Huntbase matches an open hunt for the same case by external_ref.url
        if reuse_open and (external_ref or {}).get("url"):
            body["reuse_open"] = True
        data = self._request("POST", "start_hunt", json_body=body)
        hunt = Hunt.from_json(data)
        if not hunt.hunt_id:
            msg = "Huntbase accepted the hunt but returned no hunt id."
            raise HuntbaseApiError(msg)
        hunt.url = hunt.url or self.app_link("hunt", hunt_id=hunt.hunt_id)
        if title and not hunt.title:
            hunt.title = title
        return hunt

    def get_hunt(self, hunt_id: str) -> Hunt:
        hunt = Hunt.from_json(self._request("GET", "hunt", path_params={"hunt_id": hunt_id}))
        hunt.hunt_id = hunt.hunt_id or hunt_id
        hunt.url = hunt.url or self.app_link("hunt", hunt_id=hunt.hunt_id)
        return hunt

    def get_hunt_findings(self, hunt_id: str) -> list[Finding]:
        data = self._request("GET", "hunt_findings", path_params={"hunt_id": hunt_id})
        items = data.get("items") if isinstance(data, dict) else data
        return [self._finding(item) for item in items or []]

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

    def list_findings(
        self,
        since: str,
        dispositions: Iterable[str],
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Finding]:
        params: list[tuple[str, Any]] = [
            ("since", since),
            ("limit", limit or constants.CONNECTOR_PAGE_SIZE),
            ("offset", offset),
            ("order", "asc"),
        ]
        params.extend(("disposition", d) for d in dispositions)
        data = self._request("GET", "findings", params=params)
        items = data.get("items") if isinstance(data, dict) else data
        return [self._finding(item) for item in items or []]

    def list_insights(
        self,
        since: str,
        severity: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Insight]:
        params: list[tuple[str, Any]] = [
            ("from", since),
            ("limit", limit or constants.CONNECTOR_PAGE_SIZE),
            ("offset", offset),
            ("sort", "time"),
            ("order", "asc"),
        ]
        if severity:
            params.append(("severity", severity.capitalize()))
        data = self._request("GET", "insights", params=params)
        items = data.get("items") if isinstance(data, dict) else data
        return [self._insight(item) for item in items or []]

    def ask_scout(
        self,
        question: str,
        hunt_id: str | None = None,
        external_ref: SingleJson | None = None,
        initiative: str | None = None,
    ) -> ScoutJob:
        body: SingleJson = {"question": question}
        if hunt_id:
            body["hunt_id"] = hunt_id
        if initiative:
            body["initiative"] = initiative
        if external_ref:
            body["external_ref"] = external_ref
        job = ScoutJob.from_json(self._request("POST", "scout_jobs", json_body=body))
        if not job.job_id:
            msg = "Huntbase accepted the question but returned no job id."
            raise HuntbaseApiError(msg)
        return job

    def get_scout_job(self, job_id: str) -> ScoutJob:
        job = ScoutJob.from_json(self._request("GET", "scout_job", path_params={"job_id": job_id}))
        job.job_id = job.job_id or job_id
        return job

    def list_watchlists(self) -> list[Watchlist]:
        data = self._request("GET", "watchlists")
        items = data.get("items") if isinstance(data, dict) else data
        return [Watchlist.from_json(item) for item in items or []]

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
        return self._request(
            "POST",
            "watchlist_values",
            path_params={"watchlist_id": watchlist_id},
            json_body={"values": values},
        )

    def list_pending_approvals(self, limit: int = 50) -> list[Proposal]:
        data = self._request("GET", "proposals", params={"limit": limit})
        items = data.get("items") if isinstance(data, dict) else data
        proposals = []
        for item in items or []:
            proposal = Proposal.from_json(item)
            if not proposal.url and proposal.proposal_id:
                proposal.url = self.app_link("approval", proposal_id=proposal.proposal_id)
            proposals.append(proposal)
        return proposals
