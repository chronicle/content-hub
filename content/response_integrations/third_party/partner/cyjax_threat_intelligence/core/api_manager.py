from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import requests

from .constants import (
    CYJAX_API_BASE_URL,
    CYJAX_API_VERSION,
    DEFAULT_REQUEST_TIMEOUT,
    DOMAIN_MONITOR_ENDPOINT,
    ENRICH_IOC_ENDPOINT,
    FIRST_RETRY_DELAY,
    LIST_DATA_BREACH_ENDPOINT,
    MAX_RECORDS_LIMIT,
    PING_ENDPOINT,
    RETRY_COUNT,
    SECOND_RETRY_DELAY,
)
from .cyjax_exceptions import (
    CyjaxException,
    InternalServerError,
    ItemNotFoundException,
    RateLimitException,
    UnauthorizedException,
)


class APIManager:
    def __init__(
        self,
        siemplify,
        api_token: str,
        verify_ssl: bool = False,
    ) -> None:
        """
        Initializes an object of the APIManager class.

        Args:
            api_token (str): API Token for authentication.
            verify_ssl (bool, optional): If True, verify the SSL certificate. Defaults to False.
            siemplify (object, optional): An instance of the SDK SiemplifyAction class. 
                                          Defaults to None.
        """
        self.base_url = CYJAX_API_BASE_URL.format(api_version=CYJAX_API_VERSION)
        if api_token and not api_token.strip():
            raise ValueError("API Token cannot be empty.")
        self.api_token = api_token.strip()
        self.siemplify = siemplify
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_token}",
        })

    def _make_rest_call(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        retry_count: int = RETRY_COUNT,
    ) -> requests.Response:
        """
        Make a REST call to the Cyjax API with retry logic.

        Args:
            method (str): HTTP method (GET, POST, DELETE, etc.)
            endpoint (str): API endpoint path
            params (dict, optional): Query parameters
            json_body (dict, optional): JSON body for POST/PUT requests
            retry_count (int, optional): Number of retries for rate limit. Defaults to RETRY_COUNT.

        Returns:
            requests.Response: Response object

        Raises:
            RateLimitException: If rate limit is exceeded after retries
            UnauthorizedException: If authentication fails
            InternalServerError: If server error occurs
        """
        url = f"{self.base_url}{endpoint}"

        for attempt in range(retry_count):
            try:
                response = self.session.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    timeout=DEFAULT_REQUEST_TIMEOUT,
                )

                if response.status_code == 200:
                    return response
                elif response.status_code == 401:
                    raise UnauthorizedException(
                        "Invalid credentials provided. Please enter valid credentials."
                    )
                elif response.status_code == 403:
                    raise UnauthorizedException("Access denied. Please check your permissions.")
                elif response.status_code == 429:
                    if attempt < retry_count - 1:
                        delay = FIRST_RETRY_DELAY if attempt == 0 else SECOND_RETRY_DELAY
                        self.siemplify.LOGGER.warn(
                            f"Rate limit hit (429). Retrying in {delay} seconds... "
                            f"(Attempt {attempt + 1}/{retry_count})"
                        )
                        time.sleep(delay)
                        continue
                    raise RateLimitException(
                        "Rate limit hit. Max retries exceeded."
                        " Please check your network connection and try again later."
                    )
                elif response.status_code == 404:
                    raise ItemNotFoundException("Resource not found.")
                elif response.status_code >= 500:
                    if attempt < retry_count - 1:
                        delay = FIRST_RETRY_DELAY if attempt == 0 else SECOND_RETRY_DELAY
                        self.siemplify.LOGGER.warn(
                            f"Server error ({response.status_code}). Retrying in {delay}"
                            f" seconds... (Attempt {attempt + 1}/{retry_count})"
                        )
                        time.sleep(delay)
                        continue
                    raise InternalServerError(
                        "Max retries exceeded."
                        " Please check your network connection and try again later."
                    )
                else:
                    response.raise_for_status()
                    return response

            except requests.exceptions.HTTPError as e:
                error_msg = str(e)
                response_obj = getattr(e, "response", None)
                response_details = ""

                if response_obj is not None:
                    response_details = self._get_response_error_details(response_obj)

                if response_details:
                    error_msg = f"{error_msg} Details: {response_details}"

                raise CyjaxException(error_msg)
            except requests.exceptions.RequestException as e:
                error_msg = str(e)
                if "http" in error_msg.lower():
                    raise CyjaxException(f"Request failed: {error_msg}")
                raise

        return response

    def _get_response_error_details(self, response: requests.Response) -> str:
        """Extract user-friendly error details from a failed HTTP response."""
        try:
            payload = response.json()
        except ValueError:
            return response.text or ""

        details: List[str] = []

        # Try to extract message from common error response formats
        message = payload.get("message") or payload.get("error") or payload.get("detail")
        if message:
            details.append(f"Message: {message}")

        status_code = payload.get("status_code") or response.status_code
        if status_code:
            details.append(f"Status Code: {status_code}")

        if not details:
            return response.text or ""

        return " | ".join(details)

    def ping(self) -> bool:
        """
        Test connectivity to the Cyjax API.

        Returns:
            bool: True if successful

        Raises:
            Exception: If connectivity test fails
        """
        params = {"per-page": 1}
        _ = self._make_rest_call("GET", PING_ENDPOINT, params=params)
        return True

    def _paginate_results(
        self,
        endpoint: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generic pagination function to fetch all results up to 1000 records.

        Args:
            endpoint (str): API endpoint to call
            params (dict): Base query parameters (will be updated with page and per-page)

        Returns:
            dict: Dictionary containing:
                - results (list): List of results (max 1000)
                - total_fetched (int): Total number of records fetched
                - limit_reached (bool): True if 1000 record limit was reached
                - partial_error (str): Error message if pagination stopped due to 429/5xx error
        """
        all_results = []
        page = 1
        per_page = 100
        limit_reached = False
        partial_error = None

        while len(all_results) < MAX_RECORDS_LIMIT:
            # Update params with pagination info
            current_params = params.copy()
            current_params["page"] = page
            current_params["per-page"] = per_page

            self.siemplify.LOGGER.info(f"Fetching page {page} with {per_page} records per page")

            try:
                response = self._make_rest_call("GET", endpoint, params=current_params)
                page_results = response.json()
            except (RateLimitException, InternalServerError) as e:
                if page > 1:
                    self.siemplify.LOGGER.error(
                        f"Stopping pagination due to error on page {page}: {e}"
                    )
                    partial_error = str(e)
                    break
                raise e

            if not page_results:
                self.siemplify.LOGGER.info(
                    f"No more results found on page {page}. Stopping pagination."
                )
                break

            all_results.extend(page_results)
            self.siemplify.LOGGER.info(
                f"Fetched {len(page_results)} records from page {page}."
                f" Total so far: {len(all_results)}"
            )

            if len(all_results) >= MAX_RECORDS_LIMIT:
                all_results = all_results[:MAX_RECORDS_LIMIT]
                limit_reached = True
                self.siemplify.LOGGER.info(f"Reached maximum limit of {MAX_RECORDS_LIMIT} records")
                break

            if len(page_results) < per_page:
                self.siemplify.LOGGER.info(
                    f"Received {len(page_results)} results. No more pages available."
                )
                break

            page += 1

        return {
            "results": all_results,
            "total_fetched": len(all_results),
            "limit_reached": limit_reached,
            "partial_error": partial_error,
        }

    def process_enrich_iocs(self, entity_objects: List[str]) -> Dict[str, Any]:
        """
        Process IOC enrichment for multiple IOCs and enrich entities.

        Args:
            ioc_values (list): List of IOC values to enrich
            entities_object (list): List of Siemplify entity objects to enrich

        Returns:
            dict: Processed results with enriched_results, failed_iocs, not_found_iocs"""

        enriched_results = []
        failed_iocs = []
        not_found_iocs = []

        for entity in entity_objects:
            entity_identifier = entity.identifier
            try:
                self.siemplify.LOGGER.info(f"Enriching IOC: {entity_identifier}")
                params = {"value": entity_identifier}
                resp = self._make_rest_call("GET", ENRICH_IOC_ENDPOINT, params=params)
                response = resp.json()
                if isinstance(response, dict):
                    if response.get("code") == 404:
                        not_found_iocs.append(entity_identifier)
                        continue
                    response["ioc"] = entity_identifier
                enriched_results.append(response)
                self.siemplify.LOGGER.info(
                    f"Successfully enriched IOC: {entity_identifier}"
                )
            except ItemNotFoundException:
                not_found_iocs.append(entity_identifier)
                continue
            except UnauthorizedException as e:
                raise UnauthorizedException(str(e))
            except Exception as e:
                self.siemplify.LOGGER.warn(f"Failed to enrich IOC {entity_identifier}: {str(e)}")
                failed_iocs.append(entity_identifier)

        return {
            "enriched_results": enriched_results,
            "failed_iocs": failed_iocs,
            "not_found_iocs": not_found_iocs,
        }

    def process_domain_monitor(
        self,
        query: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process domain monitor request with automatic pagination up to 1000 records.

        Args:
            query (str, optional): Domain query
            since (str, optional): Start date
            until (str, optional): End date

        Returns:
            dict: Dictionary containing:
                - results (list): List of domain monitor results (max 1000)
                - total_fetched (int): Total number of records fetched
                - limit_reached (bool): True if 1000 record limit was reached
        """
        params: Dict[str, Any] = {}

        if query:
            params["query"] = query
        if since:
            params["since"] = since
        if until:
            params["until"] = until

        return self._paginate_results(DOMAIN_MONITOR_ENDPOINT, params)

    def process_data_breaches(
        self,
        query: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List all data breaches from Cyjax with automatic pagination up to 1000 records.

        Args:
            query (str, optional): Search query to filter breaches
            since (str, optional): Start date
            until (str, optional): End date

        Returns:
            dict: Dictionary containing:
                - results (list): List of data breach results (max 1000)
                - total_fetched (int): Total number of records fetched
                - limit_reached (bool): True if 1000 record limit was reached
        """
        params: Dict[str, Any] = {}

        if query:
            params["query"] = query
        if since:
            params["since"] = since
        if until:
            params["until"] = until

        return self._paginate_results(LIST_DATA_BREACH_ENDPOINT, params)
