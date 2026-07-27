"""
CybleManager — core API client for the Cyble Vision integration.

Handles:
  - Authentication (Bearer token)
  - Exponential backoff with jitter for rate limits and transient errors
  - Paginated alert fetching (skip/take)
  - Time-window iteration (updated_at gte/lte)
  - Batch update (PUT /alerts, up to 100 per request)
  - Structured exceptions for clean action/job error handling
"""
from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from time import sleep
from typing import Generator, List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .constants import (
    DEFAULT_FETCH_STATUSES,
    DEFAULT_PAGE_SIZE,
    DEFAULT_TIMEOUT,
    ENDPOINT_ALERTS,
    ENDPOINT_SERVICES,
    ENDPOINT_UPDATE,
    MAX_RETRIES,
    PING_TIMEOUT,
    RETRY_BACKOFF_BASE,
    RETRY_STATUS_CODES,
)

logger = logging.getLogger("CybleManager")


# ── Custom Exceptions ─────────────────────────────────────────────────────────

class CybleAPIError(Exception):
    """Base exception for all Cyble API errors."""
    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class CybleAuthError(CybleAPIError):
    """Raised on 401/403 — bad or expired API key."""


class CybleRateLimitError(CybleAPIError):
    """Raised when retry budget exhausted on 429."""


class CybleNotFoundError(CybleAPIError):
    """Raised on 404 — alert ID not found during update."""


class CybleValidationError(CybleAPIError):
    """Raised on 400/422 — bad request payload."""


class CybleServerError(CybleAPIError):
    """Raised on 5xx after all retries exhausted."""


# ── Manager ───────────────────────────────────────────────────────────────────

class CybleManager:
    """
    Thread-safe API client for Cyble Vision TPI endpoints.

    Usage:
        manager = CybleManager(api_key="...", base_url="https://bifrost.cyble.ai/...")
        services = manager.get_services()
        for batch in manager.iter_alerts(services=["github"], gte=..., lte=...):
            process(batch)
        manager.update_alerts([{"id": "...", "status": "RESOLVED", "service": "github"}])
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        verify_ssl: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
        page_size: int = DEFAULT_PAGE_SIZE,
        sleep_func: callable = sleep,
    ):
        if not api_key or not api_key.strip():
            raise CybleAuthError("API key must not be empty.")
        if not base_url or not base_url.strip():
            raise CybleAPIError("Base URL must not be empty.")

        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.page_size = page_size
        self.sleep_func = sleep_func

        self._session = self._build_session()

    # ── Session setup ─────────────────────────────────────────────────────────

    def _build_session(self) -> requests.Session:
        """
        Build a requests Session with connection pooling.
        Transport-level retries are intentionally disabled here — we handle
        retries ourselves so we can log, jitter, and distinguish error types.
        """
        session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=5,
            pool_maxsize=10,
            max_retries=Retry(total=0),  # no transport retries — we own retry logic
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        })
        return session

    # ── Request primitives ────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        endpoint: str,
        payload: dict = None,
        timeout_override: int = None,
    ) -> dict:
        """
        Execute an HTTP request with exponential backoff + jitter.

        Retries on:
          - 429 Too Many Requests
          - 500, 502, 503, 504 (transient server errors)
          - requests.ConnectionError / Timeout

        Does NOT retry on:
          - 400, 401, 403, 404, 422 (client errors — retrying won't help)
        """
        url = f"{self.base_url}{endpoint}"
        timeout = timeout_override or self.timeout
        last_exc = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._session.request(
                    method=method.upper(),
                    url=url,
                    json=payload,
                    verify=self.verify_ssl,
                    timeout=timeout,
                )
            except requests.Timeout as exc:
                last_exc = exc
                logger.warning(
                    "Cyble API timeout (attempt %d/%d): %s %s",
                    attempt, MAX_RETRIES, method, endpoint,
                )
                self._backoff(attempt, self.sleep_func)
                continue
            except requests.ConnectionError as exc:
                last_exc = exc
                logger.warning(
                    "Cyble API connection error (attempt %d/%d): %s",
                    attempt, MAX_RETRIES, exc,
                )
                self._backoff(attempt, self.sleep_func)
                continue

            if response.status_code == 200:
                try:
                    body = response.json()
                except ValueError:
                    raise CybleAPIError(
                        f"Non-JSON response from {endpoint}",
                        status_code=response.status_code,
                        response_body=response.text[:500],
                    )
                # Cyble wraps all responses in {"success": bool, "data": ...}
                if not body.get("success", True):
                    raise CybleAPIError(
                        f"Cyble API returned success=false: {body}",
                        status_code=200,
                    )
                return body

            # ── Client errors (no retry) ──────────────────────────────────────
            if response.status_code in (401, 403):
                raise CybleAuthError(
                    f"Authentication failed ({response.status_code}). "
                    "Check your API key in the connector configuration.",
                    status_code=response.status_code,
                    response_body=response.text[:500],
                )
            if response.status_code == 404:
                raise CybleNotFoundError(
                    f"Resource not found: {endpoint}",
                    status_code=404,
                    response_body=response.text[:500],
                )
            if response.status_code in (400, 422):
                raise CybleValidationError(
                    f"Bad request to {endpoint}: {response.text[:500]}",
                    status_code=response.status_code,
                    response_body=response.text[:500],
                )

            # ── Retryable server errors ───────────────────────────────────────
            if response.status_code in RETRY_STATUS_CODES:
                logger.warning(
                    "Cyble API %d (attempt %d/%d): %s",
                    response.status_code, attempt, MAX_RETRIES, endpoint,
                )
                # Honour Retry-After header if present (e.g., on 429)
                retry_after = int(response.headers.get("Retry-After", 0))
                if retry_after:
                    logger.info("Retry-After header: sleeping %ds", retry_after)
                    self.sleep_func(retry_after)
                else:
                    self._backoff(attempt, self.sleep_func)

                if attempt == MAX_RETRIES:
                    exc_cls = CybleRateLimitError if response.status_code == 429 else CybleServerError
                    raise exc_cls(
                        f"Cyble API {response.status_code} after {MAX_RETRIES} retries: {endpoint}",
                        status_code=response.status_code,
                    )
                continue

            # ── Unexpected status ─────────────────────────────────────────────
            raise CybleAPIError(
                f"Unexpected status {response.status_code} from {endpoint}",
                status_code=response.status_code,
                response_body=response.text[:500],
            )

        # Exhausted retries on connection/timeout errors
        raise CybleServerError(
            f"Cyble API unreachable after {MAX_RETRIES} attempts: {last_exc}"
        ) from last_exc

    @staticmethod
    def _backoff(attempt: int, sleep_func: callable = sleep) -> None:
        """Exponential backoff with ±30% jitter."""
        base = RETRY_BACKOFF_BASE ** attempt
        sleep_time = base * random.uniform(0.7, 1.3)
        logger.debug("Backoff: sleeping %.2fs (attempt %d)", sleep_time, attempt)
        sleep_func(sleep_time)

    # ── Public API methods ────────────────────────────────────────────────────

    def ping(self) -> bool:
        """
        Test connectivity and credential validity.
        Returns True on success; raises CybleAuthError / CybleAPIError on failure.
        """
        self._request("GET", ENDPOINT_SERVICES, timeout_override=PING_TIMEOUT)
        return True

    def get_services(self) -> List[dict]:
        """
        Fetch the list of services from Cyble.
        Returns a list of service dicts: [{"name": "github", "displayName": "...", "allowAlerts": True}, ...]

        Edge cases handled:
          - Empty list → returns [] (caller decides whether to warn/skip)
          - allowAlerts=False services → filtered out
        """
        body = self._request("GET", ENDPOINT_SERVICES)
        services = body.get("data", [])

        if not services:
            logger.warning("Cyble returned an empty services list.")
            return []

        # Only include services that actually support alerts
        active = [s for s in services if s.get("allowAlerts", False)]
        logger.info("Fetched %d services (%d allow alerts).", len(services), len(active))
        return active

    def iter_alerts(
        self,
        services: List[str],
        gte: datetime,
        lte: datetime,
        statuses: List[str] = None,
        max_total: int = None,
    ) -> Generator[List[dict], None, None]:
        """
        Generator that yields batches of alerts for the given services and time window.

        Pagination: uses skip/take.
        Stops when:
          - `data` is empty (no more pages)
          - `max_total` alerts have been yielded for this call
          - A page returns fewer records than `page_size` (last page)

        Args:
            services:  List of Cyble service names to query.
            gte:       Start of time window (timezone-aware datetime).
            lte:       End of time window (timezone-aware datetime).
            statuses:  Alert statuses to include (defaults to DEFAULT_FETCH_STATUSES).
            max_total: Hard cap on total alerts yielded (safety valve).

        Yields:
            List[dict] — one page of raw Cyble alert records.
        """
        if not services:
            logger.warning("iter_alerts called with empty services list — skipping.")
            return

        if statuses is None:
            statuses = DEFAULT_FETCH_STATUSES

        gte_str = gte.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        lte_str = lte.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

        skip = 0
        yielded = 0

        while True:
            if max_total and yielded >= max_total:
                logger.info("Reached max_total=%d for this fetch window.", max_total)
                break

            remaining = (max_total - yielded) if max_total else self.page_size
            take = min(self.page_size, remaining)

            payload = {
                "filters": {
                    "service":    services,
                    "created_at": {"gte": gte_str, "lte": lte_str},
                    "status":     statuses,
                },
                # ASC ordering is intentional and critical for cursor correctness.
                # When max_total truncates a high-volume window, the tail we lose
                # is the NEWEST slice; the next cycle picks it up naturally because
                # the cursor advances to the max(created_at) we successfully
                # processed. With DESC ordering, the lost slice would be the
                # oldest alerts in the window, which would be permanently skipped.
                "orderBy":       [{"created_at": "asc"}],
                "skip":          skip,
                "take":          take,
                "countOnly": False,
                "taggedAlert": False,
                "withDataMessage": True,
            }

            body = self._request("POST", ENDPOINT_ALERTS, payload=payload)
            batch = body.get("data", [])

            if not batch:
                logger.debug("Empty page at skip=%d — pagination complete.", skip)
                break

            # Defensively cap batch to remaining quota.
            # The API could return more items than `take` requested, so we
            # never exceed max_total regardless of what the server sends back.
            if max_total:
                remaining_quota = max_total - yielded
                if len(batch) > remaining_quota:
                    batch = batch[:remaining_quota]

            actual = len(batch)
            is_partial = actual < take  # true when this is the last real page

            yield batch
            yielded += actual
            skip += actual

            if is_partial:
                logger.debug(
                    "Partial page (%d < %d) at skip=%d — pagination complete.",
                    actual, take, skip,
                )
                break

            if max_total and yielded >= max_total:
                logger.info("Reached max_total=%d for this fetch window.", max_total)
                break

    def get_alert_count(
        self,
        services: List[str],
        gte: datetime,
        lte: datetime,
        statuses: List[str] = None,
    ) -> int:
        """
        Return the total alert count for a time window without fetching records.
        Useful for deciding whether to split the window into smaller chunks.
        """
        if statuses is None:
            statuses = DEFAULT_FETCH_STATUSES

        gte_str = gte.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        lte_str = lte.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

        payload = {
            "filters": {
                "service":    services,
                "created_at": {"gte": gte_str, "lte": lte_str},
                "status":     statuses,
            },
            "orderBy":       [{"created_at": "asc"}],
            "skip":          0,
            "take":          1,
            "countOnly": True,
            "taggedAlert": False,
            "withDataMessage": True,
        }
        body = self._request("POST", ENDPOINT_ALERTS, payload=payload)
        # countOnly returns {"success": true, "data": {"count": N}} or similar
        data = body.get("data", {})
        if isinstance(data, dict):
            return data.get("count", 0)
        return 0

    def update_alerts(self, updates: List[dict]) -> dict:
        """
        Update status and/or user_severity for one or more alerts.

        Args:
            updates: List of dicts, each containing:
                - id (required): Cyble alert UUID
                - service (required): service name, e.g. "github"
                - status (optional): new status string
                - user_severity (optional): new severity string

        Returns:
            Raw API response body.

        Each dict must have at minimum `id` and `service`.
        Batches >100 are split automatically (API limit guard).

        Raises:
            CybleValidationError: if an update dict is missing required fields.
            CybleNotFoundError:   if an alert ID does not exist.
        """
        if not updates:
            return {"success": True, "data": []}

        # Validate before hitting the API
        validated = []
        for i, upd in enumerate(updates):
            if not upd.get("id"):
                raise CybleValidationError(f"Update item {i} missing required field 'id'.")
            if not upd.get("service"):
                raise CybleValidationError(f"Update item {i} missing required field 'service'.")
            # Build minimal payload — omit fields not present (don't send null status)
            entry = {"id": upd["id"], "service": upd["service"]}
            if "status" in upd and upd["status"]:
                entry["status"] = upd["status"]
            if "user_severity" in upd and upd["user_severity"]:
                entry["user_severity"] = upd["user_severity"]
            validated.append(entry)

        # Split into batches of 100 (safe API limit)
        BATCH_SIZE = 100
        results = []
        for batch_start in range(0, len(validated), BATCH_SIZE):
            batch = validated[batch_start: batch_start + BATCH_SIZE]
            payload = {"alerts": batch}
            result = self._request("PUT", ENDPOINT_UPDATE, payload=payload)
            results.append(result)
            logger.info("Updated %d alerts (batch starting at %d).", len(batch), batch_start)

        return results[0] if len(results) == 1 else {"success": True, "batches": results}
