from __future__ import annotations

import json
import sys
import time
import urllib.parse
from typing import Any, Dict, List, Optional

import requests

from .censys_exceptions import (
    CensysException,
    InternalServerError,
    PartialDataException,
    RateLimitException,
    UnauthorizedErrorException,
    ValidationException,
)
from .constants import (
    API_ROOT,
    DEFAULT_REQUEST_TIMEOUT,
    ENDPOINTS,
    ENRICH_CERTIFICATES_ACTION_IDENTIFIER,
    ENRICH_IPS_ACTION_IDENTIFIER,
    ENRICH_WEB_PROPERTIES_ACTION_IDENTIFIER,
    GET_HOST_HISTORY_ACTION_IDENTIFIER,
    GET_RESCAN_STATUS_ACTION_IDENTIFIER,
    INITIATE_RESCAN_ACTION_IDENTIFIER,
    INTEGRATION_VERSION,
    INTERNAL_SERVER_ERROR_STATUS_CODES,
    IOC_TYPE_SERVICE_ID,
    IOC_TYPE_WEB_ORIGIN,
    MAX_PAGINATION_CALLS,
    MAX_PAYLOAD_SIZE_BYTES,
    MAX_RECORD_THRESHOLD,
    PING_ACTION_IDENTIFIER,
    RATE_LIMIT_EXCEEDED_STATUS_CODE,
    RETRY_COUNT,
    UNAUTHORIZED_STATUS_CODE,
    VALIDATION_ERROR_STATUS_CODES,
    WAIT_TIME_FOR_RETRY,
)
from .utils import HandleExceptions


class APIManager:
    def __init__(
        self,
        api_key: str,
        organization_id: str,
        verify_ssl: bool = False,
        siemplify: Optional[Any] = None,
    ) -> None:
        """Initialize the APIManager with API key authentication.

        Args:
            api_key: Censys API Key
            organization_id: Censys Organization ID
            verify_ssl: Whether to verify SSL certificates
            siemplify: Chronicle SOAR SDK instance for logging
        """
        self.siemplify = siemplify
        self.api_root = API_ROOT
        self.api_key = api_key
        self.organization_id = organization_id
        self.verify_ssl = verify_ssl

        # Build User-Agent header
        google_secops_version = siemplify.get_system_version() if siemplify else "Unknown"
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        epoch_time = int(time.time())
        user_agent = (
            f"CensysGoogleSecopsSOAR/{INTEGRATION_VERSION} "
            f"(GoogleSecopsSOAR/{google_secops_version}; "
            f"Python/{python_version}; "
            f"ts={epoch_time})"
        )

        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": user_agent,
        })

    def _get_full_url(self, url_id: str, **kwargs: Any) -> str:
        """Get full URL from URL identifier.

        Args:
            url_id: The ID of the URL
            kwargs: Variables passed for string formatting

        Returns:
            str: The full URL
        """
        return urllib.parse.urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def _make_rest_call(
        self,
        api_identifier: str,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        data: Optional[str] = None,
        retry_count: int = RETRY_COUNT,
    ) -> Dict[str, Any]:
        """Make a REST call to the Censys API with automatic retry logic.

        Args:
            api_identifier: API action identifier for logging
            method: HTTP method (GET, POST, etc.)
            url: Target URL
            params: URL parameters (organization_id will be automatically added)
            body: JSON payload
            data: Raw data payload
            retry_count: Number of retries for rate limiting/auth errors

        Returns:
            JSON response as dictionary

        Raises:
            RateLimitException: If max retries exceeded
            UnauthorizedErrorException: If auth fails
            CensysException: For other errors
        """
        # Always add organization_id as query parameter
        if params is None:
            params = {}
        params["organization_id"] = self.organization_id

        request_kwargs = {"params": params, "timeout": DEFAULT_REQUEST_TIMEOUT}
        if data:
            request_kwargs["data"] = data
        elif body:
            request_kwargs["json"] = body

        response = self.session.request(method, url, verify=self.verify_ssl, **request_kwargs)

        try:
            self.validate_response(api_identifier, response)
        except (RateLimitException, InternalServerError):
            if retry_count > 0:
                time.sleep(WAIT_TIME_FOR_RETRY)
                return self._make_rest_call(
                    api_identifier, method, url, params, body, data, retry_count - 1
                )
            raise RateLimitException(
                "Max retries exceeded. Please check your network connection and try again later."
            )
        except UnauthorizedErrorException:
            raise UnauthorizedErrorException(
                "Unauthorized, please verify your API Key and Organization ID."
            )

        try:
            return response.json()
        except Exception:
            self.siemplify.LOGGER.error(
                f"Exception occurred while parsing response JSON for {api_identifier} and URL {url}"
            )
            return {}

    def validate_response(
        self,
        api_identifier: str,
        response: requests.Response,
        error_msg: str = "An error occurred",
    ) -> bool:
        """Validate API response for HTTP errors.

        Args:
            api_identifier: API action identifier
            response: HTTP response object
            error_msg: Custom error message

        Returns:
            True if response is valid

        Raises:
            ValidationException: If input validation fails (400, 422)
            RateLimitException: If API rate limit exceeded
            UnauthorizedErrorException: If authentication failed
            InternalServerError: If server error occurred
            CensysException: For other errors
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            if response.status_code == UNAUTHORIZED_STATUS_CODE:
                raise UnauthorizedErrorException()
            if response.status_code == RATE_LIMIT_EXCEEDED_STATUS_CODE:
                raise RateLimitException("API rate limit exceeded")
            if response.status_code in VALIDATION_ERROR_STATUS_CODES:
                error_detail = self._parse_validation_error(response)
                raise ValidationException(error_detail)
            if response.status_code in INTERNAL_SERVER_ERROR_STATUS_CODES:
                raise InternalServerError(f"Internal server error: {response.status_code}")
            HandleExceptions(api_identifier, error, response, error_msg).do_process()
        except (
            ValidationException,
            UnauthorizedErrorException,
            RateLimitException,
            InternalServerError,
        ):
            raise
        except Exception as e:
            self.siemplify.LOGGER.error(f"Error validating response: {str(e)}")
            raise CensysException(f"{str(e)}")

        return True

    def _parse_validation_error(self, response: requests.Response) -> str:
        """Parse validation error details from response.

        Args:
            response: HTTP response object

        Returns:
            Formatted error message with validation details
        """
        raw_response = response.text

        try:
            error_data = response.json()

            # Handle Censys API validation error format (422)
            if "errors" in error_data and isinstance(error_data["errors"], list):
                error_messages = []
                for err in error_data["errors"]:
                    msg = err.get("message", "")
                    location = err.get("location", "")
                    if msg:
                        error_messages.append(f"{msg} (location: {location})" if location else msg)

                detail = error_data.get("detail", "Validation failed")
                if error_messages:
                    return f"{detail}: {'; '.join(error_messages)}"
                return detail

            # Handle generic error format with "error" object
            if "error" in error_data:
                error_obj = error_data["error"]
                message = error_obj.get("message", "")
                reason = error_obj.get("reason", "")
                if message and reason:
                    return f"{message} - {reason}"
                return message or reason or "Validation error"

            # Fallback to detail or title
            if "detail" in error_data or "title" in error_data:
                return error_data.get("detail", error_data.get("title", "Validation error"))

            # Unknown format - return raw response for debugging
            self.siemplify.LOGGER.info(
                f"Unknown validation error format. Raw response: {raw_response}"
            )
            return f"Validation error. Response: {raw_response}"

        except Exception as e:
            # Failed to parse JSON - return raw response
            self.siemplify.LOGGER.info(
                f"Failed to parse validation error JSON: {e}. Raw response: {raw_response}"
            )
            return f"Validation error. Response: {raw_response}"

    def test_connectivity(self) -> bool:
        """Test connectivity to the Censys API.

        Returns:
            bool: True if connection is successful, raises exception otherwise.

        Raises:
            CensysException: If there's an error in the API response.
        """
        url = self._get_full_url(PING_ACTION_IDENTIFIER, organization_id=self.organization_id)

        self._make_rest_call(PING_ACTION_IDENTIFIER, "GET", url)

        return True

    def initiate_rescan(
        self,
        ioc_type: str,
        ioc_value: str,
        port: int,
        protocol: Optional[str] = None,
        transport_protocol: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Initiate a live rescan for a known host service.

        Args:
            ioc_type: Type of IOC (Service or Web Origin)
            ioc_value: IP address or domain name
            port: Port number
            protocol: Service protocol (required for Service)
            transport_protocol: Transport protocol (required for Service)

        Returns:
            Dict containing scan ID and task information

        Raises:
            CensysException: If there's an error in the API response
        """
        url = self._get_full_url(INITIATE_RESCAN_ACTION_IDENTIFIER)

        # Build request body based on IOC type
        if ioc_type == IOC_TYPE_SERVICE_ID:
            body = {
                "target": {
                    "service_id": {
                        "ip": ioc_value,
                        "port": port,
                        "protocol": protocol,
                        "transport_protocol": transport_protocol.lower(),
                    }
                }
            }
        elif ioc_type == IOC_TYPE_WEB_ORIGIN:
            body = {
                "target": {
                    "web_origin": {
                        "hostname": ioc_value,
                        "port": port,
                    }
                }
            }
        else:
            raise CensysException(f"Invalid IOC Type: {ioc_type}")

        response = self._make_rest_call(
            INITIATE_RESCAN_ACTION_IDENTIFIER,
            "POST",
            url,
            body=body,
        )

        return response

    def get_rescan_status(self, scan_id: str) -> Dict[str, Any]:
        """Get the current status of a scan by its ID.

        Args:
            scan_id: The unique identifier of the tracked scan

        Returns:
            Dict containing scan status, tasks, and completion information

        Raises:
            CensysException: If there's an error in the API response
        """
        url = self._get_full_url(GET_RESCAN_STATUS_ACTION_IDENTIFIER, scan_id=scan_id)

        response = self._make_rest_call(
            GET_RESCAN_STATUS_ACTION_IDENTIFIER,
            "GET",
            url,
        )

        return response

    def get_host_history(
        self,
        host_id: str,
        start_time: str,
        end_time: str,
    ) -> Dict[str, Any]:
        """Get the event history for a host (IP address) with time-based pagination.

        The API uses reversed time semantics:
        - start_time (API param) = newer/closer to now (UI "To" date)
        - end_time (API param) = older/further back (UI "From" date)

        User provides:
        - start_time = past time (UI "From" date)
        - end_time = current/recent time (UI "To" date)

        We validate start_time < end_time, then reverse them when calling the API.

        Pagination uses scanned_to as cursor. Max 1000 records.

        Args:
            host_id: The IP address of the host
            start_time: Start time from the past (RFC3339 format) - will be reversed to API end_time
            end_time: End time near current (RFC3339 format) - will be reversed to API start_time

        Returns:
            Dict containing host event history with all paginated events (max 1000)

        Raises:
            ValueError: If start_time >= end_time
            CensysException: If there's an error in the API response
        """
        url = self._get_full_url(GET_HOST_HISTORY_ACTION_IDENTIFIER, host_id=host_id)

        # Validate that start_time < end_time (chronological order)
        if start_time >= end_time:
            raise ValueError(
                f"Invalid time range: start_time ({start_time}) must be earlier than "
                f"end_time ({end_time}). Please provide start_time from the past and "
                f"end_time closer to the current time."
            )

        all_events = []
        total_fetched = 0
        max_records = MAX_RECORD_THRESHOLD
        max_pages = MAX_PAGINATION_CALLS
        page_count = 0
        current_payload_size = 0
        truncation_reason = None

        # Reverse the times for API call (API expects reverse chronological order)
        # User's end_time (recent) -> API start_time (newer)
        # User's start_time (past) -> API end_time (older)
        api_start_time = end_time
        api_end_time = start_time

        self.siemplify.LOGGER.info(
            f"Fetching host history with time-based pagination. "
            f"User input (chronological): {start_time} to {end_time}. "
            f"API call (reversed): start_time={api_start_time}, end_time={api_end_time}"
        )

        while page_count < max_pages and total_fetched < max_records:
            page_count += 1
            params = {
                "start_time": api_start_time,
                "end_time": api_end_time,
            }

            try:
                response = self._make_rest_call(
                    GET_HOST_HISTORY_ACTION_IDENTIFIER,
                    "GET",
                    url,
                    params=params,
                )
            except (RateLimitException, InternalServerError, CensysException) as e:
                # If we have collected some data, raise PartialDataException
                if all_events:
                    error_type = type(e).__name__
                    error_message = str(e)

                    self.siemplify.LOGGER.info(
                        f"Pagination failed at page {page_count} after collecting "
                        f"{total_fetched} events. Error: {error_message}"
                    )

                    collected_data = {
                        "events": all_events,
                        "total_events": len(all_events),
                        "partial_data": True,
                        "pagination_info": {
                            "pages_fetched": page_count - 1,
                            "pages_attempted": page_count,
                            "stopped_at_page": page_count,
                        },
                    }

                    error_details = {
                        "error_type": error_type,
                        "error_message": error_message,
                        "page_number": page_count,
                        "retries_attempted": RETRY_COUNT,
                    }

                    raise PartialDataException(
                        f"Partial data collected. Pagination failed at page {page_count}:"
                        f" {error_message}",
                        collected_data=collected_data,
                        error_details=error_details,
                    )
                else:
                    # No data collected yet, re-raise the original exception
                    raise

            result = response.get("result", {})
            events = result.get("events", [])
            scanned_to = result.get("scanned_to")

            if events:
                # Calculate how many we can add without exceeding max_records
                remaining_capacity = max_records - total_fetched
                events_to_add = events[:remaining_capacity]
                all_events.extend(events_to_add)
                total_fetched += len(events_to_add)

                # Check payload size after adding events
                json_str = json.dumps(all_events, ensure_ascii=False)
                current_payload_size = len(json_str.encode("utf-8"))

                self.siemplify.LOGGER.info(
                    f"Fetched {len(events)} events on page {page_count}. "
                    f"Total so far: {total_fetched}/{max_records}. "
                    f"Payload size: {current_payload_size / (1024 * 1024):.2f} MB"
                )

                # Check if payload size limit reached
                if current_payload_size >= MAX_PAYLOAD_SIZE_BYTES:
                    truncation_reason = "payload_limit"
                    self.siemplify.LOGGER.info(
                        f"Payload size limit reached ({current_payload_size / (1024 * 1024):.2f}"
                        " MB). Stopping pagination."
                    )
                    break

                # If we've hit the record limit, stop
                if total_fetched >= max_records:
                    truncation_reason = "record_limit"
                    self.siemplify.LOGGER.info(
                        f"Reached maximum of {max_records} records. Stopping pagination."
                    )
                    break
            else:
                # No events in this response - stop pagination
                self.siemplify.LOGGER.info(
                    f"No events returned on page {page_count}. Pagination complete."
                )
                break

            # Check if we should continue pagination
            if not scanned_to:
                self.siemplify.LOGGER.info("No scanned_to cursor. Pagination complete.")
                break

            # Compare scanned_to with api_end_time to check if we've gone past the range
            if scanned_to <= api_end_time:
                self.siemplify.LOGGER.info(
                    f"scanned_to ({scanned_to}) <= end_time ({api_end_time}). Pagination complete."
                )
                break

            # Update start_time for next iteration
            api_start_time = scanned_to
            self.siemplify.LOGGER.info(
                f"Continuing pagination with new start_time: {api_start_time}"
            )

        # Log if we stopped due to max_pages limit
        if page_count >= max_pages and total_fetched < max_records:
            self.siemplify.LOGGER.info(
                f"Pagination stopped: reached maximum of {max_pages} pages. "
                f"Fetched {total_fetched} events."
            )

        return {
            "result": {
                "events": all_events,
                "total_events": len(all_events),
                "partial_data": False,
                "truncated": truncation_reason is not None,
                "truncation_reason": truncation_reason,
                "pagination_info": {"pages_fetched": page_count, "pages_attempted": page_count},
            }
        }

    def enrich_hosts(self, host_ids: List[str], at_time: Optional[str] = None) -> Dict[str, Any]:
        """
        Enrich multiple hosts with detailed information.

        Args:
            host_ids: List of IP addresses to enrich
            at_time: Optional RFC3339 timestamp for historical data

        Returns:
            Dict containing host enrichment data

        Raises:
            CensysException: If there's an error in the API response
        """
        url = self._get_full_url(ENRICH_IPS_ACTION_IDENTIFIER)

        body = {"host_ids": host_ids}
        if at_time:
            body["at_time"] = at_time

        response = self._make_rest_call(ENRICH_IPS_ACTION_IDENTIFIER, "POST", url, body=body)

        return response

    def enrich_web_properties(
        self, webproperty_ids: List[str], at_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enrich multiple web properties with detailed information.

        Args:
            webproperty_ids: List of web property IDs (hostname:port format)
            at_time: Optional RFC3339 timestamp for historical data

        Returns:
            Dict containing web property enrichment data

        Raises:
            CensysException: If there's an error in the API response
        """
        url = self._get_full_url(ENRICH_WEB_PROPERTIES_ACTION_IDENTIFIER)

        body = {"webproperty_ids": webproperty_ids}
        if at_time:
            body["at_time"] = at_time

        response = self._make_rest_call(
            ENRICH_WEB_PROPERTIES_ACTION_IDENTIFIER, "POST", url, body=body
        )

        return response

    def enrich_certificates(self, certificate_ids: List[str]) -> Dict[str, Any]:
        """
        Enrich certificates using Censys API.

        Args:
            certificate_ids: List of certificate SHA-256 fingerprints

        Returns:
            Dict containing API response with certificate data

        Raises:
            CensysException: If API call fails
        """
        url = self._get_full_url(ENRICH_CERTIFICATES_ACTION_IDENTIFIER)

        body = {"certificate_ids": certificate_ids}

        response = self._make_rest_call(
            ENRICH_CERTIFICATES_ACTION_IDENTIFIER, "POST", url, body=body
        )

        return response
