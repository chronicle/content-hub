from __future__ import annotations

from typing import TYPE_CHECKING

import requests

from .data_models import ScanLaunch
from .exceptions import HoudinAccountError, HoudinError
from .houdin_constants import API_ROOT, MAX_RETRIES, REQUEST_TIMEOUT, RESULT_BATCH_SIZE, USER_AGENT
from .houdin_utils import error_message, normalize_scanners

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class HoudinManager:
    """Thin client for the Houdin REST API (https://app.houdin.io/docs/api)."""

    def __init__(self, api_key: str, api_root: str | None = None, verify_ssl: bool = True) -> None:
        """Open a session on the instance's API Root (the constant is its default).

        Raises:
            HoudinError: The API Key is blank.
        """
        if not api_key:
            raise HoudinError("API Key is missing from the integration configuration.")
        self.api_root: str = (api_root or API_ROOT).strip().rstrip("/")
        self.session: requests.Session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update({"X-API-Key": api_key, "Accept": "application/json", "User-Agent": USER_AGENT})

    def _request(
        self,
        method: str,
        path: str,
        params: SingleJson | None = None,
        json: SingleJson | None = None,
    ) -> requests.Response:
        """One call to the API, retried on a 5xx or a dropped connection.

        Raises:
            HoudinAccountError: No attempt got an answer below 500.
        """
        url: str = f"{self.api_root}/{path}"
        last_error: Exception | None = None
        for _attempt in range(MAX_RETRIES + 1):
            try:
                response: requests.Response = self.session.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    timeout=REQUEST_TIMEOUT,
                )
            except requests.RequestException as error:
                last_error = error
                continue
            if response.status_code >= 500:
                last_error = HoudinError(f"Houdin answered {response.status_code} on {method} {path}", 500)
                continue
            return response
        raise HoudinAccountError(f"Could not reach Houdin: {last_error}")

    def _raise_for_status(self, response: requests.Response) -> None:
        """Turn an error answer into the matching exception.

        Raises:
            HoudinAccountError: 401, 429, or a 400 about the key or the quota.
            HoudinError: Any other answer of 400 or above.
        """
        if response.status_code < 400:
            return
        message: str = error_message(response)
        lowered: str = message.lower()
        account_wide: bool = response.status_code in (401, 429) or (
            response.status_code == 400 and ("api key" in lowered or "quota" in lowered)
        )
        error_type: type[HoudinError] = HoudinAccountError if account_wide else HoudinError
        raise error_type(message, response.status_code)

    def ping(self) -> None:
        """Check that the API key is accepted.

        Raises:
            HoudinError: The key is rejected or the API is unreachable.
        """
        self._raise_for_status(self._request("POST", "ping"))

    def launch_scan(self, artifact: str, scanners: list[str] | None = None, force_rescan: bool = False) -> ScanLaunch:
        """Start a scan; the artifact's type is detected server-side.

        Raises:
            HoudinError: Houdin refused the artifact, or answered without a scanID.
        """
        payload: SingleJson = {"artifact": artifact}
        selected: list[str] | None = normalize_scanners(scanners)
        if selected:
            payload["scanners"] = selected
        if force_rescan:
            payload["forceRescan"] = True
        response: requests.Response = self._request("POST", "scan/launch", json=payload)
        self._raise_for_status(response)
        body: SingleJson = response.json()
        scan_id: str | None = body.get("scanID")
        if not scan_id:
            raise HoudinError(f"Houdin accepted the scan but returned no scanID: {body}")
        return ScanLaunch(scan_id=scan_id, status=body.get("status", ""), cached=bool(body.get("cached")))

    def get_results(self, scan_ids: list[str]) -> dict[str, SingleJson]:
        """Scan documents keyed by scanID, read once; scans still running are left out.

        Raises:
            HoudinError: Houdin refused the request.
        """
        documents: dict[str, SingleJson] = {}
        for start in range(0, len(scan_ids), RESULT_BATCH_SIZE):
            batch: list[str] = scan_ids[start : start + RESULT_BATCH_SIZE]
            response: requests.Response = self._request("POST", "scan/result", json={"scanIDs": batch})
            self._raise_for_status(response)
            body: SingleJson = response.json()
            documents.update(body.get("results") or {})
        return documents
