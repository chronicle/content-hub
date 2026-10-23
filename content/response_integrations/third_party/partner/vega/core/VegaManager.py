"""
Vega HTTP manager: login_machine session JWT + GraphQL /api/v1/query.

Does not import the SecOps SDK.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


import json
import logging
import time
from .constants import (
    ALERT_EVENTS_ID_BATCH,
    ALERT_EVENTS_PAGE_SIZE,
    DEFAULT_HTTP_TIMEOUT,
    GET_ALERT_EVENTS_QUERY,
    GET_ALERTS_QUERY,
    GET_INCIDENT_TIMELINE_QUERY,
    GET_INCIDENTS_QUERY,
    GRAPHQL_PAGE_SIZE,
    LOGIN_PATH,
    MAX_EVENTS_PER_ALERT,
    MSG_BAD_REQUEST,
    MSG_FORBIDDEN,
    MSG_INVALID_ACCESS_KEY,
    MSG_INVALID_ACCESS_KEY_ID,
    MSG_INVALID_API_ROOT,
    MSG_NOT_FOUND,
    MSG_RATE_LIMIT,
    MSG_SERVER_ERROR,
    QUERY_PATH,
    SERVER_ERROR_RETRIES,
    SERVER_ERROR_WAIT_SECONDS,
    SYNC_RESOLVED_STATUS,
    TIMELINE_MAX_FETCH,
    TIMELINE_PAGE_SIZE,
    UPDATE_ALERTS_MUTATION,
    UPDATE_ALERTS_STATUS_MUTATION,
    UPDATE_INCIDENTS_MUTATION,
    UPDATE_INCIDENTS_STATUS_MUTATION,
)
from .exceptions import (
    VegaBadRequestException,
    VegaException,
    VegaForbiddenException,
    VegaNotFoundException,
    VegaRateLimitException,
    VegaTimeoutException,
    VegaUnauthorizedException,
    VegaValidationException,
)
from .rate_limit import RateLimitController
from .alert_events_parse import (
    _graphql_alert_id,
    _optional_int,
    _same_alert_id,
    events_for_alert_bucket,
    parse_alert_events_results,
)
from .utils import classify_credential_error, normalize_api_root, require_secret, safe_log

logger = logging.getLogger(__name__)


def is_rate_limit_message(value: Any) -> bool:
    """True for Vega HTTP 429 text and GraphQL 'Rate limit exceeded' bodies."""
    text = str(value or "").strip().lower()
    if not text:
        return False
    return "rate limit" in text or "too many requests" in text


def _requests() -> Any:
    import requests

    return requests


@dataclass(frozen=True)
class VegaClientConfig:
    """Connection settings for VegaManager."""

    api_root: str
    access_key_id: str
    access_key: str
    verify_ssl: bool = True
    timeout: float | tuple[float, float] = DEFAULT_HTTP_TIMEOUT


class VegaManager:
    """Client for Vega login and GraphQL APIs."""

    def __init__(
        self,
        config: VegaClientConfig,
        logger_instance: Any = None,
        session: Any = None,
        rate_limiter: RateLimitController | None = None,
        sleeper: Any = None,
    ) -> None:
        self.api_root = normalize_api_root(config.api_root)
        self.access_key_id = require_secret(config.access_key_id, "Access Key ID")
        self.access_key = require_secret(config.access_key, "Access Key")
        self.verify_ssl = bool(config.verify_ssl)
        self.timeout = config.timeout
        self.logger = logger_instance or logger
        self.session = session or _requests().Session()
        self.session.trust_env = False
        self.session.verify = self.verify_ssl
        self.rate_limiter = rate_limiter or RateLimitController(sleeper=sleeper or __import__("time").sleep)
        self._sleeper = sleeper or __import__("time").sleep
        self._jwt: str | None = None
        self.last_fetch_truncated = False

    def _log(self, level: str, msg: str, *args) -> None:
        safe_log(self.logger, level, msg, *args)

    def _url(self, path: str) -> str:
        return f"{self.api_root}{path}"

    def _response_error_text(self, response: Any) -> str:
        try:
            payload = response.json()
        except Exception:
            return str(getattr(response, "text", "") or "")
        if isinstance(payload, dict):
            error = payload.get("error") or payload.get("errors") or payload.get("message")
            if isinstance(error, dict):
                return str(error.get("message") or error.get("code") or error)
            if isinstance(error, list) and error:
                first = error[0]
                if isinstance(first, dict):
                    return str(first.get("message") or first.get("code") or first)
                return str(first)
            if error:
                return str(error)
            return str(payload)
        return str(payload)

    def _raise_http(self, response: Any, path: str = "") -> None:
        status = response.status_code
        classified = classify_credential_error(self._response_error_text(response))
        if classified:
            raise VegaUnauthorizedException(classified)
        if path == LOGIN_PATH:
            if status == 400:
                raise VegaUnauthorizedException(MSG_INVALID_ACCESS_KEY_ID)
            if status == 404:
                raise VegaValidationException(MSG_INVALID_API_ROOT)
            if status in (401, 403) or status >= 500:
                raise VegaUnauthorizedException(MSG_INVALID_ACCESS_KEY)
        if status == 400:
            raise VegaBadRequestException(MSG_BAD_REQUEST)
        if status == 401:
            raise VegaUnauthorizedException(MSG_INVALID_ACCESS_KEY_ID)
        if status == 403:
            raise VegaForbiddenException(MSG_FORBIDDEN)
        if status == 404:
            raise VegaNotFoundException(MSG_NOT_FOUND)
        if status == 429:
            raise VegaRateLimitException(MSG_RATE_LIMIT)
        if status >= 500:
            raise VegaException(MSG_SERVER_ERROR)
        raise VegaException("Vega request failed. Please try again.")

    def _send(self, method: str, path: str, **kwargs):
        requests = _requests()
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("verify", self.verify_ssl)
        try:
            return self.session.request(method, self._url(path), **kwargs)
        except requests.Timeout as exc:
            raise VegaTimeoutException(MSG_INVALID_API_ROOT) from exc
        except requests.exceptions.SSLError as exc:
            raise VegaValidationException(MSG_INVALID_API_ROOT) from exc
        except requests.ConnectionError as exc:
            raise VegaValidationException(MSG_INVALID_API_ROOT) from exc

    def _wait_rate_limit(self, source: str) -> int:
        wait = self.rate_limiter.on_429()
        self._log("warn", "Vega %s rate limit; waiting %s seconds.", source, wait)
        return wait

    def _request(
        self,
        method: str,
        path: str,
        allow_relogin: bool = True,
        apply_success: bool = True,
        **kwargs,
    ):
        server_attempts = 0
        while True:
            response = self._send(method, path, **kwargs)
            status = response.status_code
            if status == 429:
                self._wait_rate_limit("HTTP 429")
                continue
            if status >= 500:
                if path == LOGIN_PATH:
                    self._raise_http(response, path)
                server_attempts += 1
                if server_attempts <= SERVER_ERROR_RETRIES:
                    self._sleeper(SERVER_ERROR_WAIT_SECONDS)
                    continue
                self._raise_http(response, path)
            if status == 401 and allow_relogin and path != LOGIN_PATH:
                self._jwt = None
                self.login()
                headers = dict(kwargs.get("headers") or {})
                headers.update(self._auth_headers())
                kwargs["headers"] = headers
                allow_relogin = False
                continue
            if not (200 <= status < 300):
                self._raise_http(response, path)
            if apply_success:
                self.rate_limiter.on_success()
            return response

    def _auth_headers(self) -> SingleJson:
        if not self._jwt:
            self.login()
        return {
            "Content-Type": "application/json",
            "JWTSessionToken": self._jwt,
            "X-Vega-Key-Id": self.access_key_id,
        }

    def login(self) -> str:
        """Authenticate with Vega and return a bearer JWT."""
        response = self._request(
            "POST",
            LOGIN_PATH,
            allow_relogin=False,
            headers={
                "Content-Type": "application/json",
                "X-Vega-Key-Id": self.access_key_id,
            },
            json={"access_key": self.access_key},
        )
        try:
            payload = response.json()
        except Exception as exc:
            raise VegaValidationException(MSG_INVALID_API_ROOT) from exc
        token = payload.get("session_jwt") or payload.get("sessionJwt") or payload.get("token")
        if not token:
            raise VegaUnauthorizedException(MSG_INVALID_ACCESS_KEY)
        self._jwt = str(token)
        return self._jwt

    def graphql(self, query: str, variables: SingleJson | None = None) -> SingleJson:
        """Execute a GraphQL query/mutation and return the data object."""
        while True:
            response = self._request(
                "POST",
                QUERY_PATH,
                headers=self._auth_headers(),
                json={"query": query, "variables": variables or {}},
                apply_success=False,
            )
            try:
                payload = response.json()
            except Exception as parse_error:
                raise VegaException("Vega GraphQL returned a non-JSON body.") from parse_error
            if payload.get("errors"):
                message = payload["errors"][0].get("message") if payload["errors"] else ""
                classified = classify_credential_error(message)
                if classified:
                    raise VegaUnauthorizedException(classified)
                detail = str(message or "").strip() or "Vega request failed. Please try again."
                if is_rate_limit_message(detail):
                    self._wait_rate_limit("GraphQL")
                    continue
                self._log("error", "Vega GraphQL error: %s", detail)
                raise VegaException(detail)
            self.rate_limiter.on_success()
            return payload.get("data") or {}

    def test_connection(self) -> bool:
        """Validate API Root, Access Key, and Access Key ID before ingest."""
        try:
            self.get_alerts({"limit": 1, "offset": 0}, max_records=1)
        except VegaBadRequestException as exc:
            raise VegaUnauthorizedException(MSG_INVALID_ACCESS_KEY_ID) from exc
        return True

    def _count_records(
        self,
        query: str,
        envelope_key: str,
        records_key: str,
        variables: SingleJson,
    ) -> int:
        """Return GraphQL `total` without paging the full result set."""
        page_vars = dict(variables or {})
        page_vars["limit"] = 1
        page_vars["offset"] = 0
        while True:
            data = self.graphql(query, page_vars)
            envelope = data.get(envelope_key) or {}
            if not isinstance(envelope, dict):
                envelope = {}
            error = envelope.get("error") or envelope.get("errors") or {}
            message = None
            if isinstance(error, dict) and (error.get("code") or error.get("message")):
                message = error.get("message") or "Vega query failed."
            elif isinstance(error, list) and error:
                first = error[0]
                message = first.get("message") if isinstance(first, dict) else str(first)
            if message:
                if is_rate_limit_message(message):
                    self._wait_rate_limit("GraphQL")
                    continue
                classified = classify_credential_error(message)
                if classified:
                    raise VegaUnauthorizedException(classified)
                raise VegaException(str(message).strip() or "Vega query failed.")
            total = envelope.get("total")
            if total is not None:
                try:
                    return max(int(total), 0)
                except (TypeError, ValueError):
                    pass
            records = envelope.get(records_key) or []
            return len(records) if isinstance(records, list) else 0

    def count_alerts(self, variables: SingleJson) -> int:
        """Return the total alert count for the given GraphQL variables."""
        return self._count_records(GET_ALERTS_QUERY, "getAlerts", "alerts", variables)

    def count_incidents(self, variables: SingleJson) -> int:
        """Return the total incident count for the given GraphQL variables."""
        return self._count_records(GET_INCIDENTS_QUERY, "getIncidents", "incidents", variables)

    def _deadline_passed(self, deadline_monotonic: float | None) -> bool:
        if deadline_monotonic is None:
            return False
        return time.monotonic() >= float(deadline_monotonic)

    def _paged(
        self,
        query: str,
        envelope_key: str,
        records_key: str,
        variables: SingleJson,
        max_records: int | None = None,
        deadline_monotonic: float | None = None,
        start_offset: int = 0,
        page_size: int | None = None,
    ) -> list:
        collected: list = []
        offset = max(int(start_offset or 0), 0)
        truncated = False
        requested_page = GRAPHQL_PAGE_SIZE if page_size is None else max(int(page_size), 1)
        while True:
            if collected and self._deadline_passed(deadline_monotonic):
                truncated = True
                break
            if max_records is not None and len(collected) >= max_records:
                break
            page_limit = requested_page
            if max_records is not None:
                page_limit = min(requested_page, max_records - len(collected))
                if page_limit <= 0:
                    break
            page_vars = dict(variables)
            page_vars["limit"] = page_limit
            page_vars["offset"] = offset
            data = self.graphql(query, page_vars)
            envelope = data.get(envelope_key) or {}
            error = envelope.get("error") or envelope.get("errors") or {}
            if isinstance(error, dict) and (error.get("code") or error.get("message")):
                message = error.get("message") or "Vega query failed."
                if is_rate_limit_message(message):
                    self._wait_rate_limit("GraphQL")
                    continue
                classified = classify_credential_error(message)
                if classified:
                    raise VegaUnauthorizedException(classified)
                raise VegaException(message)
            if isinstance(error, list) and error:
                message = error[0].get("message") if isinstance(error[0], dict) else str(error[0])
                if is_rate_limit_message(message):
                    self._wait_rate_limit("GraphQL")
                    continue
                classified = classify_credential_error(message)
                if classified:
                    raise VegaUnauthorizedException(classified)
                raise VegaException(message or "Vega query failed.")
            records = envelope.get(records_key) or []
            if not records:
                break
            collected.extend(records)
            offset += len(records)
            total = envelope.get("total")
            if total is not None and offset >= int(total):
                break
            if len(records) < page_limit:
                break
            if self._deadline_passed(deadline_monotonic):
                truncated = True
                break
        if max_records is not None:
            collected = collected[:max_records]
        self.last_fetch_truncated = truncated
        return collected

    def get_alerts(
        self,
        variables: SingleJson,
        max_records: int | None = None,
        deadline_monotonic: float | None = None,
        start_offset: int = 0,
        page_size: int | None = None,
    ) -> list:
        """Page getAlerts. Pass alertIds to resolve incident-related alerts.

        start_offset resumes a previous scan instead of reading page 0 again.
        page_size is the GraphQL limit. Id lookups use up to 1000.
        """
        self.last_fetch_truncated = False
        return self._paged(
            GET_ALERTS_QUERY,
            "getAlerts",
            "alerts",
            variables,
            max_records,
            deadline_monotonic=deadline_monotonic,
            start_offset=start_offset,
            page_size=page_size,
        )

    def get_incidents(
        self,
        variables: SingleJson,
        max_records: int | None = None,
        deadline_monotonic: float | None = None,
    ) -> list:
        """Page getIncidents and return incident records up to max_records."""
        self.last_fetch_truncated = False
        return self._paged(
            GET_INCIDENTS_QUERY,
            "getIncidents",
            "incidents",
            variables,
            max_records,
            deadline_monotonic=deadline_monotonic,
        )

    def _dedupe_alert_ids(self, alert_ids: list) -> list[str]:
        unique: list[str] = []
        seen: set[str] = set()
        for item in alert_ids or []:
            alert_id = str(item or "").strip()
            if not alert_id or alert_id in seen:
                continue
            seen.add(alert_id)
            unique.append(alert_id)
        return unique

    def _buckets_from_alerts_events(self, envelope: SingleJson, requested: list[str]) -> dict[str, SingleJson]:
        """Map a getAlertsEvents payload onto the ids that were requested.

        Per-alert `alerts[]` buckets are the source of truth. Top-level
        `results` is used only for a single-id call that did not return
        `alerts`, so a batch response cannot smear every row onto every alert.
        """
        buckets = {alert_id: {"results": [], "total": None, "error": {}, "present": False} for alert_id in requested}
        raw_alerts = envelope.get("alerts") if isinstance(envelope, dict) else None
        if isinstance(raw_alerts, list) and raw_alerts:
            seen_ids: set[str] = set()
            for item in raw_alerts:
                if not isinstance(item, dict):
                    continue
                raw_id = str(item.get("alertId") or "").strip()
                alert_id = next(
                    (candidate for candidate in requested if _same_alert_id(candidate, raw_id)),
                    "",
                )
                if not alert_id:
                    self._log(
                        "warn",
                        "getAlertsEvents returned alertId=%s which was not in "
                        "this batch; those events were not attached to another alert.",
                        raw_id or "<missing>",
                    )
                    continue
                if alert_id in seen_ids:
                    self._log(
                        "warn",
                        "getAlertsEvents returned alertId=%s more than once; keeping the first bucket only.",
                        alert_id,
                    )
                    continue
                seen_ids.add(alert_id)
                error = item.get("error") if isinstance(item.get("error"), dict) else {}
                if error.get("code") or error.get("message"):
                    buckets[alert_id] = {
                        "results": [],
                        "total": item.get("total"),
                        "error": error,
                        "present": True,
                    }
                    continue
                raw_results = item.get("results")
                parsed, dropped = events_for_alert_bucket(raw_results, alert_id)
                if dropped:
                    self._log(
                        "warn",
                        "Dropped %s getAlertsEvents row(s) for alert %s because "
                        "they were tagged with a different alert id.",
                        dropped,
                        alert_id,
                    )
                if not parsed and raw_results not in (None, "", [], {}):
                    self._log(
                        "warn",
                        "getAlertsEvents returned results that did not parse to events (alertId=%s, type=%s).",
                        alert_id,
                        type(raw_results).__name__,
                    )
                buckets[alert_id] = {
                    "results": parsed,
                    "returned": len(parsed) + dropped,
                    "total": item.get("total"),
                    "error": {},
                    "present": True,
                }
            return buckets

        if len(requested) == 1:
            alert_id = requested[0]
            error = {}
            if isinstance(envelope, dict) and isinstance(envelope.get("error"), dict):
                error = envelope.get("error") or {}
            raw_results = envelope.get("results") if isinstance(envelope, dict) else None
            parsed: list[SingleJson] = []
            returned = 0
            if not (error.get("code") or error.get("message")):
                parsed, dropped = events_for_alert_bucket(raw_results, alert_id)
                returned = len(parsed) + dropped
                if dropped:
                    self._log(
                        "warn",
                        "Dropped %s getAlertsEvents row(s) for alert %s because "
                        "they were tagged with a different alert id.",
                        dropped,
                        alert_id,
                    )
                if not parsed and raw_results not in (None, "", [], {}):
                    self._log(
                        "warn",
                        "getAlertsEvents returned results that did not parse to events (alertId=%s, type=%s).",
                        alert_id,
                        type(raw_results).__name__,
                    )
            buckets[alert_id] = {
                "results": parsed,
                "returned": returned,
                "total": envelope.get("total") if isinstance(envelope, dict) else None,
                "error": error,
                "present": True,
            }
            return buckets

        top_error = {}
        if isinstance(envelope, dict) and isinstance(envelope.get("error"), dict):
            top_error = envelope.get("error") or {}
        if top_error.get("code") or top_error.get("message"):
            for alert_id in requested:
                buckets[alert_id] = {
                    "results": [],
                    "total": None,
                    "error": top_error,
                    "present": True,
                }
            return buckets
        self._log(
            "warn",
            "getAlertsEvents batch of %s alert id(s) did not include per-alert results; no events were assigned.",
            len(requested),
        )
        return buckets

    def _fetch_alerts_events_page(self, alert_ids: list[str], limit: int, offset: int) -> dict[str, SingleJson]:
        """One getAlertsEvents call. UUID ids go in alertIds (max 10)."""
        ids = self._dedupe_alert_ids(alert_ids)[: max(1, int(ALERT_EVENTS_ID_BATCH))]
        if not ids:
            return {}
        variables: SingleJson = {
            "limit": int(limit),
            "offset": int(offset),
        }
        if all(_graphql_alert_id(alert_id) for alert_id in ids):
            variables["alertIds"] = ids
        elif len(ids) == 1:
            variables["alertId"] = ids[0]
        else:
            raise VegaValidationException(
                f"getAlertsEvents alertIds accepts at most {ALERT_EVENTS_ID_BATCH} UUID alert ids."
            )
        data = self.graphql(GET_ALERT_EVENTS_QUERY, variables)
        envelope = data.get("getAlertsEvents") or {}
        if not isinstance(envelope, dict):
            envelope = {}
        return self._buckets_from_alerts_events(envelope, ids)

    def _page_has_rate_limit(self, buckets: dict[str, SingleJson], alert_ids: list[str]) -> bool:
        for alert_id in alert_ids:
            error = (buckets.get(alert_id) or {}).get("error") or {}
            if not isinstance(error, dict):
                continue
            message = error.get("message") or error.get("code")
            if is_rate_limit_message(message):
                return True
        return False

    def get_alert_events(self, alert_id: str, limit: int = ALERT_EVENTS_PAGE_SIZE, offset: int = 0) -> SingleJson:
        """Return one page of getAlertsEvents for a single alert id."""
        alert_id = str(alert_id or "").strip()
        if not alert_id:
            return {}
        buckets = self._fetch_alerts_events_page([alert_id], limit, offset)
        bucket = buckets.get(alert_id) or {}
        return {
            "total": bucket.get("total"),
            "limit": limit,
            "offset": offset,
            "results": list(bucket.get("results") or []),
            "error": bucket.get("error") or {},
        }

    def _collect_paged(
        self,
        fetch_page,
        records_key: str,
        page_size: int,
        max_records: int,
        label: str,
        deadline_monotonic: float | None = None,
    ) -> list:
        collected: list = []
        offset = 0
        total: int | None = None
        self.last_fetch_truncated = False
        while len(collected) < max_records:
            if collected and self._deadline_passed(deadline_monotonic):
                self.last_fetch_truncated = True
                break
            request_size = min(max(int(page_size or 1), 1), max_records - len(collected))
            try:
                envelope = fetch_page(request_size, offset)
            except Exception:
                if collected:
                    break
                raise
            if not isinstance(envelope, dict):
                envelope = {}
            error = envelope.get("error") or {}
            if isinstance(error, dict) and (error.get("code") or error.get("message")):
                message = error.get("message") or error.get("code")
                if is_rate_limit_message(message):
                    self._wait_rate_limit("GraphQL")
                    continue
                if collected:
                    self._log(
                        "warn",
                        "Stopped paging Vega %s after %s row(s): %s",
                        label,
                        len(collected),
                        error.get("message") or error.get("code"),
                    )
                    break
                raise VegaException(error.get("message") or f"{label} fetch failed.")
            records = envelope.get(records_key) or []
            if isinstance(records, dict):
                records = [records]
            if not isinstance(records, list) or not records:
                break
            collected.extend(records)
            offset += len(records)
            page_total = envelope.get("total")
            if page_total is not None:
                try:
                    parsed_total = int(page_total)
                    if parsed_total > 0:
                        total = parsed_total
                except (TypeError, ValueError):
                    pass
            if total is not None and offset >= total:
                break
            if self._deadline_passed(deadline_monotonic):
                self.last_fetch_truncated = True
                break
        return collected[:max_records]

    def get_all_alerts_events(
        self,
        alert_ids: list[str],
        page_size: int = ALERT_EVENTS_PAGE_SIZE,
        max_records: int = MAX_EVENTS_PER_ALERT,
        deadline_monotonic: float | None = None,
    ) -> dict[str, list[SingleJson]]:
        """Page getAlertsEvents for many alerts.

        UUID ids are sent in `alertIds` batches of at most 10. Each alert
        receives only the `alerts[]` bucket for its own id. Non-UUID ids are
        fetched one at a time with `alertId` so a human id cannot fail the batch.
        """
        from .mapping import normalize_alert_event

        requested = self._dedupe_alert_ids(alert_ids)
        collected: dict[str, list] = {alert_id: [] for alert_id in requested}
        if not requested:
            return {}
        page_size = max(int(page_size or 1), 1)
        try:
            record_cap = max(int(max_records), 0)
        except (TypeError, ValueError):
            record_cap = MAX_EVENTS_PER_ALERT
        if record_cap == 0:
            return collected

        batch_size = max(1, int(ALERT_EVENTS_ID_BATCH))
        self.last_fetch_truncated = False
        graphql_ids = [alert_id for alert_id in requested if _graphql_alert_id(alert_id)]
        other_ids = [alert_id for alert_id in requested if alert_id not in graphql_ids]
        groups = [graphql_ids[index : index + batch_size] for index in range(0, len(graphql_ids), batch_size)]
        groups.extend([alert_id] for alert_id in other_ids)

        for group in groups:
            if not group:
                continue
            if self.last_fetch_truncated and self._deadline_passed(deadline_monotonic):
                break
            offsets = {alert_id: 0 for alert_id in group}
            finished: set[str] = set()
            while len(finished) < len(group):
                active = [alert_id for alert_id in group if alert_id not in finished]
                if any(collected[alert_id] for alert_id in active) and self._deadline_passed(deadline_monotonic):
                    self.last_fetch_truncated = True
                    break
                offset = min(offsets[alert_id] for alert_id in active)
                page_ids = [alert_id for alert_id in active if offsets[alert_id] == offset][:batch_size]
                remaining = max(record_cap - len(collected[alert_id]) for alert_id in page_ids)
                if remaining <= 0:
                    finished.update(page_ids)
                    continue
                request_size = min(page_size, remaining)
                try:
                    buckets = self._fetch_alerts_events_page(page_ids, request_size, offset)
                except Exception:
                    if any(collected[alert_id] for alert_id in page_ids):
                        self.last_fetch_truncated = True
                        self._log(
                            "warn",
                            "Stopped paging Vega alert events after a partial batch of %s alert(s).",
                            len(page_ids),
                        )
                        finished.update(page_ids)
                        continue
                    raise
                if self._page_has_rate_limit(buckets, page_ids):
                    self._wait_rate_limit("GraphQL")
                    continue
                for alert_id in page_ids:
                    bucket = buckets.get(alert_id) or {}
                    error = bucket.get("error") if isinstance(bucket.get("error"), dict) else {}
                    message = str(error.get("message") or error.get("code") or "")
                    if message:
                        if collected[alert_id]:
                            self._log(
                                "warn",
                                "Stopped paging Vega alert events for %s after %s row(s): %s",
                                alert_id,
                                len(collected[alert_id]),
                                message,
                            )
                        else:
                            self._log(
                                "warn",
                                "getAlertsEvents failed for alert %s: %s",
                                alert_id,
                                message,
                            )
                        finished.add(alert_id)
                        continue
                    records = bucket.get("results") or []
                    if not isinstance(records, list) or not records:
                        finished.add(alert_id)
                        continue
                    returned = _optional_int(bucket.get("returned"))
                    if returned is None:
                        returned = len(records)
                    room = record_cap - len(collected[alert_id])
                    collected[alert_id].extend(records[:room])
                    offsets[alert_id] += returned
                    total = _optional_int(bucket.get("total"))
                    if len(collected[alert_id]) >= record_cap:
                        finished.add(alert_id)
                    elif total is not None and offsets[alert_id] >= total:
                        finished.add(alert_id)
                    elif returned < request_size:
                        finished.add(alert_id)

        return {alert_id: [normalize_alert_event(item) for item in collected[alert_id]] for alert_id in requested}

    def get_all_alert_events(
        self,
        alert_id: str,
        page_size: int = ALERT_EVENTS_PAGE_SIZE,
        max_records: int = MAX_EVENTS_PER_ALERT,
        deadline_monotonic: float | None = None,
    ) -> list[SingleJson]:
        """Fetch every event page for one alert id."""
        alert_id = str(alert_id or "").strip()
        if not alert_id:
            return []
        fetched = self.get_all_alerts_events(
            [alert_id],
            page_size=page_size,
            max_records=max_records,
            deadline_monotonic=deadline_monotonic,
        )
        return list(fetched.get(alert_id) or [])

    def get_incident_timeline(
        self,
        incident_id: str,
        limit: int = TIMELINE_PAGE_SIZE,
        offset: int = 0,
    ) -> SingleJson:
        """Return one page of getIncidentTimeline for an incident id."""
        data = self.graphql(
            GET_INCIDENT_TIMELINE_QUERY,
            {"incidentId": incident_id, "limit": limit, "offset": offset},
        )
        envelope = data.get("getIncidentTimeline") or {}
        if not isinstance(envelope, dict):
            return {}
        envelope = dict(envelope)
        events = envelope.get("events") or []
        if isinstance(events, dict):
            events = [events]
        if not isinstance(events, list):
            events = []
        envelope["events"] = [item for item in events if isinstance(item, dict)]
        return envelope

    def get_all_incident_timeline(
        self,
        incident_id: str,
        page_size: int = TIMELINE_PAGE_SIZE,
        deadline_monotonic: float | None = None,
    ) -> list:
        """Fetch every timeline page for one incident id."""
        return self._collect_paged(
            lambda limit, offset: self.get_incident_timeline(incident_id, limit, offset),
            "events",
            page_size,
            TIMELINE_MAX_FETCH,
            f"incident timeline for {incident_id}",
            deadline_monotonic=deadline_monotonic,
        )

    def get_incident(self, incident_id: str) -> SingleJson:
        """Fetch one incident by GraphQL UUID or human Vega incident id."""
        from .mapping import is_graphql_alert_id

        lookup = str(incident_id).strip()
        if is_graphql_alert_id(lookup):
            variables = {"incidentIds": [lookup]}
        else:
            variables = {"vegaIncidentIds": [lookup]}
        records = self.get_incidents(variables, max_records=1)
        return records[0] if records else {}

    def update_alerts(self, payload: SingleJson) -> SingleJson:
        """Apply an updateAlerts mutation and return the response envelope."""
        data = self.graphql(UPDATE_ALERTS_MUTATION, {"input": payload})
        envelope = data.get("updateAlerts") or {}
        error = envelope.get("error") or {}
        if error.get("code") or error.get("message"):
            raise VegaException(error.get("message") or "updateAlerts failed.")
        return envelope

    def update_incidents(self, payload: SingleJson) -> SingleJson:
        """Apply an updateIncidents mutation and return the response envelope."""
        data = self.graphql(UPDATE_INCIDENTS_MUTATION, {"input": payload})
        envelope = data.get("updateIncidents") or {}
        errors = envelope.get("errors") or []
        if errors:
            message = errors[0].get("message") if isinstance(errors[0], dict) else str(errors[0])
            raise VegaException(message or "updateIncidents failed.")
        return envelope

    def resolve_alerts(self, alert_ids: list[str]) -> SingleJson:
        """Set Vega alert status to resolved for the given alert ids."""
        payload = {"alertIds": list(alert_ids), "status": SYNC_RESOLVED_STATUS}
        data = self.graphql(UPDATE_ALERTS_STATUS_MUTATION, {"input": payload})
        envelope = data.get("updateAlerts") or {}
        error = envelope.get("error") or {}
        if error.get("code") or error.get("message"):
            raise VegaException(error.get("message") or "updateAlerts failed.")
        return envelope

    def resolve_incidents(self, incident_ids: list[str]) -> SingleJson:
        """Set Vega incident userStatus to resolved for the given incident ids."""
        from .constants import ENTITY_TYPE_INCIDENT
        from .mapping import is_graphql_alert_id, record_id

        graphql_ids: list[str] = []
        seen: set[str] = set()
        for raw in incident_ids:
            lookup = str(raw or "").strip()
            if not lookup:
                continue
            if is_graphql_alert_id(lookup):
                resolved = lookup
            else:
                record = self.get_incident(lookup)
                resolved = record_id(record, ENTITY_TYPE_INCIDENT) if record else ""
                if not resolved:
                    resolved = lookup
            if resolved in seen:
                continue
            seen.add(resolved)
            graphql_ids.append(resolved)
        if not graphql_ids:
            raise VegaException("No Vega incident ids to resolve.")
        payload = {"incidentIds": graphql_ids, "userStatus": SYNC_RESOLVED_STATUS}
        data = self.graphql(UPDATE_INCIDENTS_STATUS_MUTATION, {"input": payload})
        envelope = data.get("updateIncidents") or {}
        errors = envelope.get("errors") or []
        if errors:
            message = errors[0].get("message") if isinstance(errors[0], dict) else str(errors[0])
            raise VegaException(message or "updateIncidents failed.")
        return envelope
