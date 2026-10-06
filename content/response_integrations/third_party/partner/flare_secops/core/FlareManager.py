"""
Flare API manager for the Flare - Google SecOps integration.

Uses the official flareio SDK (FlareApiClient) which handles JWT generation
and auto-refresh. Adds session-level retries for 429/5xx and explicit 401
token refresh + retry for mutating calls.
"""
from __future__ import annotations

import logging
import urllib.parse
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from flareio import FlareApiClient

from .constants import (
    DEFAULT_FLARE_API_URL,
    ENDPOINT_EVENT_ACTIONS,
    ENDPOINT_EVENTS_DETAIL,
    ENDPOINT_EVENTS_SEARCH,
    ENDPOINT_FILTER_SEVERITIES,
    ENDPOINT_FILTER_TYPES,
    ENDPOINT_TENANTS,
    FORBIDDEN,
    MAX_FLARE_PAGE_SIZE,
    SEVERITY_OPTIONS,
    TYPE_DISPLAY_NAME,
    UNAUTHORIZED,
)
from .exceptions import (
    FlareBadRequestException,
    FlareException,
    FlareForbiddenException,
    FlareNotFoundException,
    FlareRateLimitException,
    FlareUnauthorizedException,
    FlareValidationException,
)
from .utils import (
    cap_page_size,
    extract_filter_options,
    format_user_facing_error,
    safe_log,
)

logger = logging.getLogger(__name__)


def _build_session(ssl_verify: bool = True) -> requests.Session:
    session = requests.Session()
    session.verify = ssl_verify
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 502, 503, 504],
        allowed_methods={"GET", "POST"},
    )
    if hasattr(retry, "backoff_max"):
        retry.backoff_max = 60  # type: ignore[attr-defined]
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


class FlareManager:
    """Client for Flare Firework APIs (search, enrich, remediate)."""

    def __init__(
        self,
        api_key: str,
        tenant_id: int,
        api_url: str = DEFAULT_FLARE_API_URL,
        logger_instance=None,
    ) -> None:
        if not api_key:
            raise FlareException("Flare API Key is required.")
        self.api_key = api_key
        self.tenant_id = int(tenant_id or 0)
        self.api_url = (api_url or DEFAULT_FLARE_API_URL).rstrip("/")
        self.logger = logger_instance or logger
        self._session = _build_session(ssl_verify=True)
        self.client = FlareApiClient(api_key=self.api_key, session=self._session)

    def _log(self, level: str, msg: str, *args) -> None:
        safe_log(self.logger, level, msg, *args)

    def _raise_for_status(self, response, context: str = "Flare API request") -> None:
        status = response.status_code
        if 200 <= status < 300:
            return
        try:
            detail = response.json()
        except Exception:
            detail = (response.text or "")[:200]

        # Keep raw detail in logs; raise short, operator-facing messages.
        self._log(
            "error",
            "%s failed (HTTP %s): %s",
            context,
            status,
            detail,
        )
        if status == 400:
            raise FlareBadRequestException(
                "Invalid request to Flare. Check the connector filters and try again."
            )
        if status == UNAUTHORIZED:
            raise FlareUnauthorizedException(
                "Invalid API Key. Please check your credentials and try again."
            )
        if status == FORBIDDEN:
            raise FlareForbiddenException(
                "Access denied for this Flare Tenant ID. "
                "Verify the tenant ID and API key permissions."
            )
        if status == 404:
            raise FlareNotFoundException(
                "Requested Flare resource was not found. Verify the tenant ID and filters."
            )
        if status == 429:
            raise FlareRateLimitException(
                "Flare rate limit reached. Wait a moment and try again."
            )
        if status >= 500:
            raise FlareException(
                "Flare service is temporarily unavailable. Please try again later."
            )
        raise FlareException(
            format_user_facing_error(
                FlareException(f"{context} failed (HTTP {status})")
            )
        )

    def _refresh_token(self) -> None:
        self._log("info", "Refreshing Flare JWT token after auth failure.")
        self.client.generate_token()

    def _request_with_auth_retry(self, method: str, path: str, **kwargs):
        """Execute SDK request; on 401/403 refresh token and retry once."""
        fn = getattr(self.client, method.lower())
        resp = fn(path, **kwargs)
        if resp.status_code in (UNAUTHORIZED, FORBIDDEN):
            self._log(
                "warning",
                "Flare returned HTTP %s. Refreshing token and retrying once.",
                resp.status_code,
            )
            try:
                self._refresh_token()
            except Exception as exc:
                self._log("error", "Flare token refresh failed: %s", exc)
                raise FlareUnauthorizedException(
                    "Invalid API Key. Please check your credentials and try again."
                ) from exc
            resp = fn(path, **kwargs)
        return resp

    # ── Discovery ─────────────────────────────────────────────────────

    def fetch_available_severities(self) -> list:
        try:
            resp = self._request_with_auth_retry("get", ENDPOINT_FILTER_SEVERITIES)
            self._raise_for_status(resp, "Fetch severities")
            return resp.json()
        except Exception as exc:
            self._log("warning", "Could not fetch severity filters: %s", exc)
            return []

    def fetch_available_source_types(self) -> list:
        try:
            resp = self._request_with_auth_retry("get", ENDPOINT_FILTER_TYPES)
            self._raise_for_status(resp, "Fetch source types")
            return resp.json()
        except Exception as exc:
            self._log("warning", "Could not fetch source type filters: %s", exc)
            return []

    def list_severity_options(self) -> list:
        """Return [{key, labels}] for severities; falls back to built-in defaults."""
        options = extract_filter_options(self.fetch_available_severities())
        if options:
            self._log(
                "info",
                "Loaded %d severity option(s) from Flare: %s",
                len(options),
                ", ".join(opt["key"] for opt in options),
            )
            return options

        fallback = [{"key": value, "labels": {value}} for value in SEVERITY_OPTIONS]
        self._log(
            "warning",
            "Severity catalog unavailable from Flare — using defaults: %s",
            ", ".join(SEVERITY_OPTIONS),
        )
        return fallback

    def list_source_type_options(self) -> list:
        """Return [{key, labels}] for source types (includes display-name aliases)."""
        options = extract_filter_options(
            self.fetch_available_source_types(),
            extra_label_map=TYPE_DISPLAY_NAME,
        )
        if options:
            self._log(
                "info",
                "Loaded %d source-type option(s) from Flare.",
                len(options),
            )
            return options

        fallback = [
            {"key": key, "labels": {key, display}}
            for key, display in TYPE_DISPLAY_NAME.items()
        ]
        self._log(
            "warning",
            "Source-type catalog unavailable from Flare — using built-in type map "
            "(%d types).",
            len(fallback),
        )
        return fallback

    def fetch_tenants(self) -> list:
        """Tenants this API key can access. Raises on auth/API failure."""
        resp = self._request_with_auth_retry("get", ENDPOINT_TENANTS)
        self._raise_for_status(resp, "Fetch tenants")
        data = resp.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for field in ("tenants", "items", "data", "results"):
                candidate = data.get(field)
                if isinstance(candidate, list):
                    return candidate
            return [data]
        return []

    def validate_tenant(self) -> dict:
        """
        Confirm the configured Tenant ID exists for this API key.

        Flare API keys can reach several tenants, so a syntactically valid ID
        is not enough — it must be one of the accessible tenants.
        """
        tenants = self.fetch_tenants()

        available: list = []
        for tenant in tenants:
            if isinstance(tenant, dict):
                raw_id = tenant.get("id", tenant.get("tenant_id"))
                name = tenant.get("name") or tenant.get("display_name") or ""
            else:
                raw_id, name = tenant, ""
            try:
                tenant_id = int(str(raw_id).strip())
            except (TypeError, ValueError):
                continue
            available.append({"id": tenant_id, "name": str(name)})

        if not available:
            raise FlareValidationException(
                "No Flare tenants are accessible with this API key. "
                "Check the API key permissions in Flare."
            )

        for tenant in available:
            if tenant["id"] == self.tenant_id:
                self._log(
                    "info",
                    "Validated Flare Tenant ID %s (%s).",
                    tenant["id"],
                    tenant["name"] or "unnamed",
                )
                return tenant

        allowed = ", ".join(
            f"{t['id']}" + (f" ({t['name']})" if t["name"] else "") for t in available
        )
        raise FlareValidationException(
            f"Flare Tenant ID {self.tenant_id} is not available for this API key. "
            f"Available tenant ID(s): {allowed}."
        )

    # ── Events ────────────────────────────────────────────────────────

    def fetch_events_page(
        self,
        from_token: Optional[str] = None,
        size: int = 10,
        severities: Optional[list] = None,
        source_types: Optional[list] = None,
        start_date: Optional[str] = None,
        start_date_op: str = "gte",
    ) -> dict:
        page_size = cap_page_size(size, MAX_FLARE_PAGE_SIZE)
        search_body: dict = {"size": page_size, "order": "asc"}
        if from_token:
            search_body["from"] = from_token

        filters: dict = {}
        if start_date:
            filters["estimated_created_at"] = {start_date_op: start_date}
        if severities:
            filters["severity"] = severities
        if source_types:
            filters["type"] = source_types
        if filters:
            search_body["filters"] = filters

        self._log(
            "info",
            "Requesting Flare page (tenant=%s, size=%d, %s=%s, cursor=%s).",
            self.tenant_id,
            page_size,
            f"estimated_created_at.{start_date_op}" if start_date else "no_date_filter",
            start_date or "-",
            (from_token[:20] + "...") if from_token and len(from_token) > 20 else from_token,
        )

        resp = self._request_with_auth_retry(
            "post", ENDPOINT_EVENTS_SEARCH, json=search_body
        )
        self._raise_for_status(resp, "Event search")
        return resp.json()

    def enrich_event(self, event: dict) -> dict:
        """Merge full event detail onto the search-result event."""
        uid = (event.get("metadata") or {}).get("uid")
        if not uid:
            return event

        encoded_uid = urllib.parse.quote(uid, safe="")
        try:
            resp = self._request_with_auth_retry(
                "get", f"{ENDPOINT_EVENTS_DETAIL}?uid={encoded_uid}"
            )
            self._raise_for_status(resp, f"Enrich event {uid}")
            full_detail = resp.json()
            if not isinstance(full_detail, dict):
                return event

            if "data" in full_detail:
                event["data"] = full_detail["data"]
            if full_detail.get("event_type"):
                event["event_type"] = full_detail["event_type"]

            detail_meta = full_detail.get("metadata")
            if isinstance(detail_meta, dict):
                merged = dict(event.get("metadata") or {})
                for key, value in detail_meta.items():
                    if value is not None:
                        merged[key] = value
                event["metadata"] = merged
        except (FlareException, requests.exceptions.HTTPError) as exc:
            self._log(
                "warning",
                "Enrichment failed for UID %s (%s). Using base event.",
                uid,
                exc,
            )
        except Exception as exc:
            self._log("warning", "Enrichment failed for UID %s: %s", uid, exc)

        return event

    def apply_event_action(self, action: str, uids: list) -> dict:
        if not uids:
            return {"status_code": 200, "json": {}}

        payload = {
            "action": {"type": action},
            "targets": [{"uid": uid} for uid in uids],
        }
        resp = self._request_with_auth_retry(
            "post", ENDPOINT_EVENT_ACTIONS, json=payload
        )
        try:
            body = resp.json()
        except Exception:
            body = {}
        self._log(
            "info",
            "Flare event-actions type=%s status=%s targets=%d",
            action,
            resp.status_code,
            len(uids),
        )
        return {"status_code": resp.status_code, "text": resp.text, "json": body}

    def remediate_events(self, uids: list, batch_size: int = 10) -> dict:
        """Remediate Flare events in batches with 401 retry."""
        applied = 0
        errors: list = []
        size = max(1, int(batch_size))

        for i in range(0, len(uids), size):
            batch = uids[i : i + size]
            try:
                result = self.apply_event_action("remediate", batch)
                if result.get("status_code") in (UNAUTHORIZED, FORBIDDEN):
                    self._refresh_token()
                    result = self.apply_event_action("remediate", batch)

                status = int(result.get("status_code") or 500)
                if status >= 400:
                    detail = result.get("json") or result.get("text")
                    self._log(
                        "error",
                        "Flare remediate failed (%s): %s",
                        status,
                        detail,
                    )
                    raise FlareException(
                        format_user_facing_error(
                            FlareException(f"Flare remediate failed ({status})")
                        )
                    )
                applied += len(batch)
            except Exception as exc:
                friendly = format_user_facing_error(exc)
                errors.append(friendly)
                self._log("error", "Flare remediate batch failed: %s", friendly)

        return {"applied": applied, "errors": errors}

    def test_connection(self, validate_tenant: bool = True) -> bool:
        """Authenticate, then confirm the configured tenant is reachable."""
        try:
            self.client.generate_token()
            self._log("info", "Successfully authenticated with the Flare API.")
        except FlareException:
            raise
        except Exception as exc:
            self._log(
                "error",
                "Flare API connection test failed. Verify Flare API Key: %s",
                exc,
            )
            raise FlareUnauthorizedException(
                "Invalid API Key. Please check your credentials and try again."
            ) from exc

        if validate_tenant:
            self.validate_tenant()
        return True
