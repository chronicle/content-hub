from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

from .houdin_constants import (
    API_ROOT,
    MAX_RETRIES,
    MESMER_MODULES,
    REQUEST_TIMEOUT,
    RESULT_BATCH_SIZE,
    RUN_POLL_INTERVAL,
    RUN_WAIT_SECONDS,
    USER_AGENT,
)


class HoudinError(Exception):
    """An answer from Houdin that is not the one asked for, with the API's own message."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class HoudinAccountError(HoudinError):
    """A refusal that concerns the account, not one artifact: rejected key, spent quota, daily cap, unreachable API."""


@dataclass(frozen=True)
class ScanLaunch:
    scan_id: str
    status: str
    cached: bool


class HoudinManager:
    """Thin client for the Houdin REST API (https://app.houdin.io/docs/api)."""

    def __init__(self, api_key: str, api_root: str | None = None, verify_ssl: bool = True) -> None:
        if not api_key:
            raise HoudinError("API Key is missing from the integration configuration.")
        # The API Root parameter of the instance; the constant is its default.
        self.api_root = (api_root or API_ROOT).strip().rstrip("/")
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update({
            "X-API-Key": api_key,
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        })

    # ----------------------------------------------------------------- HTTP

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        """One call to the API, retried on a 5xx or a dropped connection."""
        url = f"{self.api_root}/{path}"
        kwargs.setdefault("timeout", REQUEST_TIMEOUT)
        last_error: Exception | None = None
        for _attempt in range(MAX_RETRIES + 1):
            try:
                response = self.session.request(method, url, **kwargs)
            except requests.RequestException as error:
                last_error = error
                continue
            if response.status_code >= 500:
                last_error = HoudinError(f"Houdin answered {response.status_code} on {method} {path}", 500)
                continue
            return response
        raise HoudinAccountError(f"Could not reach Houdin: {last_error}")

    @staticmethod
    def _error_message(response: requests.Response) -> str:
        """The API answers errors as plain text or as {"error": ...}; return either as a string."""
        try:
            body = response.json()
        except ValueError:
            return response.text.strip() or f"HTTP {response.status_code}"
        if isinstance(body, dict):
            message = body.get("error") or body.get("message") or ""
            details = body.get("details")
            if details:
                message = f"{message}: {details}" if message else str(details)
            if message:
                return str(message)
        return str(body)

    def _raise_for_status(self, response: requests.Response) -> None:
        if response.status_code < 400:
            return
        message = self._error_message(response)
        lowered = message.lower()
        account_wide = response.status_code in (401, 429) or (
            response.status_code == 400 and ("api key" in lowered or "quota" in lowered)
        )
        error_type = HoudinAccountError if account_wide else HoudinError
        raise error_type(message, response.status_code)

    # ------------------------------------------------------------------ API

    def ping(self) -> None:
        """Raise HoudinError unless the API key is accepted."""
        response = self._request("POST", "ping")
        self._raise_for_status(response)

    @staticmethod
    def normalize_scanners(scanners: list[str] | None) -> list[str] | None:
        """Trim the list; None when empty so the API picks its default set.

        An explicit list always gets the MesmerAI modules appended, since the
        verdict is what the enrichment and the widget read.
        """
        if not scanners:
            return None
        cleaned = [s.strip() for s in scanners if isinstance(s, str) and s.strip()]
        if not cleaned:
            return None
        for module in MESMER_MODULES:
            if module not in cleaned:
                cleaned.append(module)
        return cleaned

    def launch_scan(
        self,
        artifact: str,
        scanners: list[str] | None = None,
        force_rescan: bool = False,
    ) -> ScanLaunch:
        """Start a scan; the artifact's type is detected server-side."""
        payload: dict[str, Any] = {"artifact": artifact}
        selected = self.normalize_scanners(scanners)
        if selected:
            payload["scanners"] = selected
        if force_rescan:
            payload["forceRescan"] = True
        response = self._request("POST", "scan/launch", json=payload)
        self._raise_for_status(response)
        body = response.json()
        scan_id = body.get("scanID")
        if not scan_id:
            raise HoudinError(f"Houdin accepted the scan but returned no scanID: {body}")
        return ScanLaunch(
            scan_id=scan_id,
            status=body.get("status", ""),
            cached=bool(body.get("cached")),
        )

    def get_result(self, scan_id: str) -> dict[str, Any] | None:
        """The scan document, or None while the scan is still running."""
        response = self._request("GET", "scan/result", params={"scanID": scan_id})
        if response.status_code == 202:
            return None
        self._raise_for_status(response)
        return response.json()

    def get_results(self, scan_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Scan documents keyed by scanID. Scans still running are left out."""
        documents: dict[str, dict[str, Any]] = {}
        for start in range(0, len(scan_ids), RESULT_BATCH_SIZE):
            batch = scan_ids[start : start + RESULT_BATCH_SIZE]
            response = self._request("POST", "scan/result", json={"scanIDs": batch})
            self._raise_for_status(response)
            body = response.json()
            documents.update(body.get("results") or {})
        return documents

    def wait_for_results(
        self,
        scan_ids: list[str],
        seconds: int = RUN_WAIT_SECONDS,
        interval: int = RUN_POLL_INTERVAL,
    ) -> dict[str, dict[str, Any]]:
        """Scan documents keyed by scanID, polling for up to `seconds`; scans still running are left out."""
        documents: dict[str, dict[str, Any]] = {}
        pending = list(scan_ids)
        polls = max(1, seconds // interval)
        for attempt in range(polls):
            documents.update(self.get_results(pending))
            pending = [scan_id for scan_id in pending if scan_id not in documents]
            if not pending or attempt == polls - 1:
                break
            time.sleep(interval)
        return documents
