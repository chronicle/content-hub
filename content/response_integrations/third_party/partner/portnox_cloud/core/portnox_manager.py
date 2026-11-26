"""Client for the Portnox Cloud REST API.

The client has no SOAR SDK imports, so it can be used and tested outside the platform.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

import requests
from requests.auth import HTTPBasicAuth

from .constants import (
    DEFAULT_API_ROOT,
    DEFAULT_BLOCK_REASON,
    DEVICE_LIST_RESULT_KEYS,
    ENDPOINTS,
    ENRICHMENT_PREFIX,
    ERROR_BODY_MAX_LENGTH,
    MAX_PAGE_SIZE,
    MAX_RETRIES,
    MIN_PAGE_SIZE,
    RATE_LIMIT_CALLS,
    RATE_LIMIT_WINDOW_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    RETRYABLE_STATUS_CODES,
)

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class PortnoxError(Exception):
    """Generic Portnox Cloud API error."""


class PortnoxAuthError(PortnoxError):
    """HTTP 401: expired or revoked token, or wrong admin credentials."""


class PortnoxLicenseError(PortnoxError):
    """HTTP 403: operation blocked by tenant licensing."""


class PortnoxNotFoundError(PortnoxError):
    """HTTP 404: the device or account does not exist."""


class RateLimiter:
    """Sliding-window limiter shared by every call made through one client."""

    def __init__(
        self,
        calls: int = RATE_LIMIT_CALLS,
        window: float = RATE_LIMIT_WINDOW_SECONDS,
    ) -> None:
        self.calls = calls
        self.window = window
        self._timestamps: list[float] = []
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until one more request fits into the current window."""
        with self._lock:
            now = time.time()
            self._timestamps = [t for t in self._timestamps if now - t < self.window]
            if len(self._timestamps) >= self.calls:
                sleep_for = self.window - (now - self._timestamps[0]) + 0.05
                if sleep_for > 0:
                    time.sleep(sleep_for)
                now = time.time()
                self._timestamps = [t for t in self._timestamps if now - t < self.window]
            self._timestamps.append(time.time())


def normalize_mac(mac: str | None) -> str:
    """Return a MAC address as bare uppercase hex.

    Args:
        mac: A MAC address in any common notation, e.g. "aa:bb:cc:11:22:33".

    Returns:
        The bare form, e.g. "AABBCC112233", or an empty string for empty input.
    """
    if not mac:
        return ""
    return "".join(c for c in str(mac) if c.isalnum()).upper()


def validate_response(response: requests.Response, url: str) -> SingleJson:
    """Raise a typed error for a failed response and parse a successful one.

    Args:
        response: The HTTP response returned by Portnox Cloud.
        url: The requested URL, used in error messages.

    Returns:
        The parsed JSON body, or an empty dict when the body is empty.

    Raises:
        PortnoxAuthError: On HTTP 401.
        PortnoxLicenseError: On HTTP 403.
        PortnoxNotFoundError: On HTTP 404.
        PortnoxError: On any other unsuccessful status code.
    """
    body = response.text[:ERROR_BODY_MAX_LENGTH]
    if response.status_code == 401:
        raise PortnoxAuthError(
            f"Portnox Cloud rejected the credentials for {url}. The API token has most likely "
            "expired or been revoked, or the admin account is federated (Entra ID and Google "
            "Workspace accounts cannot use the API)."
        )
    if response.status_code == 403:
        raise PortnoxLicenseError(f"Portnox Cloud denied {url} due to license restrictions on this tenant.")
    if response.status_code == 404:
        raise PortnoxNotFoundError(f"Portnox Cloud has no such object: {url}")
    if response.status_code == 400:
        raise PortnoxError(f"Malformed request to {url}: {body}")
    if not response.ok:
        raise PortnoxError(f"Portnox Cloud returned HTTP {response.status_code} for {url}: {body}")

    if not response.content:
        return {}
    try:
        data: Any = response.json()
    except json.JSONDecodeError:
        return {"raw": response.text}

    # Some Portnox Cloud responses arrive as a JSON string that itself contains JSON.
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return {"raw": data}
    return data if isinstance(data, dict) else {"items": data}


def extract_account_devices(response: SingleJson) -> list[SingleJson]:
    """Pull the list of account/device entries out of a device list response.

    Args:
        response: The parsed body of /api/device/list.

    Returns:
        The account/device entries, or an empty list when none are present.
    """
    for key in DEVICE_LIST_RESULT_KEYS:
        value = response.get(key)
        if isinstance(value, list):
            return value
    return []


def flatten_device_for_enrichment(device: SingleJson, prefix: str = ENRICHMENT_PREFIX) -> dict[str, Any]:
    """Turn a Portnox Cloud device object into flat entity enrichment fields.

    Args:
        device: A device object, with its owning account under "_Account".
        prefix: The prefix added to every field name.

    Returns:
        The enrichment fields, without empty values.
    """
    account = device.get("_Account") or {}
    last_status = device.get("LastValidationStatus") or {}
    computer_data = device.get("ComputerData") or {}
    fields = {
        "DeviceId": device.get("DeviceId"),
        "AccountId": device.get("AccountId"),
        "AccountName": account.get("AccountName"),
        "GroupId": account.get("GroupId"),
        "IsBlockedByAdmin": account.get("IsBlockByAdmin"),
        "BlockReason": account.get("BlockReason"),
        "MacAddresses": ", ".join(device.get("AllMacAddresses") or []),
        "IpAddresses": ", ".join(device.get("AllIpAddresses") or []),
        "OsVersion": computer_data.get("OsVersion"),
        "LastNasId": device.get("LastValidationStatusNasId"),
        "LastAuthResult": last_status.get("Status") or last_status.get("AuthNStatus"),
        "RiskScore": device.get("RiskScore") or device.get("Risk"),
    }
    return {f"{prefix}_{key}": value for key, value in fields.items() if value not in (None, "")}


class PortnoxManager:
    """Client for the Portnox Cloud REST API."""

    def __init__(
        self,
        api_root: str = DEFAULT_API_ROOT,
        api_token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        verify_ssl: bool = True,
        timeout: int = REQUEST_TIMEOUT_SECONDS,
        logger: Any | None = None,
    ) -> None:
        """Create a client authenticated with an API token or a local admin account.

        Args:
            api_root: The Portnox Cloud API root URL.
            api_token: A Portnox Cloud API token.
            username: A local (non-federated) Portnox Cloud admin username.
            password: The password of that admin account.
            verify_ssl: Whether to verify the server's TLS certificate.
            timeout: The request timeout in seconds.
            logger: An optional logger with an ``info`` method.

        Raises:
            PortnoxError: When neither an API token nor a username and password are given.
        """
        if not api_token and not (username and password):
            raise PortnoxError("Provide either an API Token or a local admin Username and Password.")

        self.api_root = api_root if api_root.endswith("/") else f"{api_root}/"
        self.timeout = timeout
        self.logger = logger
        self._limiter = RateLimiter()

        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "GoogleSecOps-SOAR-PortnoxCloud/1.0",
        })

        # Credentials are passed per request, never stored on the shared session.
        self._auth_headers: dict[str, str] = {"Authorization": api_token} if api_token else {}
        self._basic_auth: HTTPBasicAuth | None = None if api_token else HTTPBasicAuth(username, password)

    def _log(self, message: str) -> None:
        if self.logger:
            self.logger.info(message)

    def _request(self, method: str, endpoint: str, payload: SingleJson | None = None) -> SingleJson:
        url = urljoin(self.api_root, endpoint)
        attempt = 0
        while True:
            self._limiter.acquire()
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=payload,
                    headers=self._auth_headers,
                    auth=self._basic_auth,
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                if attempt >= MAX_RETRIES:
                    raise PortnoxError(f"Network error calling {url}: {exc}") from exc
                attempt += 1
                time.sleep(2**attempt)
                continue

            if response.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
                attempt += 1
                self._log(f"Portnox Cloud returned {response.status_code}, backing off (attempt {attempt})")
                time.sleep(RATE_LIMIT_WINDOW_SECONDS if response.status_code == 429 else 2**attempt)
                continue

            return validate_response(response, url)

    def test_connectivity(self) -> bool:
        """Run the cheapest authenticated read. Used by the Ping action.

        Returns:
            True when Portnox Cloud accepted the request.
        """
        self.list_devices(page_size=MIN_PAGE_SIZE)
        return True

    def list_devices(
        self,
        filter_text: str | None = None,
        page_number: int = 1,
        page_size: int = MAX_PAGE_SIZE,
    ) -> SingleJson:
        """Get one page of devices.

        Args:
            filter_text: Free text that Portnox Cloud matches against devices and accounts.
            page_number: The 1-based page number.
            page_size: The page size, clamped to what the API accepts.

        Returns:
            The raw device list response.
        """
        page_size = max(MIN_PAGE_SIZE, min(MAX_PAGE_SIZE, int(page_size)))
        payload = {
            "Query": {
                "Filter": filter_text,
                "PageNumber": int(page_number),
                "PageSize": page_size,
                "Order": 0,
                "OrderBy": None,
            },
            "Search": None,
            "ClientTimeOffset": 0,
            "IncludeAccountWithoutDevices": False,
        }
        return self._request("POST", ENDPOINTS["device_list"], payload)

    def iter_devices(
        self,
        filter_text: str | None = None,
        page_size: int = MAX_PAGE_SIZE,
        max_pages: int = 20,
    ) -> Iterator[SingleJson]:
        """Walk the device list page by page.

        Large tenants take minutes to enumerate under the API rate limit, so the
        walk stops after ``max_pages`` pages.

        Args:
            filter_text: Free text that Portnox Cloud matches against devices and accounts.
            page_size: The page size.
            max_pages: The maximum number of pages to read.

        Yields:
            Account/device entries, each with "Account" and "Devices" keys.
        """
        for page in range(1, max_pages + 1):
            response = self.list_devices(filter_text=filter_text, page_number=page, page_size=page_size)
            entries = extract_account_devices(response)
            yield from entries
            if len(entries) < page_size:
                return

    def find_devices_by_mac(self, mac: str, max_pages: int = 20) -> list[SingleJson]:
        """Find devices with a network interface that carries this MAC address.

        Args:
            mac: The MAC address, in any common notation.
            max_pages: The maximum number of device list pages to read.

        Returns:
            Matching devices, each with its owning account under "_Account".
        """
        wanted = normalize_mac(mac)
        matches = []
        for entry in self.iter_devices(filter_text=mac, max_pages=max_pages):
            for device in entry.get("Devices") or []:
                macs = device.get("AllMacAddresses") or []
                if any(normalize_mac(m) == wanted for m in macs):
                    device["_Account"] = entry.get("Account")
                    matches.append(device)
        return matches

    def find_devices_by_ip(self, ip_address: str, max_pages: int = 20) -> list[SingleJson]:
        """Find devices whose IP addresses include exactly this address.

        The free-text search also returns look-alike addresses (10.0.0.1 matches
        10.0.0.10), so results are filtered to exact matches.

        Args:
            ip_address: The IP address.
            max_pages: The maximum number of device list pages to read.

        Returns:
            Matching devices, each with its owning account under "_Account".
        """
        wanted = ip_address.strip().lower()
        return [
            device
            for device in self.find_devices_by_text(ip_address, max_pages=max_pages)
            if wanted in (str(ip).strip().lower() for ip in device.get("AllIpAddresses") or [])
        ]

    def find_devices_by_text(self, text: str, max_pages: int = 5) -> list[SingleJson]:
        """Find devices by free text, such as a hostname or an IP address.

        Args:
            text: The text to search for.
            max_pages: The maximum number of device list pages to read.

        Returns:
            Matching devices, each with its owning account under "_Account".
        """
        results = []
        for entry in self.iter_devices(filter_text=text, max_pages=max_pages):
            for device in entry.get("Devices") or []:
                device["_Account"] = entry.get("Account")
                results.append(device)
        return results

    def block_device(self, device_id: str, reason: str = DEFAULT_BLOCK_REASON) -> None:
        """Block a device's network access.

        Args:
            device_id: The device GUID (not its MAC address).
            reason: The block reason shown in Portnox Cloud.
        """
        self._request("POST", ENDPOINTS["device_block"], {"EntityId": str(device_id), "Reason": reason})

    def block_account(self, account_id: str, reason: str = DEFAULT_BLOCK_REASON) -> None:
        """Block an account.

        Args:
            account_id: The account name, usually the user's e-mail address.
            reason: The block reason shown in Portnox Cloud.
        """
        self._request("POST", ENDPOINTS["account_block"], {"EntityId": str(account_id), "Reason": reason})

    def move_account_to_group(self, account_id: str, group_name: str) -> None:
        """Move a non-LDAP account to another group.

        Pointing the target group at a restrictive policy and moving the account
        into it is the practical way to quarantine an account.

        Args:
            account_id: The account name, usually the user's e-mail address.
            group_name: The name of the target group.
        """
        self._request(
            "POST",
            ENDPOINTS["account_move_group"],
            {"AccountId": str(account_id), "GroupName": group_name},
        )
