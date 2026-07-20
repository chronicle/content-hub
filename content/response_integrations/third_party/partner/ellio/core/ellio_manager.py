"""ELLIO API client: CTI lookup, CBS lookup, Blocklist Automation (EDL). X-API-Key auth.

API reference: docs.ellio.tech/api-reference.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

import requests

from .constants import INTEGRATION_VERSION, REQUEST_TIMEOUT


class EllioManagerError(Exception):
    """General exception for the ELLIO manager."""


class EllioManager:
    """Client for the ELLIO API: CTI lookup, CBS lookup, Blocklist Automation (EDL)."""

    def __init__(
        self,
        ellio_api_root: str,
        ellio_api_key: str,
        blocklist_ruleset_id: str | None = None,
        verify_ssl: bool = True,
    ) -> None:
        """Set up the API session.

        Args:
            ellio_api_root: The ELLIO API root URL.
            ellio_api_key: The ELLIO API key (X-API-Key header).
            blocklist_ruleset_id: Optional Blocklist Automation ruleset ID.
            verify_ssl: Verify the API server's SSL certificate.
        """
        self.ellio_api_root = (ellio_api_root or "").strip().rstrip("/")
        self.blocklist_ruleset_id = blocklist_ruleset_id.strip() if blocklist_ruleset_id else None
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update({
            "X-API-Key": (ellio_api_key or "").strip(),
            "Accept": "application/json",
            "User-Agent": f"ELLIO-SecOps-SOAR/{INTEGRATION_VERSION}",
        })

    # ---------- connectivity ----------
    def test_connectivity(self) -> None:
        """Validate auth via a CTI lookup of a documentation IP (expects 200).

        Raises:
            EllioManagerError: If the connection or authentication fails.
        """
        url = f"{self.ellio_api_root}/v1/cti/lookup/192.0.2.1"
        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            self._validate(resp, "Unable to connect to the ELLIO API")
        except requests.RequestException as error:
            raise EllioManagerError(f"Unable to connect to the ELLIO API: {error}") from error

    # ---------- CBS (Common Business Services) classification ----------
    def cbs_lookup(self, ip: str) -> dict[str, Any] | None:
        """Classify an IP against ELLIO Common Business Services.

        GET /v1/cbs/lookup?ip=<ip> (X-API-Key).

        Args:
            ip: The IP address to look up.

        Returns:
            The response dict {ip, found, cidr, labels[], cbs_ids[], providers[],
            types[], services[], regions[], matches[]} when found, else None.

        Raises:
            EllioManagerError: If the request fails or the API returns an error.
        """
        url = f"{self.ellio_api_root}/v1/cbs/lookup"
        try:
            resp = self.session.get(url, params={"ip": ip}, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as error:
            raise EllioManagerError(f"ELLIO CBS lookup failed for {ip}: {error}") from error
        if resp.status_code == 404:
            return None
        self._validate(resp, f"ELLIO CBS lookup failed for {ip}")
        data = self._json(resp, f"ELLIO CBS lookup failed for {ip}")
        return data if data.get("found") else None

    # ---------- enrichment ----------
    def lookup_ip(self, ip: str) -> dict[str, Any] | None:
        """ELLIO extended CTI lookup (GET /v1/cti/extended_lookup/{ip}).

        Args:
            ip: The IP address to look up.

        Returns:
            A normalized record (mapped to the docs.ellio.tech extended-ip-lookup
            schema), or None when the IP is not seen.

        Raises:
            EllioManagerError: If the request fails or the API returns an error.
        """
        url = f"{self.ellio_api_root}/v1/cti/extended_lookup/{quote(ip)}"
        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as error:
            raise EllioManagerError(f"ELLIO API lookup failed for {ip}: {error}") from error
        if resp.status_code == 404:
            return None
        self._validate(resp, f"ELLIO API lookup failed for {ip}")
        data = self._json(resp, f"ELLIO API lookup failed for {ip}")
        if not data.get("seen"):
            return None

        def join(v: Any, cap: int = 25) -> str:
            """Pipe-join a list, capped so a field never outgrows the SOAR display.

            Args:
                v: A list to join, or a scalar passed through as a string.
                cap: Maximum items before the '(+N more)' sentinel is appended.

            Returns:
                The joined string, or '' for empty input.
            """
            if isinstance(v, list):
                items = [str(x) for x in v if x not in (None, "") and str(x).strip()]
                if len(items) > cap:
                    return "|".join(items[:cap]) + f"|(+{len(items) - cap} more)"
                return "|".join(items)
            return str(v) if v not in (None, "") else ""

        # the CTI API uses "unknown" as an actor placeholder; drop it so the entity
        # is never enriched with ELLIO_actor=unknown (mirrors the wire contract rule)
        actor = data.get("actor", "")
        if isinstance(actor, str) and actor.lower() == "unknown":
            actor = ""

        src_geo = ((data.get("src") or {}).get("geo")) or {}
        country = src_geo.get("country") or {}
        continent = src_geo.get("continent") or {}
        net = data.get("network") or {}
        fp = data.get("fingerprints") or {}
        http = data.get("http") or {}

        return {
            "ip": ip,
            "rdns": data.get("rdns", ""),
            "classification": data.get("classification", ""),
            "actor": actor,
            "spoofable": data.get("spoofable"),
            # CVEs come straight from the API (key `cve`); filter the stray empty string
            "cve": join([c for c in (data.get("cve") or []) if str(c).strip()], cap=20),
            "tags": join(data.get("tags")),
            "tag_ids": join(data.get("tag_ids")),
            "country": join(country.get("code")),
            "country_name": join(country.get("name")),
            "continent": join(continent.get("code")),
            "ports": join(net.get("ports")),
            "non_spoofable_ports": join(net.get("non_spoofable_ports")),
            "muonfp": join(fp.get("muonfp"), cap=10),
            "ja3": join(fp.get("ja3"), cap=10),
            "ja4": join(fp.get("ja4"), cap=10),
            # http observation arrays are the largest fields for active scanners; cap hard
            "http_path": join(http.get("path"), cap=15),
            "http_user_agent": join(http.get("user_agent"), cap=10),
            "first_seen": data.get("first_seen", ""),
            "last_seen": data.get("last_seen", ""),
        }

    # ---------- response action ----------
    def add_ip_to_blocklist(self, ip_address: str, name: str | None = None,
                            conflict_resolution: str = "extend",
                            expires_in_days: int = 0) -> dict[str, Any]:
        """Add an IP rule to an ELLIO Blocklist Automation (EDL) ruleset.

        POST /v1/edl/ip-rulesets/{ruleset_id}/rules (Read & Write API key).

        Args:
            ip_address: The IP address to blocklist.
            name: Optional rule name; auto-built case context when empty.
            conflict_resolution: extend | override | skip | fail.
            expires_in_days: Rule expiry in days; 0 creates a permanent rule.

        Returns:
            The API response, or {ip, status} when the response body is empty.

        Raises:
            EllioManagerError: If no ruleset ID is configured or the API call fails.
        """
        if not self.blocklist_ruleset_id:
            raise EllioManagerError("Blocklist Ruleset ID is not configured")
        url = f"{self.ellio_api_root}/v1/edl/ip-rulesets/{self.blocklist_ruleset_id}/rules"
        payload = {"ip": ip_address, "conflict_resolution": conflict_resolution or "extend"}
        if name:
            payload["name"] = name
        try:
            days = int(expires_in_days)
        except (TypeError, ValueError):
            days = 0
        if days > 0:  # omit for a permanent rule
            payload["expires_in_days"] = days
        try:
            resp = self.session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            self._validate(resp, f"Unable to add {ip_address} to the blocklist")
        except requests.RequestException as error:
            raise EllioManagerError(f"Blocklist POST failed for {ip_address}: {error}") from error
        if not resp.content:
            return {"ip": ip_address, "status": "added"}
        return self._json(resp, f"Unable to add {ip_address} to the blocklist")

    @staticmethod
    def _json(response: requests.Response, error_msg: str) -> dict[str, Any]:
        """Parse the response body as JSON.

        Args:
            response: The API response.
            error_msg: Context prefix for the raised error.

        Returns:
            The parsed JSON object.

        Raises:
            EllioManagerError: If the body is not valid JSON (e.g. a proxy error page).
        """
        try:
            return response.json()
        except ValueError as error:
            raise EllioManagerError(f"{error_msg}: response is not valid JSON") from error

    @staticmethod
    def _validate(response: requests.Response, error_msg: str = "An error occurred") -> None:
        """Turn an HTTP error response into an EllioManagerError.

        Args:
            response: The API response to check.
            error_msg: Context prefix for the raised error.

        Raises:
            EllioManagerError: If the response status is an HTTP error.
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            detail = error.response.content[:300].decode("utf-8", errors="ignore")
            raise EllioManagerError(f"{error_msg}: {error} - {detail}") from error
