from __future__ import annotations
from datetime import datetime

from greynoise.api import GreyNoise, APIConfig
from .greynoise_exceptions import ExpiredAPIKeyException
from .constants import USER_AGENT, MAX_CONNECTOR_RESULTS, GNQL_PAGE_SIZE
from .datamodels import GNQLEventResult
from TIPCommon.smp_time import is_approaching_timeout


class GreyNoiseExtended(GreyNoise):
    """
    Extended GreyNoise API client with additional endpoints.

    Extends the base GreyNoise class to add support for tag metadata retrieval.
    """

    EP_TAGS = "v3/tags/{tag_id}"

    def get_tags(self, tag_id):
        """
        Retrieve tag metadata from GreyNoise API.

        Args:
            tag_id (str): Tag identifier to retrieve metadata for.

        Returns:
            dict: Tag metadata response from GreyNoise API.
        """
        endpoint = self.EP_TAGS.format(tag_id=tag_id)
        response = self._request(endpoint)

        return response


class APIManager:
    def __init__(self, api_key, siemplify=None):
        """
        Initializes an object of the APIManager class.

        Args:
            api_key (str): API key of the GreyNoise account.
            siemplify (object, optional): An instance of the SDK SiemplifyAction class.
                Defaults to None.
        """
        self.api_key = api_key
        self.siemplify = siemplify
        api_config = APIConfig(
            api_key=api_key,
            timeout=30,
            integration_name=USER_AGENT,
        )
        self.session = GreyNoiseExtended(api_config)

    def test_connectivity(self):
        """
        Test connectivity to the GreyNoise API.

        Returns:
            bool: True if successful, exception otherwise.
        """
        res = self.session.test_connection()

        # Check if it's an expired enterprise API key
        if res["offering"] != "community":
            try:
                expires = datetime.strptime(res["expiration"], "%Y-%m-%d")
                now = datetime.today()

                if expires < now:
                    raise ExpiredAPIKeyException("Unable to auth, API Key appears to be expired")
            except (KeyError, ValueError) as e:
                self.siemplify.LOGGER.error(f"Invalid expiration date format: {e}")
                # Continue without expiration check if date is malformed

        # Valid enterprise key (expires > now) or community key
        self.siemplify.LOGGER.info(f"Connectivity Response: {res}")

        return True

    def quick_lookup(self, ip_addresses, include_invalid=False):
        """
        Perform a quick IP lookup using GreyNoise API.

        Args:
            ip_addresses (str or list): One or more IP addresses to lookup.
            include_invalid (bool): Whether to include invalid IPs in results.

        Returns:
            list: List of results from the quick lookup.
        """
        res = self.session.quick(ip_addresses, include_invalid=include_invalid)
        self.siemplify.LOGGER.info(f"Quick lookup result: {len(res)} items")
        return res

    def cve_lookup(self, cve_id):
        """
        Retrieve detailed CVE information from GreyNoise.

        Args:
            cve_id (str): CVE identifier (e.g., CVE-2024-12345)

        Returns:
            dict: CVE details response from GreyNoise API

        Raises:
            Exception: If API call fails or CVE not found
        """
        response = self.session.cve(cve_id)
        return response

    def execute_gnql_query(self, query, size=1000, exclude_raw=True, quick=False, scroll=None):
        """
        Execute a GNQL query using GreyNoise API.

        Args:
            query (str): The GNQL query string to execute.
            size (int): Number of results to return per request (max 10,000).
            exclude_raw (bool): Whether to exclude raw scan data from the response.
            quick (bool): If true, response only includes IP address and classification/trust level.
            scroll (str, optional): Scroll token for pagination (internal use).

        Returns:
            dict: Query results containing data array and request_metadata.
        """
        res = self.session.query(
            query=query, size=size, exclude_raw=exclude_raw, quick=quick, scroll=scroll
        )
        return res

    def get_tags(self, tag_id):
        """
        Retrieve tag metadata for a specific tag ID.

        Args:
            tag_id (str): Tag identifier to retrieve metadata for.

        Returns:
            dict: Tag metadata response from GreyNoise API.
        """
        res = self.session.get_tags(tag_id=tag_id)
        return res

    def ip_timeline(self, ip_address, days=30, field="classification", granularity="1d"):
        """
        Retrieve historical activity timeline for a specific IP address.

        Args:
            ip_address (str): IP address to lookup.
            days (int): Number of days to show data for. Defaults to 30.
            field (str): Field over which to show activity breakdown.
                Defaults to "classification".
            granularity (str): Granularity of activity date ranges.
                Defaults to "1d".

        Returns:
            dict: Timeline data response from GreyNoise API.
        """
        response = self.session.timeline(
            ip_address, days=days, field=field, granularity=granularity
        )
        if field.lower() == "tag_ids":
            results = response.get("results", [])
            for result in results:
                tag_id = result["label"]
                result["tag_metadata"] = self.get_tags(tag_id)
        return response

    def ip_multi(self, ip_addresses, include_invalid=True):
        """
        Perform comprehensive IP lookup for multiple IPs (Enterprise tier).

        Args:
            ip_addresses (list): List of IP addresses to lookup.
            include_invalid (bool): Include invalid IPs in results.
                Defaults to True.

        Returns:
            list: List of IP lookup results from GreyNoise API.
        """
        response = self.session.ip_multi(ip_addresses, include_invalid=include_invalid)

        self.siemplify.LOGGER.info(f"IP Multi Lookup: {len(ip_addresses)} IPs processed")
        return response

    def ip(self, ip_address):
        """
        Perform IP lookup for single IP (Community tier compatible).

        Args:
            ip_address (str): IP address to lookup.

        Returns:
            dict: IP lookup result from GreyNoise API.
        """
        response = self.session.ip(ip_address)
        self.siemplify.LOGGER.info(
            f"IP Lookup Response for {ip_address}: Found={response.get('internet_scanner_intelligence', {}).get('found', False)}"
        )
        return response

    def is_community_key(self):
        """
        Check if the API key is a community tier key.

        Returns:
            bool: True if community tier, False otherwise.
        """
        res = self.session.test_connection()
        return res.get("offering") == "community"

    def _process_gnql_page(self, data, existing_ids, events):
        """
        Process a single page of GNQL results.

        Args:
            data (list): Page data from API response.
            existing_ids (list): List of existing event IDs.
            events (list): List to append new events to.

        Returns:
            int: Number of events added from this page.
        """
        added_count = 0
        for item in data:
            event = GNQLEventResult(item)

            if event.event_id in existing_ids:
                self.siemplify.LOGGER.info(f"Skipping duplicate event: {event.event_id}")
                continue

            events.append(event)
            added_count += 1

        return added_count

    def _extract_response_data(self, response, is_first_page=False):
        """
        Extract data, complete flag, and scroll token from API response.

        Args:
            response (dict): API response from execute_gnql_query.
            is_first_page (bool): True if this is the first page of results.

        Returns:
            tuple: (data, complete, scroll_token)
        """
        data = response.get("data", [])
        request_metadata = response.get("request_metadata", {})
        complete = request_metadata.get("complete", True)
        scroll_token = request_metadata.get("scroll", "")

        if is_first_page and self.siemplify:
            total_count = request_metadata.get("count", 0)
            self.siemplify.LOGGER.info(f"Total available results: {total_count}")

        self.siemplify.LOGGER.info(f"Fetched {len(data)} events from current page.")

        return data, complete, scroll_token


    def get_gnql_events(
        self,
        query,
        page_size=GNQL_PAGE_SIZE,
        existing_ids=None,
        connector_start_time=None,
        timeout=None,
        max_results=MAX_CONNECTOR_RESULTS,
    ):
        """
        Fetch GNQL events for connector with deduplication and pagination support.

        Args:
            query (str): GNQL query string to execute.
            page_size (int): Page size for API requests. Defaults to GNQL_PAGE_SIZE (1000).
            existing_ids (list): List of existing event IDs for deduplication.
            connector_start_time (int): Unix timestamp when connector started.
            timeout (int): Timeout in seconds for connector execution.
            max_results (int): Maximum number of results to return. Defaults to MAX_CONNECTOR_RESULTS (100).

        Returns:
            list: List of GNQLEventResult objects (up to max_results).
        """
        existing_ids = existing_ids or []
        events = []
        scroll_token = None
        complete = False
        is_first_page = True

        page_size = min(page_size, max_results)

        self.siemplify.LOGGER.info(
            f"Starting GNQL query pagination with page size: {page_size}, "
            f"max results: {max_results}"
        )

        # Loop through all pages until complete or max_results reached
        while not complete:
            if is_approaching_timeout(connector_start_time, timeout):
                self.siemplify.LOGGER.info(
                    f"Timeout is approaching during pagination. "
                    f"Returning {len(events)} events collected so far."
                )
                break

            try:
                response = self.execute_gnql_query(
                    query=query,
                    size=page_size,
                    exclude_raw=True,
                    quick=False,
                    scroll=scroll_token,
                )

                data, complete, scroll_token = self._extract_response_data(
                    response, is_first_page=is_first_page
                )
                is_first_page = False
                added_count = self._process_gnql_page(data, existing_ids, events)

                # Break if max results reached
                if len(events) >= max_results:
                    self.siemplify.LOGGER.info(
                        f"Reached max results limit of {max_results}, stopping pagination."
                    )
                    break

                # Break if no more data or complete
                if complete or not scroll_token or len(data) == 0:
                    break

            except Exception as e:
                self.siemplify.LOGGER.error(f"Error occurred while subsequent pages: {str(e)}")
                self.siemplify.LOGGER.exception(e)
                self.siemplify.LOGGER.info(f"Returning {len(events)} events collected before the error.")
                break

        if len(events) > max_results:
            events = events[:max_results]

        self.siemplify.LOGGER.info(f"Returning {len(events)} new events after deduplication and pagination.")

        return events
