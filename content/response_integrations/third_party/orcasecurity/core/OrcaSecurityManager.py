from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urljoin

import requests

from .constants import (
    DEFAULT_RESULTS_LIMIT,
    ENDPOINTS,
    POSSIBLE_SEVERITIES,
    WHITELIST_FILTER,
)
from .OrcaSecurityParser import OrcaSecurityParser
from .query_builder import AlertQueryBuilder, AssetQueryBuilder
from .UtilsManager import validate_response

if TYPE_CHECKING:
    from typing import Any

    from soar_sdk.SiemplifyLogger import SiemplifyLogger

    from .datamodels import Alert, AlertComment, Asset, Framework, ScanStatus


class OrcaSecurityManager:
    def __init__(
        self,
        api_root: str,
        api_key: str,
        api_token: str,
        verify_ssl: bool,
        ui_root: str | None = "",
        siemplify_logger: SiemplifyLogger = None,
    ) -> None:
        """Initialize an OrcaSecurityManager instance and configure authentication.

        Args:
            api_root (str): Base URL of the OrcaSecurity API.
            api_key (str): OrcaSecurity API key (used if token is not provided).
            api_token (str): OrcaSecurity API token (preferred authentication method).
            verify_ssl (bool): Whether to validate the SSL certificate of the API root.
            ui_root (str): Base URL of the OrcaSecurity UI. Defaults to "".
            siemplify_logger (SiemplifyLogger): Logger instance for logging.
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.api_key = api_key
        self.api_token = api_token
        self.verify_ssl = verify_ssl
        self.ui_root = ui_root
        self.siemplify_logger = siemplify_logger
        self.parser = OrcaSecurityParser()
        self.session = requests.Session()
        self.session.verify = verify_ssl
        if self.api_token:
            self.session.headers = {"Authorization": f"Token {self.api_token}"}
        elif self.api_key:
            self.set_auth_cookies()
        else:
            raise Exception(
                'Either "API Key" or "API Token" needs to be provided for authentication.'
            )

    def _get_full_url(self, url_id: str, **kwargs) -> str:
        """Build the full API URL for a given endpoint identifier.

        Args:
            url_id (str): The endpoint identifier key.
            **kwargs: Variables used for string formatting in the URL.

        Returns:
            str: The fully constructed API URL.
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def set_auth_cookies(self) -> None:
        """Set authentication cookies for the session.
        Sends a login request using the API key, validates the response,
        and updates the session with the required cookies.
        """
        url = self._get_full_url("login")
        params = {"security_token": self.api_key}

        response = self.session.get(url, params=params, allow_redirects=False)
        validate_response(response)

        for cookie in response.cookies:
            if cookie.name == "csrftoken":
                self.session.cookies.update({"csrftoken": cookie.value})
            if cookie.name == "sessionid":
                self.session.cookies.update({"sessionid": cookie.value})

    def test_connectivity(self) -> None:
        """Test connectivity to the OrcaSecurity API."""
        payload = {"limit": 1}
        url = self._get_full_url("vulnerability_details")
        response = self.session.post(url, json=payload)
        validate_response(response)

    def get_alerts(
        self,
        start_timestamp: int,
        limit: int,
        lowest_severity: str | None = None,
        categories: list[str] | None = None,
        title_filter: list[str] | None = None,
        title_filter_type: int | None = WHITELIST_FILTER,
        alert_types: list[str] | None = None,
        lowest_score: float | None = None,
    ) -> list[Alert]:
        """Retrieve alerts from the API.
        Builds an alert query payload with the provided filters (severity, categories,
        title, type, score, etc.), sends it to the alerts endpoint, validates the
        response, and parses it into a list of Alert objects.

        Args:
            start_timestamp (int): The start timestamp in milliseconds to fetch alerts.
            limit (int): The maximum number of alerts to fetch.
            lowest_severity (str): The lowest severity to filter by.
            categories (list[str]): List of categories to filter by.
            title_filter (list[str]): List of titles to filter by.
            title_filter_type (int): The type of title filter, either WHITELIST_FILTER
            or BLACKLIST_FILTER. Defaults to WHITELIST_FILTER.
            alert_types (list[str]): List of alert types to filter by.
            lowest_score (float): The lowest score to filter by.

        Returns:
            list[Alert]: List of Alert objects.
        """
        url: str = self._get_full_url("get_alerts")
        payload: AlertQueryBuilder = (
            AlertQueryBuilder(start_timestamp, limit)
            .with_severity(lowest_severity)
            .with_categories(categories)
            .with_title_filter(title_filter, title_filter_type)
            .with_alert_types(alert_types)
            .with_score(lowest_score)
            .build()
        )

        response: requests.Response = self.session.post(url, json=payload)
        validate_response(response)
        return self.parser.build_alert_objects(response.json())

    def verify_alert(self, alert_id: str) -> None:
        """Verify an alert in OrcaSecurity by its ID.

        Args:
            alert_id (str): The identifier of the alert to verify.
        """
        url = self._get_full_url("verify_alert", alert_id=alert_id)
        response = self.session.put(url)
        validate_response(response)

    def snooze_alert(self, alert_id: str, snooze_days: int) -> None:
        """Snooze an alert for a given number of days.

        Args:
            alert_id (str): The identifier of the alert to snooze.
            snooze_days (int): Number of days to snooze the alert.
        """
        url = self._get_full_url("snooze_alert", alert_id=alert_id)
        payload = {"days": snooze_days}

        response = self.session.put(url, json=payload)
        validate_response(response)

    def update_alert_status(self, alert_id: str, status: int) -> None:
        """Update the status of an alert.

        Args:
            alert_id (str): The identifier of the alert to update.
            status (int): The status value to set for the alert.
        """
        url = self._get_full_url("update_alert_status", alert_id=alert_id, status=status)
        response = self.session.put(url)
        validate_response(response)

    def get_alert_data(self, alert_id: str) -> Alert:
        """Retrieve detailed alert data for a specific alert ID.
        Builds a query for the given alert ID, posts it to the alerts endpoint,
        validates the response, and parses the result into an Alert object.

        Args:
            alert_id (str): Identifier of the alert to fetch.

        Returns:
            Alert: Parsed alert object returned by the API.
        """
        url: str = self._get_full_url("get_alerts")
        payload: AlertQueryBuilder = AlertQueryBuilder().with_alert_id(alert_id).build()

        response: requests.Response = self.session.post(url, json=payload)
        validate_response(response)
        return self.parser.build_alert_objects(response.json())[0]

    def add_alert_comment(self, alert_id: str, comment: str) -> AlertComment:
        """Add a comment to a specific alert.

        Args:
            alert_id (str): The identifier of the alert to comment on.
            comment (str): The comment text to add to the alert.

        Returns:
            AlertComment: The AlertComment object created for the alert.
        """
        url = self._get_full_url("add_alert_comment", alert_id=alert_id)
        payload = {"comment": comment}

        response = self.session.put(url, json=payload)
        validate_response(response)
        return self.parser.build_alert_comment_object(response.json())

    def get_frameworks(
        self,
        framework_names: list[str],
        limit: int,
    ) -> tuple[list[Framework], list[str]]:
        """Retrieve frameworks by their names.

        Args:
            framework_names (list[str]): List of framework names to retrieve.
            limit (int): Maximum number of results to return.

        Returns:
            tuple[list[Framework], list[str]]:
                List of Framework objects that were found.
                List of framework names that were not found.
        """
        url = self._get_full_url("get_frameworks")
        response = self.session.post(url)
        validate_response(response)
        return self.filter_frameworks(
            self.parser.build_framework_objects(response.json()), framework_names, limit
        )

    @staticmethod
    def filter_frameworks(
        frameworks: list[Framework],
        framework_names: list[str] | None,
        limit: int | None,
    ) -> tuple[list[Framework], list[str]]:
        """Filter a list of frameworks by specified names and apply a limit.

        Args:
            frameworks (list[Framework]): List of Framework objects to filter.
            framework_names (list[str] | None): Names to filter the frameworks by.
            limit (int | None): Maximum number of frameworks to return.

        Returns:
            tuple[list[Framework], list[str]]:
                Filtered list of Framework objects.
                List of framework names that were not found in the provided frameworks.
        """
        if framework_names:
            filtered_frameworks = [
                framework for framework in frameworks if framework.display_name in framework_names
            ]
            not_found_frameworks = list(
                set(framework_names)
                - set([framework.display_name for framework in filtered_frameworks])
            )
        else:
            filtered_frameworks = frameworks
            not_found_frameworks = []

        return (filtered_frameworks[:limit] if limit else filtered_frameworks), not_found_frameworks

    def start_scan(self, asset_id: str) -> ScanStatus:
        """Start a scan for a specific asset.

        Args:
            asset_id (str): The identifier of the asset to scan.

        Returns:
            ScanStatus: The ScanStatus object representing the scan initiation status.
        """
        url = self._get_full_url("start_scan", asset_id=asset_id)
        response = self.session.post(url)
        validate_response(response)
        return self.parser.build_scan_status_object(response.json())

    def get_scan_status(self, scan_id: str) -> ScanStatus:
        """Retrieve the status of a scan by its ID.

        Args:
            scan_id (str): The identifier of the scan.

        Returns:
            ScanStatus: The ScanStatus object representing the current scan status.
        """
        url = self._get_full_url("get_scan_status", scan_id=scan_id)
        response = self.session.get(url)
        validate_response(response)
        return self.parser.build_scan_status_object(response.json())

    def get_vulnerability_results(
        self,
        cve_id: str,
        limit: int | None = None,
        create_insight: bool = False,
    ) -> list[Any]:
        """Retrieve vulnerability results for a given CVE ID.

        Builds a query to fetch vulnerabilities matching the CVE ID, applies optional
        result limits, and optionally prepares data for insight generation.

        Args:
            cve_id (str): The CVE identifier to query.
            limit (int): Maximum number of results to return.
            create_insight (bool): Whether to generate full insight data.

        Returns:
            list[Any]: A list containing:
                The filtered vulnerability results (limited if `limit` is set).
                Full insight data if `create_insight` is True, otherwise None.
        """
        payload = {
            "dsl_filter": {
                "filter": [{"field": "cve_id", "includes": [cve_id]}],
                "sort": [{"field": "severity", "order": "desc"}],
            }
        }

        results = self._paginate_results(
            method="POST",
            url=self._get_full_url("vulnerability_details"),
            body=payload,
            limit=limit,
        )
        enrichment_data = self.parser.build_results(
            raw_json=results[:limit], pure_data=True, method="build_cve_object"
        )
        return_list = [enrichment_data, None]
        if create_insight:
            # for insight generation whole data is required
            insight_data = self.parser.build_results(
                raw_json=results, pure_data=True, method="build_cve_object"
            )
            return_list[1] = insight_data
        return return_list

    def get_asset_details(self, asset_id: str) -> Asset:
        """Get asset details by asset unique ID.

        Args:
            asset_id (str): The asset unique ID.

        Returns:
            Asset: The Asset object.
        """
        url: str = self._get_full_url("asset_details")
        payload: AssetQueryBuilder = AssetQueryBuilder().with_asset_id(asset_id).build()

        response: requests.Response = self.session.post(url, json=payload)
        validate_response(response)

        return self.parser.build_asset_object(response.json())

    def get_vulnerability_details(
        self,
        asset_id: str,
        severity: str,
        limit: int | None = None,
    ) -> list[Any]:
        """Retrieve vulnerability details for a specific asset filtered by severity.

        Builds a query to fetch vulnerabilities for the given asset ID, filters by
        severity, applies an optional limit, and returns the parsed results.

        Args:
            asset_id (str): The unique identifier of the asset.
            severity (str): The lowest severity value to include in results.
            limit (int): Maximum number of results to return. Defaults to None.

        Returns:
            list[Any]: List of parsed vulnerability objects.
        """
        payload = {
            "dsl_filter": {
                "filter": [{"field": "asset_unique_id", "includes": [asset_id]}],
                "sort": [{"field": "score", "order": "desc"}],
            },
            "limit": limit,
            "start_at_index": 0,
            "grouping": True,
        }

        if severity:
            payload.get("dsl_filter").get("filter").append({
                "field": "severity",
                "includes": POSSIBLE_SEVERITIES[: POSSIBLE_SEVERITIES.index(severity.lower()) + 1],
            })

        response = self.session.post(self._get_full_url("vulnerability_details"), json=payload)
        validate_response(response)

        return self.parser.build_results(raw_json=response.json(), method="build_cve_object")

    def _paginate_results(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        limit: int | None = None,
        err_msg: str = "Unable to get results",
    ) -> list[Any]:
        """Paginate through API results and return a consolidated list.

        Sends repeated requests if a next page token is returned, accumulating
        all results into a single list.

        Args:
            method (str): HTTP method to use for the request (GET, POST, etc.).
            url (str): The URL to send the request to.
            params (dict, optional): Query parameters for the request. Defaults to None.
            body (dict, optional): JSON payload for the request. Defaults to None.
            limit (int, optional): Maximum number of results to fetch.
            err_msg (str, optional): Error message to display if request fails.

        Returns:
            list[Any]: List of results returned by the API across all pages.
        """
        if body is None:
            body = {}

        body.update({"limit": limit or DEFAULT_RESULTS_LIMIT})

        response = self.session.request(method, url, params=params, json=body)

        validate_response(response, err_msg)
        json_response = response.json()
        results = json_response.get("data", [])
        next_page_token = json_response.get("next_page_token", "")

        while next_page_token:
            body.update({"next_page_token": next_page_token})

            response = self.session.request(method, url, params=params, json=body)
            validate_response(response, err_msg)
            json_response = response.json()
            next_page_token = json_response.get("next_page_token", "")
            results.extend(json_response.get("data", []))
        return results
