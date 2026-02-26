from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import Any, Dict, List, Optional

import requests

from .constants import (
    ADD_NOTE_ENDPOINT,
    ALLOWED_INDICATORS_ENDPOINT,
    BULK_ACTION_ADD_TAG_ENDPOINT,
    BULK_ACTION_FALSE_POSITIVE_ENDPOINT,
    BULK_ACTION_REMOVE_TAG_ENDPOINT,
    BULK_ACTION_UNWHITELIST_ENDPOINT,
    BULK_LOOKUP_ENDPOINT,
    CREATE_INTEL_ENDPOINT,
    CREATE_TASK_ENDPOINT,
    DEFAULT_BULK_LOOKUP_FIELDS,
    DEFAULT_REQUEST_TIMEOUT,
    PING_ENDPOINT,
    QUICK_INTEL_STATUS_ENDPOINT,
    RETRIEVE_USERS_ENDPOINT,
    RETRY_COUNT,
    SIGNATURE_EXPIRY_SECONDS,
    TAGS_ENDPOINT,
    TAGS_PAGE_SIZE,
    USER_AGENT_NAME,
    WAIT_TIME_FOR_RETRY,
)
from .cyware_exceptions import (
    CywareException,
    InternalServerError,
    RateLimitException,
    UnauthorizedException,
)
from .utils import sanitize_url


class APIManager:
    def __init__(
        self,
        base_url: str,
        access_id: str,
        secret_key: str,
        verify_ssl: bool = False,
        siemplify: Optional[Any] = None,
    ) -> None:
        """
        Initializes an object of the APIManager class.

        Args:
            base_url (str): Base URL of the Cyware CTIX tenant.
            access_id (str): Access ID for API authentication.
            secret_key (str): Secret Key for API authentication.
            verify_ssl (bool, optional): If True, verify the SSL certificate. Defaults to False.
            siemplify (object, optional): An instance of the SDK SiemplifyAction class.
                Defaults to None.
        """
        self.base_url = base_url.rstrip("/")
        self.access_id = access_id
        self.secret_key = secret_key
        self.siemplify = siemplify
        self.session = requests.session()
        self.session.verify = verify_ssl

    def get_ctix_auth_params(self) -> Dict[str, Any]:
        """
        Generate authentication query parameters for CTIX API requests.

        Returns:
            dict: Dictionary containing AccessID, Expires, and Signature
        """
        expires = int(time.time()) + SIGNATURE_EXPIRY_SECONDS
        to_sign = f"{self.access_id}\n{expires}"
        signature = base64.b64encode(
            hmac.new(
                self.secret_key.encode("utf-8"),
                to_sign.encode("utf-8"),
                hashlib.sha1,   # nosec B303
            ).digest()
        ).decode("utf-8")
        return {
            "AccessID": self.access_id,
            "Expires": expires,
            "Signature": signature,
        }

    def _make_rest_call(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        retry_count: int = RETRY_COUNT,
    ) -> requests.Response:
        """
        Make a REST call to the Cyware CTIX API with retry logic.

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
        auth_params = self.get_ctix_auth_params()
        all_params = {**auth_params, **(params or {})}

        for attempt in range(retry_count):
            try:
                response = self.session.request(
                    method,
                    url,
                    params=all_params,
                    json=json_body,
                    timeout=DEFAULT_REQUEST_TIMEOUT,
                    headers={"User-Agent": USER_AGENT_NAME},
                )

                if response.status_code == 200:
                    return response
                elif response.status_code == 401:
                    raise UnauthorizedException("Invalid API credentials.")
                elif response.status_code == 403:
                    raise UnauthorizedException("Access denied.")
                elif response.status_code == 429:
                    if attempt < retry_count - 1:
                        time.sleep(WAIT_TIME_FOR_RETRY)
                        continue
                    raise RateLimitException("Rate limit exceeded.")
                elif response.status_code >= 500:
                    if attempt < retry_count - 1:
                        time.sleep(WAIT_TIME_FOR_RETRY)
                        continue
                    raise InternalServerError(f"Server error: {response.status_code}")
                else:
                    response.raise_for_status()
                    return response

            except requests.exceptions.HTTPError as e:
                error_msg = str(e)
                sanitized_msg = error_msg
                response_obj = getattr(e, "response", None)
                response_details = ""

                if response_obj is not None:
                    original_url = getattr(response_obj, "url", "")
                    if original_url:
                        sanitized_url = sanitize_url(original_url)
                        sanitized_msg = sanitized_msg.replace(original_url, sanitized_url)

                    response_details = self._get_response_error_details(response_obj)

                if response_details:
                    sanitized_msg = f"{sanitized_msg} Details: {response_details}"

                raise CywareException(sanitized_msg)
            except requests.exceptions.RequestException as e:
                if attempt < retry_count - 1:
                    time.sleep(WAIT_TIME_FOR_RETRY)
                    continue
                # Sanitize any URLs in the exception message
                error_msg = str(e)
                if "http" in error_msg.lower():
                    raise CywareException(f"Request failed: {error_msg}")
                raise

        raise CywareException(
            "Request failed after all retry attempts without returning a response."
        )

    def _get_response_error_details(self, response: requests.Response) -> str:
        """Extract user-friendly error details from a failed HTTP response."""
        try:
            payload = response.json()
        except ValueError:
            return response.text or ""

        details: List[str] = []
        status_code = payload.get("status_code") or response.status_code
        if status_code:
            details.append(f"Status Code: {status_code}")

        errors_section = payload.get("errors")
        error_entries: List[Dict[str, Any]] = []

        def collect_entries(node: Any, field_name: Optional[str]) -> None:
            if isinstance(node, dict):
                contains_text = any(
                    isinstance(node.get(key), str)
                    for key in (
                        "message",
                        "log_message",
                        "title",
                        "support_code",
                        "txn_id",
                        "error",
                    )
                )
                if contains_text:
                    entry = node.copy()
                    if field_name:
                        entry.setdefault("field", field_name)
                    error_entries.append(entry)

                for child_name, child_value in node.items():
                    if isinstance(child_value, (dict, list)):
                        next_field = f"{field_name}.{child_name}" if field_name else child_name
                        collect_entries(child_value, next_field)
            elif isinstance(node, list):
                for item in node:
                    collect_entries(item, field_name)

        if isinstance(errors_section, dict):
            for section_name, section_value in errors_section.items():
                collect_entries(section_value, section_name)

        primary_entry = error_entries[0] if error_entries else {}
        message = payload.get("message") or primary_entry.get("message") or payload.get("error")
        if message:
            details.append(f"Message: {message}")

        log_message = primary_entry.get("log_message")
        if log_message:
            details.append(f"Log Message: {log_message}")

        support_code = primary_entry.get("support_code")
        if support_code:
            details.append(f"Support Code: {support_code}")

        txn_id = primary_entry.get("txn_id")
        if txn_id:
            details.append(f"Transaction ID: {txn_id}")

        field_messages: List[str] = []
        for entry in error_entries:
            field = entry.get("title") or entry.get("field")
            entry_message = entry.get("message")
            if field and entry_message:
                field_messages.append(f"{field}: {entry_message}")

        if field_messages:
            details.append("; ".join(field_messages))

        if not details:
            return response.text or ""

        return " | ".join(details)

    def test_connectivity(self) -> bool:
        """
        Test connectivity to the Cyware CTIX API.

        Returns:
            bool: True if successful

        Raises:
            Exception: If connectivity test fails
        """
        response = self._make_rest_call("GET", PING_ENDPOINT, retry_count=1)
        if self.siemplify:
            self.siemplify.LOGGER.info(f"Ping response: {response.status_code}")
        return True

    def create_intel(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an Intel in Cyware CTIX.

        Args:
            body (dict): Request body containing intel details

        Returns:
            dict: Response containing details and task_id
        """
        response = self._make_rest_call("POST", CREATE_INTEL_ENDPOINT, json_body=body)
        return response.json()

    def get_quick_intel_status(self, task_id: str) -> Dict[str, Any]:
        """Retrieve the status of a Quick Intel task/report."""
        params = {"task_id": task_id}
        response = self._make_rest_call("GET", QUICK_INTEL_STATUS_ENDPOINT, params=params)
        return response.json()

    def list_tags(self) -> List[Dict[str, Any]]:
        """Retrieve all tags with pagination."""
        params = {"page_size": TAGS_PAGE_SIZE, "page": 1}
        tags: List[Dict[str, Any]] = []

        while True:
            response = self._make_rest_call("GET", TAGS_ENDPOINT, params=params)
            data = response.json()
            tags.extend(data.get("results", []))

            next_page = data.get("next")
            if not next_page or not data.get("results"):
                break
            params["page"] += 1

        return tags

    def create_tag(self, tag_name: str) -> Dict[str, Any]:
        """Create a new tag in Cyware CTIX."""
        body = {"name": tag_name}
        response = self._make_rest_call("POST", TAGS_ENDPOINT, json_body=body)
        return response.json()

    def lookup_iocs(self, ioc_values: List[str], object_type: str = "indicator") -> Dict[str, str]:
        """Resolve IOC names to their IDs."""
        response = self.get_ioc_details(
            ioc_values=ioc_values,
            object_type=object_type,
            fields=DEFAULT_BULK_LOOKUP_FIELDS,
        )
        mapping = {}
        for result in response.get("results", []):
            name = result.get("name")
            object_id = result.get("id")
            if name and object_id:
                mapping[name] = object_id
        return mapping

    def get_allowed_iocs(
        self,
        ioc_type: Optional[str] = None,
        created_from: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get allowed IOCs from Cyware CTIX.

        Args:
            ioc_type (str, optional): Filter by indicator type
            created_from (int, optional): Filter IOCs created after this epoch timestamp

        Returns:
            dict: Aggregated response containing all pages of results
        """
        page_size = 100
        params = {"page": 1, "page_size": page_size}

        if ioc_type and ioc_type != "All":
            params["type"] = ioc_type
        if created_from:
            params["created_from"] = created_from

        aggregated_response: Optional[Dict[str, Any]] = None
        aggregated_results: List[Dict[str, Any]] = []

        while True:
            response = self._make_rest_call("GET", ALLOWED_INDICATORS_ENDPOINT, params=params)
            response_json = response.json()

            if aggregated_response is None:
                aggregated_response = response_json.copy()
                aggregated_response["results"] = []

            aggregated_results.extend(response_json.get("results", []))

            next_page = response_json.get("next")
            if not next_page or not response_json.get("results"):
                aggregated_response["total"] = response_json.get("total", len(aggregated_results))
                break

            params["page"] += 1

        aggregated_response["results"] = aggregated_results
        aggregated_response["next"] = None
        aggregated_response["previous"] = None
        aggregated_response["page_size"] = page_size

        return aggregated_response

    def add_allowed_iocs(self, ioc_type: str, values: List[str], reason: str) -> Dict[str, Any]:
        """
        Add IOCs to the allowed list.

        Args:
            ioc_type (str): Type of indicators
            values (list): List of indicator values
            reason (str): Reason for allowing these IOCs

        Returns:
            dict: Response containing details of added IOCs
        """
        body = {"type": ioc_type, "values": values, "reason": reason}
        response = self._make_rest_call("POST", ALLOWED_INDICATORS_ENDPOINT, json_body=body)
        return response.json()

    def remove_allowed_iocs(
        self, indicator_ids: List[str], object_type: str = "indicator"
    ) -> Dict[str, Any]:
        """
        Remove IOCs from the allowed list.

        Args:
            indicator_ids (list): List of indicator IDs to remove

        Returns:
            dict: Response message
        """
        body = {"object_type": object_type, "object_ids": indicator_ids}
        response = self._make_rest_call("POST", BULK_ACTION_UNWHITELIST_ENDPOINT, json_body=body)
        return response.json()

    def get_ioc_details(
        self,
        ioc_values: List[str],
        page: int = 1,
        page_size: int = 10,
        enrichment_data: bool = False,
        relation_data: bool = False,
        object_type: str = "indicator",
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get IOC details with optional enrichment data.

        Args:
            ioc_values (list): List of IOC values to lookup
            page (int): Starting page number
            page_size (int): Number of items per page
            enrichment_data (bool): Include enrichment data
            relation_data (bool): Include relation data
            object_type (str): Object type for lookup endpoint (e.g., "indicator", "observable")

        Returns:
            dict: Aggregated response containing IOC details from all pages.
        """
        params = {"page_size": page_size}
        if fields:
            params["fields"] = fields
        if enrichment_data:
            params["enrichment_data"] = "true"
        if relation_data:
            params["relation_data"] = "true"

        body = {"value": ioc_values}
        aggregated_response: Optional[Dict[str, Any]] = None
        aggregated_results: List[Dict[str, Any]] = []
        current_page = page
        endpoint = BULK_LOOKUP_ENDPOINT.format(object_type=object_type)

        while True:
            params["page"] = current_page
            response = self._make_rest_call("POST", endpoint, params=params, json_body=body)
            response_json = response.json()

            if aggregated_response is None:
                aggregated_response = response_json.copy()
                aggregated_response["results"] = []

            aggregated_results.extend(response_json.get("results", []))

            next_page = response_json.get("next")
            if not next_page or not response_json.get("results"):
                aggregated_response["total"] = response_json.get("total", len(aggregated_results))
                break

            current_page += 1

        aggregated_response["results"] = aggregated_results
        aggregated_response["next"] = None
        aggregated_response["previous"] = None
        aggregated_response["page_size"] = page_size

        return aggregated_response

    def add_tags_to_ioc(
        self, object_ids: List[str], tag_ids: List[str], object_type: str = "indicator"
    ) -> Dict[str, Any]:
        """
        Add tags to IOCs.

        Args:
            object_type (str): Type of object (e.g., "indicator")
            object_ids (list): List of object IDs
            tag_ids (list): List of tag IDs to add

        Returns:
            dict: Response message
        """
        body = {"object_type": object_type, "object_ids": object_ids, "data": {"tag_id": tag_ids}}
        response = self._make_rest_call("POST", BULK_ACTION_ADD_TAG_ENDPOINT, json_body=body)
        return response.json()

    def remove_tags_from_ioc(
        self, object_ids: List[str], tag_ids: List[str], object_type: str = "indicator"
    ) -> Dict[str, Any]:
        """
        Remove tags from IOCs.

        Args:
            object_type (str): Type of object (e.g. "indicator")
            object_ids (list): List of object IDs
            tag_ids (list): List of tag IDs to remove

        Returns:
            dict: Response message
        """
        body = {"object_type": object_type, "object_ids": object_ids, "data": {"tag_id": tag_ids}}
        response = self._make_rest_call("POST", BULK_ACTION_REMOVE_TAG_ENDPOINT, json_body=body)
        return response.json()

    def add_note_to_indicator(
        self, object_id: str, text: str, note_type: str, is_json: bool = False
    ) -> Dict[str, Any]:
        """
        Add a note to an indicator.

        Args:
            object_id (str): Object ID of the indicator
            text (str): Note text/description
            note_type (str): Type of note (e.g., "threatdata")
            is_json (bool): Whether the note is in JSON format

        Returns:
            dict: Response containing note details
        """
        body = {"object_id": object_id, "text": text, "type": note_type, "is_json": is_json}
        response = self._make_rest_call("POST", ADD_NOTE_ENDPOINT, json_body=body)
        return response.json()

    def mark_indicator_false_positive(
        self, object_ids: List[str], object_type: str = "indicator"
    ) -> Dict[str, Any]:
        """
        Mark indicators as false positive.

        Args:
            object_ids (list): List of object IDs to mark as false positive

        Returns:
            dict: Response message
        """
        body = {"object_type": object_type, "object_ids": object_ids}
        response = self._make_rest_call("POST", BULK_ACTION_FALSE_POSITIVE_ENDPOINT, json_body=body)
        return response.json()

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user information by email address.

        Args:
            email (str): Email address of the user

        Returns:
            dict: User information including user_id, or None if not found
        """
        params = {"q": email}
        response = self._make_rest_call("GET", RETRIEVE_USERS_ENDPOINT, params=params)
        result = response.json()
        users = result.get("results", [])
        if users:
            return users[0]
        return None

    def create_task(
        self,
        text: str,
        priority: str,
        object_id: str,
        deadline: int,
        assignee: Optional[str] = None,
        status: str = "not_started",
        object_type: str = "indicator",
    ) -> Dict[str, Any]:
        """
        Create a task for an indicator.

        Args:
            text (str): Task description
            priority (str): Task priority (low, medium, high, critical)
            object_id (str): Object ID of the indicator
            deadline (int): Deadline in epoch time
            assignee (str, optional): User ID of the assignee. If None, task created without
                assignee.
            status (str): Task status (default: "not_started")
            object_type (str): Type of object (default: "indicator")

        Returns:
            dict: Response containing task details
        """
        body = {
            "text": text,
            "priority": priority,
            "status": status,
            "type": object_type,
            "object_id": object_id,
            "deadline": deadline,
        }
        if assignee:
            body["assignee"] = assignee
        response = self._make_rest_call("POST", CREATE_TASK_ENDPOINT, json_body=body)
        return response.json()
