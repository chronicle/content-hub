# ============================================================================
# name       : PortnoxManager.py
# description: Wrapper around the Portnox Cloud REST API.
#              Contains NO Siemplify/SecOps SDK imports on purpose, so it can
#              be unit-tested and run locally outside the platform.
# ============================================================================

from __future__ import annotations
import time
import threading
from urllib.parse import urljoin, quote

import requests
from requests.auth import HTTPBasicAuth

DEFAULT_API_ROOT = "https://clear.portnox.com:8081/CloudPortalBackEnd/"

# Portnox Cloud enforces 10 requests per 10 seconds per tenant.
RATE_LIMIT_CALLS = 10
RATE_LIMIT_WINDOW = 10.0

# /api/device/list only accepts PageSize between 5 and 30.
MIN_PAGE_SIZE = 5
MAX_PAGE_SIZE = 30

ENDPOINTS = {
    "device_list": "api/device/list",
    "device_get": "api/device/{device_id}",
    "device_block": "api/device/block",
    "device_delete": "api/device/{device_id}",
    "account_block": "api/account/block",
    "account_move_group": "api/account/move-to-group",
    "mab_search": "api/mac-based-accounts/search",
    "mab_whitelist_add": "api/mac-based-accounts/mac-whitelist-add",
    "mab_whitelist_remove": "api/mac-based-accounts/mac-whitelist-remove",
    "sites": "api/nases/sites",
    "nases": "api/nases",
}


class PortnoxError(Exception):
    """Generic Portnox Cloud API error."""


class PortnoxAuthError(PortnoxError):
    """Raised on HTTP 401 - expired / revoked token or wrong admin credentials."""


class PortnoxLicenseError(PortnoxError):
    """Raised on HTTP 403 - operation blocked by tenant licensing."""


class PortnoxNotFoundError(PortnoxError):
    """Raised on HTTP 404 - device / account / site does not exist."""


class _RateLimiter(object):
    """Simple sliding-window limiter shared by every call on one manager."""

    def __init__(self, calls=RATE_LIMIT_CALLS, window=RATE_LIMIT_WINDOW):
        self.calls = calls
        self.window = window
        self._timestamps = []
        self._lock = threading.Lock()

    def acquire(self):
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


def normalize_mac(mac):
    """Return a MAC as bare uppercase hex, e.g. 'AA:BB:CC:11:22:33' -> 'AABBCC112233'."""
    if not mac:
        return ""
    return "".join(c for c in str(mac) if c.isalnum()).upper()


def mac_variants(mac):
    """Every common textual form of a MAC, for matching against Portnox data."""
    bare = normalize_mac(mac)
    if len(bare) != 12:
        return [str(mac)]
    pairs = [bare[i:i + 2] for i in range(0, 12, 2)]
    return [
        bare,
        ":".join(pairs),
        "-".join(pairs),
        ":".join(pairs).lower(),
        "-".join(pairs).lower(),
    ]


class PortnoxManager(object):
    """Thin, explicit client for the Portnox Cloud REST API."""

    def __init__(self, api_root=DEFAULT_API_ROOT, api_token=None, username=None,
                 password=None, verify_ssl=True, timeout=60, logger=None):
        """
        Authenticate either with an API token (Settings > Profile Settings >
        Account Settings > Cloud API tokens) or with a LOCAL Portnox admin
        username/password. Accounts federated through Entra ID or Google
        Workspace cannot be used against the API.
        """
        if not api_token and not (username and password):
            raise PortnoxError(
                "Provide either an API Token or a local admin Username and Password.")

        self.api_root = api_root if api_root.endswith("/") else api_root + "/"
        self.timeout = timeout
        self.logger = logger
        self._limiter = _RateLimiter()

        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "GoogleSecOps-SOAR-Portnox/1.0",
        })

        if api_token:
            # NOTE: confirm the exact scheme against securityDefinitions in your
            # tenant's Swagger (Help > API REFERENCE). Swap this line if your
            # tenant expects a bare token or a custom header instead of Bearer.
            self.session.headers["Authorization"] = api_token
            self.auth = None
        else:
            self.auth = HTTPBasicAuth(username, password)

    # -- plumbing ----------------------------------------------------------

    def _log(self, message):
        if self.logger:
            self.logger.info(message)

    def _request(self, method, endpoint, payload=None, retries=2):
        url = urljoin(self.api_root, endpoint)
        attempt = 0
        while True:
            self._limiter.acquire()
            try:
                response = self.session.request(
                    method=method, url=url, json=payload,
                    auth=self.auth, timeout=self.timeout)
            except requests.RequestException as exc:
                if attempt >= retries:
                    raise PortnoxError("Network error calling {0}: {1}".format(url, exc))
                attempt += 1
                time.sleep(2 ** attempt)
                continue

            if response.status_code in (429, 502, 503, 504) and attempt < retries:
                attempt += 1
                self._log("Portnox returned {0}, backing off (attempt {1})".format(
                    response.status_code, attempt))
                time.sleep(RATE_LIMIT_WINDOW if response.status_code == 429 else 2 ** attempt)
                continue

            return self._validate(response, url)

    @staticmethod
    def _validate(response, url):
        if response.status_code == 401:
            raise PortnoxAuthError(
                "Portnox rejected the credentials for {0}. The API token has most "
                "likely expired or been revoked, or the admin account is federated "
                "(Entra ID / Google Workspace accounts cannot use the API).".format(url))
        if response.status_code == 403:
            raise PortnoxLicenseError(
                "Portnox denied {0} due to license restrictions on this tenant.".format(url))
        if response.status_code == 404:
            raise PortnoxNotFoundError("Portnox has no such object: {0}".format(url))
        if response.status_code == 400:
            raise PortnoxError("Malformed request to {0}: {1}".format(url, response.text[:500]))
        if not response.ok:
            raise PortnoxError("Portnox returned HTTP {0} for {1}: {2}".format(
                response.status_code, url, response.text[:500]))

        if not response.content:
            return {}
        try:
            data = response.json()
        except ValueError:
            return {"raw": response.text}
        # Some Portnox responses arrive as a JSON string containing JSON.
        if isinstance(data, str):
            try:
                import json
                data = json.loads(data)
            except ValueError:
                pass
        return data

    # -- connectivity ------------------------------------------------------

    def test_connectivity(self):
        """Cheapest read that still exercises auth. Used by the Ping action."""
        self._request("POST", ENDPOINTS["device_list"], {
            "Query": {"Filter": None, "PageNumber": 1, "PageSize": MIN_PAGE_SIZE,
                      "Order": 0, "OrderBy": None},
            "IncludeAccountWithoutDevices": False,
        })
        return True

    # -- devices -----------------------------------------------------------

    def list_devices(self, filter_text=None, page_number=1, page_size=MAX_PAGE_SIZE,
                     search_field=None, search_value=None,
                     include_accounts_without_devices=False):
        """One page of /api/device/list. Returns the raw DeviceQueryResponse."""
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
            "IncludeAccountWithoutDevices": include_accounts_without_devices,
        }
        if search_field is not None:
            # Search.Field is a numeric enum (e.g. 15 = Browser). Confirm the
            # value you need in the Swagger DeviceQueryRequest definition.
            payload["Search"] = {"Field": int(search_field), "Value": search_value}
        return self._request("POST", ENDPOINTS["device_list"], payload)

    def iter_devices(self, filter_text=None, page_size=MAX_PAGE_SIZE, max_pages=20,
                     search_field=None, search_value=None):
        """Walk pages of /api/device/list, yielding AccountDevices entries.

        Respect max_pages: at 30 records/page and 10 requests/10s, a large
        tenant takes minutes to enumerate, which will time out an action.
        """
        page = 1
        while page <= max_pages:
            response = self.list_devices(
                filter_text=filter_text, page_number=page, page_size=page_size,
                search_field=search_field, search_value=search_value)
            entries = self._extract_account_devices(response)
            if not entries:
                return
            for entry in entries:
                yield entry
            if len(entries) < page_size:
                return
            page += 1

    @staticmethod
    def _extract_account_devices(response):
        """DeviceQueryResponse shape varies; pull the AccountDevices list out."""
        if not isinstance(response, dict):
            return []
        for key in ("Entities", "AccountDevices", "Items", "Result", "Data"):
            value = response.get(key)
            if isinstance(value, list):
                return value
        return []

    def find_devices_by_mac(self, mac, max_pages=20):
        """Return device dicts whose interfaces carry this MAC, in any format."""
        wanted = normalize_mac(mac)
        matches = []
        for entry in self.iter_devices(filter_text=mac, max_pages=max_pages):
            for device in (entry.get("Devices") or []):
                macs = device.get("AllMacAddresses") or []
                if any(normalize_mac(m) == wanted for m in macs):
                    device["_Account"] = entry.get("Account")
                    matches.append(device)
        return matches

    def find_devices_by_text(self, text, max_pages=5):
        """Free-text lookup: hostname, IP, account name."""
        results = []
        for entry in self.iter_devices(filter_text=text, max_pages=max_pages):
            for device in (entry.get("Devices") or []):
                device["_Account"] = entry.get("Account")
                results.append(device)
        return results

    def get_device(self, device_id):
        return self._request(
            "GET", ENDPOINTS["device_get"].format(device_id=quote(str(device_id))))

    def block_device(self, device_id, reason="Blocked by Google SecOps SOAR"):
        """POST /api/device/block. EntityId is the device GUID, not the MAC."""
        self._request("POST", ENDPOINTS["device_block"],
                      {"EntityId": str(device_id), "Reason": reason})
        return True

    def delete_device(self, device_id):
        self._request(
            "DELETE", ENDPOINTS["device_delete"].format(device_id=quote(str(device_id))))
        return True

    # -- accounts ----------------------------------------------------------

    def block_account(self, account_id, reason="Blocked by Google SecOps SOAR"):
        """POST /api/account/block. EntityId is the account name / ID."""
        self._request("POST", ENDPOINTS["account_block"],
                      {"EntityId": str(account_id), "Reason": reason})
        return True

    def move_account_to_group(self, account_id, group_name):
        """Move a non-LDAP account to another Portnox group.

        This is the practical way to apply a quarantine policy: point the
        target group at a restrictive policy and move the account into it.
        Device risk scores are recalculated against the new group's policy.
        """
        self._request("POST", ENDPOINTS["account_move_group"],
                      {"AccountId": str(account_id), "GroupName": group_name})
        return True

    # -- MAB ---------------------------------------------------------------

    def search_mab_accounts_by_mac(self, macs):
        whitelist = [{"Mac": m, "Description": None, "Expiration": None}
                     for m in (macs if isinstance(macs, (list, tuple)) else [macs])]
        return self._request("POST", ENDPOINTS["mab_search"], {"MacWhiteList": whitelist})

    def remove_macs_from_mab_account(self, account_name, macs):
        """Revoke MAB access by pulling MACs out of the account whitelist."""
        whitelist = [{"Mac": m, "Description": None, "Expiration": None}
                     for m in (macs if isinstance(macs, (list, tuple)) else [macs])]
        self._request("DELETE", ENDPOINTS["mab_whitelist_remove"],
                      {"AccountName": account_name, "MacWhiteList": whitelist})
        return True

    def add_macs_to_mab_account(self, account_name, macs, expiration=None,
                                description="Added by Google SecOps SOAR"):
        whitelist = [{"Mac": m, "Description": description, "Expiration": expiration}
                     for m in (macs if isinstance(macs, (list, tuple)) else [macs])]
        self._request("POST", ENDPOINTS["mab_whitelist_add"],
                      {"AccountName": account_name, "MacWhiteList": whitelist})
        return True

    # -- infrastructure ----------------------------------------------------

    def get_sites(self):
        return self._request("GET", ENDPOINTS["sites"])

    def get_nases(self, mode=None):
        return self._request("POST", ENDPOINTS["nases"], {} if mode is None else {"Mode": mode})


# --- helpers the actions use to build enrichment tables ---------------------

def flatten_device_for_enrichment(device, prefix="Portnox"):
    """Turn a Portnox device object into flat key/value enrichment fields."""
    account = device.get("_Account") or {}
    last_status = device.get("LastValidationStatus") or {}
    fields = {
        "DeviceId": device.get("DeviceId"),
        "AccountId": device.get("AccountId"),
        "AccountName": account.get("AccountName"),
        "GroupId": account.get("GroupId"),
        "IsBlockedByAdmin": account.get("IsBlockByAdmin"),
        "BlockReason": account.get("BlockReason"),
        "MacAddresses": ", ".join(device.get("AllMacAddresses") or []),
        "IpAddresses": ", ".join(device.get("AllIpAddresses") or []),
        "OsVersion": (device.get("ComputerData") or {}).get("OsVersion"),
        "LastNasId": device.get("LastValidationStatusNasId"),
        "LastAuthResult": last_status.get("Status") or last_status.get("AuthNStatus"),
        "RiskScore": device.get("RiskScore") or device.get("Risk"),
    }
    return {"{0}_{1}".format(prefix, k): v for k, v in fields.items() if v not in (None, "")}
