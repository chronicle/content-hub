"""
SOCRadar Manager
================
API wrapper for SOCRadar REST API v4.
Used by Connector, Actions, and Jobs.

Base URL: https://platform.socradar.com/api
Auth: Header -> API-Key: {api_key}
"""
from __future__ import annotations
from typing import Any

import json
import math
import time
import requests


STATUS_CODES = {
    "OPEN": 0, "INVESTIGATING": 1, "RESOLVED": 2, "PENDING_INFO": 4,
    "LEGAL_REVIEW": 5, "VENDOR_ASSESSMENT": 6, "FALSE_POSITIVE": 9,
    "DUPLICATE": 10, "PROCESSED_INTERNALLY": 11, "MITIGATED": 12,
    "NOT_APPLICABLE": 13,
}
STATUS_NAMES = {v: k for k, v in STATUS_CODES.items()}
VALID_SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
PAGE_LIMIT = 100
MAX_RETRIES = 3
RETRY_DELAY = 2


class SOCRadarManagerError(Exception):
    pass


class SOCRadarManager:
    """Manager class for interacting with the SOCRadar REST API v4."""

    def __init__(self, api_root: str, api_key: str, company_id: str | int, verify_ssl: bool = True) -> None:
        self.api_root: str = api_root.rstrip("/")
        self.api_key: str = api_key
        self.company_id: str = str(company_id)
        self.verify_ssl: bool = verify_ssl
        self.session: requests.Session = requests.Session()
        self.session.headers.update({
            "API-Key": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        self.session.verify = self.verify_ssl

    def _build_url(self, endpoint: str) -> str:
        """Build full API URL for a company-scoped endpoint."""
        return f"{self.api_root}/company/{self.company_id}/{endpoint}"

    def _request(self, method: str, endpoint: str, body: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send an HTTP request to the SOCRadar API with retry logic.

        Raises:
            SOCRadarManagerError: On auth failure, client errors, or after max retries.
        """
        url = self._build_url(endpoint)
        for attempt in range(MAX_RETRIES):
            try:
                if method == "POST":
                    resp = self.session.post(url, json=body, timeout=30)
                else:
                    resp = self.session.get(url, params=params, timeout=30)
                if resp.status_code == 401:
                    raise SOCRadarManagerError("Unauthorized - check your API key")
                if resp.status_code == 403:
                    raise SOCRadarManagerError("Forbidden - insufficient permissions")
                if resp.status_code == 404:
                    raise SOCRadarManagerError("Not Found - check company ID or endpoint")
                if 400 <= resp.status_code < 500:
                    try:
                        err_msg = resp.json().get("message", resp.text[:200])
                    except Exception as e:
                        err_msg = f"{resp.text[:200]} (parse error: {e})"
                    raise SOCRadarManagerError(f"Client error {resp.status_code}: {err_msg}")
                resp.raise_for_status()
                try:
                    data = resp.json()
                except (ValueError, json.JSONDecodeError):
                    raise SOCRadarManagerError(f"Invalid JSON response from {url}")
                if isinstance(data, dict) and "is_success" in data and not data["is_success"]:
                    raise SOCRadarManagerError(f"API error: {data.get('message', 'Unknown')}")
                return data
            except requests.exceptions.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    raise SOCRadarManagerError(f"Request failed after {MAX_RETRIES} attempts: {e}")

    @staticmethod
    def _extract_alarms_data(response: dict[str, Any]) -> tuple[list[dict[str, Any]], int, int]:
        """Extract (alarms_list, total_records, total_pages) from a SOCRadar API response.

        Handles both response shapes:
          A) { "data": [ {alarm}, {alarm}, ... ] }                              -- legacy/flat
          B) { "data": { "alarms": [...], "total_records": N, "total_pages": M } } -- current
        """
        if not isinstance(response, dict):
            return [], 0, 1
        data_field = response.get("data", [])
        if isinstance(data_field, list):
            return data_field, response.get("total_records", len(data_field)), 1
        if isinstance(data_field, dict):
            alarms = (
                data_field.get("alarms")
                or data_field.get("incidents")
                or data_field.get("items")
                or []
            )
            total_records = data_field.get("total_records") or data_field.get("total") or len(alarms)
            total_pages = data_field.get("total_pages") or 1
            return alarms, total_records, total_pages
        return [], 0, 1

    # -- Connectivity --
    def test_connectivity(self) -> bool:
        """Test API connectivity by fetching a single incident."""
        self._request("GET", "incidents/v4", params={"page": 1, "limit": 1})
        return True

    # -- Incidents --
    def get_incidents_page(
        self,
        page: int = 1,
        start_date: int | None = None,
        end_date: int | None = None,
        severities: list[str] | str | None = None,
        status: str | None = None,
        alarm_main_types: list[str] | None = None,
        alarm_sub_types: list[str] | None = None,
        alarm_title: list[str] | None = None,
        tags: list[str] | None = None,
        assignees: list[str] | None = None,
        alarm_type_ids: list[int] | None = None,
        rule_ids: list[int] | None = None,
        notification_ids: list[int] | None = None,
        alarm_ids: list[int] | None = None,
        excluded_status: str | None = None,
        excluded_alarm_main_types: list[str] | None = None,
        excluded_alarm_sub_types: list[str] | None = None,
        excluded_alarm_title: list[str] | None = None,
        excluded_tags: list[str] | None = None,
        excluded_assignees: list[str] | None = None,
        excluded_alarm_type_ids: list[int] | None = None,
        include_alarm_details: bool = True,
        include_total_records: bool = True,
        limit: int = PAGE_LIMIT,
    ) -> dict[str, Any]:
        """Fetch a single page of incidents with optional filters."""
        params = {
            "page": page, "limit": min(limit, PAGE_LIMIT),
            "include_alarm_details": include_alarm_details,
            "include_total_records": include_total_records,
        }
        if start_date is not None:
            params["start_date"] = start_date
        if end_date is not None:
            params["end_date"] = end_date
        for pname, val in [
            ("severities", severities), ("alarm_main_types", alarm_main_types),
            ("alarm_sub_types", alarm_sub_types), ("alarm_title", alarm_title),
            ("tags", tags), ("assignees", assignees), ("alarm_type_ids", alarm_type_ids),
            ("rule_ids", rule_ids), ("notification_ids", notification_ids),
            ("alarm_ids", alarm_ids),
        ]:
            if val:
                params[pname] = val
        if status:
            params["status"] = status
        for pname, val in [
            ("excluded_status", excluded_status),
            ("excluded_alarm_main_types", excluded_alarm_main_types),
            ("excluded_alarm_sub_types", excluded_alarm_sub_types),
            ("excluded_alarm_title", excluded_alarm_title),
            ("excluded_tags", excluded_tags),
            ("excluded_assignees", excluded_assignees),
            ("excluded_alarm_type_ids", excluded_alarm_type_ids),
        ]:
            if val:
                params[pname] = val
        return self._request("GET", "incidents/v4", params=params)

    def get_all_incidents(self, start_date: int | None = None, end_date: int | None = None,
                          limit: int | None = None, **filters: Any) -> tuple[list[dict[str, Any]], int]:
        if end_date is None:
            end_date = int(time.time())
        first_page = self.get_incidents_page(page=1, start_date=start_date, end_date=end_date, **filters)
        first_data, total_records, total_pages = self._extract_alarms_data(first_page)

        if not first_data and total_records == 0:
            return [], 0

        # Always recalculate total_pages based on PAGE_LIMIT, since the API may
        # return total_pages based on a different default limit (e.g. 5 vs 100).
        try:
            tr = int(total_records)
            if tr > PAGE_LIMIT:
                total_pages = math.ceil(tr / PAGE_LIMIT)
            elif tr > 0:
                total_pages = 1
        except (ValueError, TypeError):
            total_pages = max(total_pages, 1)

        pages_data: dict[int, list] = {1: first_data}

        # Determine which pages to fetch — oldest alarms are on the last pages
        if limit is not None:
            needed_pages = math.ceil(limit / PAGE_LIMIT) + 1
            start_page = max(1, total_pages - needed_pages + 1)
            required_pages: set[int] = set(range(start_page, total_pages + 1))
        else:
            required_pages = set(range(1, total_pages + 1))

        for pn in sorted(required_pages):
            if pn == 1:
                continue
            try:
                resp = self.get_incidents_page(
                    page=pn, start_date=start_date, end_date=end_date, **filters
                )
                page_alarms, _, _ = self._extract_alarms_data(resp)
                pages_data[pn] = page_alarms
            except SOCRadarManagerError as e:
                raise SOCRadarManagerError(f"Failed to fetch page {pn}: {e}")
            time.sleep(0.3)

        # Build result from oldest to newest — only include required pages
        all_alarms: list = []
        for pn in range(total_pages, 0, -1):
            if pn in required_pages and pn in pages_data:
                all_alarms.extend(reversed(pages_data[pn]))
        return all_alarms, total_records

    def get_alarm_details(self, alarm_id: int | str) -> dict[str, Any]:
        """Fetch full details of a single alarm by ID.

        Raises:
            SOCRadarManagerError: If alarm is not found.
        """
        resp = self.get_incidents_page(alarm_ids=[int(alarm_id)], limit=1)
        alarms, _, _ = self._extract_alarms_data(resp)
        if not alarms:
            raise SOCRadarManagerError(f"Alarm {alarm_id} not found")
        return alarms[0]

    # -- Actions --
    def change_status(self, alarm_ids: list[str | int] | str | int, status: str | int, comments: str = "", email: str = "",
                      update_related_finding_status: bool = True) -> dict[str, Any]:
        if isinstance(status, str):
            status_code = STATUS_CODES.get(status.upper())
            if status_code is None:
                # Try parsing as numeric string (e.g. "2")
                try:
                    status_code = int(status)
                except ValueError:
                    raise SOCRadarManagerError(f"Invalid status: {status}. Valid: {list(STATUS_CODES.keys())}")
        else:
            status_code = int(status)
        if isinstance(alarm_ids, (str, int)):
            alarm_ids = [str(alarm_ids)]
        else:
            alarm_ids = [str(a) for a in alarm_ids]
        body = {"alarm_ids": alarm_ids, "status": status_code,
                "update_related_finding_status": update_related_finding_status}
        if comments:
            body["comments"] = comments
        if email:
            body["email"] = email
        return self._request("POST", "alarms/status/change", body)

    def add_comment(self, alarm_id: int | str, comment: str, user_email: str = "") -> dict[str, Any]:
        body = {"alarm_id": int(alarm_id), "comment": comment}
        if user_email:
            body["user_email"] = user_email
        return self._request("POST", "alarm/add/comment/v2", body)

    def add_tag(self, alarm_id: int | str, tag: str) -> dict[str, Any]:
        """Add a tag to an alarm. Checks current tags first to ensure idempotency.

        Raises:
            SOCRadarManagerError: If alarm details cannot be fetched or request fails.
        """
        alarm = self.get_alarm_details(alarm_id)
        current_tags = alarm.get("tags") or []
        if tag in current_tags:
            return {"is_success": True, "message": f"Tag '{tag}' is already present."}
        return self._request("POST", "alarm/tag", {"alarm_id": int(alarm_id), "tag": tag})

    def remove_tag(self, alarm_id: int | str, tag: str) -> dict[str, Any]:
        """Remove a tag from an alarm. Checks current tags first to ensure idempotency.

        Raises:
            SOCRadarManagerError: If alarm details cannot be fetched or request fails.
        """
        alarm = self.get_alarm_details(alarm_id)
        current_tags = alarm.get("tags") or []
        if tag not in current_tags:
            return {"is_success": True, "message": f"Tag '{tag}' is not present."}
        return self._request("POST", "alarm/tag", {"alarm_id": int(alarm_id), "tag": tag})

    def change_severity(self, alarm_id: int | str, severity: str) -> dict[str, Any]:
        if not isinstance(severity, str):
            raise SOCRadarManagerError("Severity must be a string")
        severity = severity.upper()
        if severity not in VALID_SEVERITIES:
            raise SOCRadarManagerError(f"Invalid severity: {severity}. Valid: {VALID_SEVERITIES}")
        return self._request("POST", "alarm/severity", {"alarm_id": int(alarm_id), "severity": severity})

    def ask_analyst(self, alarm_id: int | str, comment: str) -> dict[str, Any]:
        return self._request("POST", "incidents/ask/analyst/v2", {"alarm_id": int(alarm_id), "comment": comment})

    def get_assignee(self, alarm_id: int | str) -> dict[str, Any]:
        return self._request("GET", f"alarm/{int(alarm_id)}/assignee")

    def change_assignee(self, alarm_id: int | str, user_ids: list[int] | None = None, user_emails: list[str] | None = None) -> dict[str, Any]:
        if not user_ids and not user_emails:
            raise SOCRadarManagerError("At least user_ids or user_emails is required")
        body = {}
        if user_ids:
            body["user_ids"] = [int(uid) for uid in user_ids]
        if user_emails:
            body["user_emails"] = list(user_emails)
        return self._request("POST", f"alarm/{int(alarm_id)}/assignee", body)

    def get_assignee_options(self, alarm_id: int | str | None = None) -> dict[str, Any]:
        # Per OpenAPI spec the endpoint is company-scoped and does not accept alarm_id.
        # alarm_id kept as optional kwarg for backwards-compat with action signatures.
        return self._request("GET", "alarm/assignee_options")

    # -- IOC Feeds --
    def get_ioc_feed(self, collection_uuid: str) -> list[dict[str, Any]]:
        """Fetch IOCs from a SOCRadar Threat Feed collection.

        Uses a different URL pattern and auth mechanism than the Incident API:
        GET /threat/intelligence/feed_list/{UUID}.json?key={api_key}&v=2

        Raises:
            SOCRadarManagerError: If the feed is not found or the request fails.
        """
        url = f"{self.api_root}/threat/intelligence/feed_list/{collection_uuid}.json"
        params = {"key": self.api_key, "v": "2"}
        for attempt in range(MAX_RETRIES):
            try:
                resp = self.session.get(url, params=params, timeout=60)
                if resp.status_code == 401:
                    raise SOCRadarManagerError("Unauthorized - check your API key")
                if 400 <= resp.status_code < 500:
                    raise SOCRadarManagerError(f"Feed request error {resp.status_code} for {collection_uuid}")
                resp.raise_for_status()
                try:
                    return resp.json()
                except (ValueError, json.JSONDecodeError):
                    raise SOCRadarManagerError(f"Invalid JSON from feed {collection_uuid}")
            except requests.exceptions.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    raise SOCRadarManagerError(f"Feed request failed after {MAX_RETRIES} attempts: {e}")

    def get_multiple_ioc_feeds(self, collection_uuids: list[str]) -> dict[str, list[dict[str, Any]] | dict[str, Any]]:
        """Fetch IOCs from multiple feed collections. Returns dict keyed by UUID."""
        results = {}
        for uuid in collection_uuids:
            uuid = uuid.strip()
            if not uuid:
                continue
            try:
                results[uuid] = self.get_ioc_feed(uuid)
            except SOCRadarManagerError as e:
                results[uuid] = {"error": str(e)}
            time.sleep(0.3)
        return results

    # -- IOC Enrichment --
    def _enrichment_request(self, endpoint: str, body: dict[str, Any], ioc_api_key: str | None = None) -> dict[str, Any]:
        """Send a request to the IOC Enrichment API.

        Uses a separate API key (credit-based add-on) and a different URL
        pattern: POST /ioc_enrichment/... with header API-Key auth.
        """
        key = ioc_api_key or self.api_key
        url = f"{self.api_root}/{endpoint}"
        headers = {"API-Key": key, "Accept": "application/json",
                   "Content-Type": "application/json"}
        for attempt in range(MAX_RETRIES):
            try:
                resp = self.session.post(url, json=body, headers=headers, timeout=60)
                if resp.status_code == 401:
                    raise SOCRadarManagerError("IOC Enrichment unauthorized - check your IOC API key")
                if 400 <= resp.status_code < 500:
                    try:
                        err_data = resp.json() if resp.text else {}
                        err_msg = err_data.get("message", resp.text[:200])
                    except Exception as e:
                        err_msg = f"{resp.text[:200]} (parse error: {e})"
                    raise SOCRadarManagerError(f"Enrichment error {resp.status_code}: {err_msg}")
                resp.raise_for_status()
                try:
                    return resp.json()
                except (ValueError, json.JSONDecodeError):
                    raise SOCRadarManagerError(f"Invalid JSON from enrichment endpoint: {endpoint}")
            except requests.exceptions.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    raise SOCRadarManagerError(
                        f"Enrichment request failed after {MAX_RETRIES} attempts: {e}")

    def enrich_indicator(self, indicator: str, fields: list[str] | None = None, ioc_api_key: str | None = None) -> dict[str, Any]:
        """Enrich an indicator (IP, domain, hash, URL) via SOCRadar IOC Enrichment API.

        Args:
            indicator: The IOC value to enrich.
            fields: List of fields to request. Options:
                     indicator_details, indicator_history,
                     indicator_relations, indicator_ai_insight.
                     None returns all except AI insight.
            ioc_api_key: Separate API key for enrichment (credit-based).

        Raises:
            SOCRadarManagerError: If the request fails or API key is invalid.
        """
        body = {"indicator": indicator}
        if fields:
            body["fields"] = fields
        else:
            body["fields"] = ["indicator_details", "indicator_history", "indicator_relations"]
        return self._enrichment_request("ioc_enrichment/get/indicator_details", body, ioc_api_key)

    def enrich_indicator_stix(self, indicator: str, show_credit_details: bool = False, ioc_api_key: str | None = None) -> dict[str, Any]:
        """Enrich an indicator and return results in STIX format."""
        body = {"indicator": indicator, "show_credit_details": show_credit_details}
        return self._enrichment_request("ioc_enrichment/get/indicator_details_stix", body, ioc_api_key)

    # -- Rapid Reputation --
    def rapid_reputation(self, entity_value: str, entity_type: str, rapid_api_key: str | None = None) -> dict[str, Any]:
        """Quick reputation lookup for an entity (IP, hostname, URL, or hash).

        Uses a separate API key (add-on) and header name 'Api-Key' (not 'API-Key').
        GET /threatfeed/rapid/reputation?entity_value=X&entity_type=Y
        """
        key = rapid_api_key or self.api_key
        url = f"{self.api_root}/threatfeed/rapid/reputation"
        params = {"entity_value": entity_value, "entity_type": entity_type}
        headers = {"Api-Key": key, "Accept": "application/json"}
        for attempt in range(MAX_RETRIES):
            try:
                resp = self.session.get(url, params=params, headers=headers, timeout=30)
                if 400 <= resp.status_code < 500:
                    try:
                        err_msg = resp.json().get("message", resp.text[:200])
                    except Exception as e:
                        err_msg = f"{resp.text[:200]} (parse error: {e})"
                    raise SOCRadarManagerError(f"Rapid Reputation error {resp.status_code}: {err_msg}")
                resp.raise_for_status()
                try:
                    data = resp.json()
                except (ValueError, json.JSONDecodeError):
                    raise SOCRadarManagerError(f"Invalid JSON response from {url}")
                if isinstance(data, dict) and "is_success" in data and not data["is_success"]:
                    raise SOCRadarManagerError(f"Rapid Reputation error: {data.get('message', 'Unknown')}")
                return data
            except requests.exceptions.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    raise SOCRadarManagerError(
                        f"Rapid Reputation request failed after {MAX_RETRIES} attempts: {e}")
