from __future__ import annotations

import base64
import datetime
import hashlib
import hmac
from urllib.parse import urljoin, urlparse

import requests

from constants import (
    AZ_TENANT_RELATED_TYPES,
    AZURE_RELATED_TYPES,
    AZURE_TYPES,
    BAD_REQUEST,
    DIRECTORY_TYPES,
    FORBIDDEN_REQUEST,
    NOT_FOUND,
    TOO_MANY_REQUEST,
    UNAUTHORIZE_REQUEST,
)
from exceptions import (
    BloodHoundBadRequestException,
    BloodHoundException,
    BloodHoundForbiddenException,
    BloodHoundNotFoundException,
    BloodHoundRateLimitException,
    BloodHoundUnauthorizedException,
)

# Comprehensive endpoints dictionary
ENDPOINTS = {
    "test_connection": "/api/v2/available-domains",
    "available_domain": "/api/v2/available-domains",
    "domain_available_types": "/api/v2/domains/{domain}/available-types",
    "path_title": "/api/v2/assets/findings/{finding_type}/title.md",
    "attack_path_details": "/api/v2/domains/{domain_id}/details?finding={finding_type}&skip={skip}",
    "search": "/api/v2/search?q={query}",
    "base": "/api/v2/base/{object_id}",
    "dictionary_types": "/api/v2/{obj_type}s/{object_id}",
    "azure_types": "/api/v2/azure/{obj_type}?object_id={object_id}&counts=false",
    "azure_related_types": (
        "/api/v2/azure/tenants?object_id={object_id}"
        "&related_entity_type={rel_type}&skip=0&limit=128"
    ),
    "update_primary_response": (
        "/api/v2/azure/{obj_type}?object_id={object_id}"
        "&related_entity_type={related_type}&skip=0&limit=128"
    ),
    "shortest_path": "/api/v2/graphs/shortest-path?start_node={start_node}&end_node={end_node}",
    "short_description": "/api/v2/assets/findings/{finding_type}/short_description.md",
    "short_remediation": "/api/v2/assets/findings/{finding_type}/short_remediation.md",
    "long_remediation": "/api/v2/assets/findings/{finding_type}/long_remediation.md"
}


class BloodhoundManager:
    def __init__(self, tenant_domain, token_id, token_key, logger=None):
        """
        Initializes the BloodhoundManager with tenant credentials and optional logger.

        Args:
            tenant_domain (str): The base URL/domain of the BloodHound Enterprise instance.
            token_id (str): The token ID used for authentication.
            token_key (str): The token secret key used to generate HMAC signatures.
            logger (logging.Logger, optional): Logger instance for logging errors and info.
        """ 
        self.tenant_domain = tenant_domain
        self.__token_id = token_id
        self.__token_key = token_key
        self.logger = logger

    def _get_full_url(self, url_key, **kwargs) -> str:
        """Construct full URL from endpoint key and parameters"""
        return urljoin(self.tenant_domain, ENDPOINTS[url_key].format(**kwargs))

    def _get_headers(self, method: str, uri: str) -> dict:
        """Generate authentication headers for API requests"""
        try:
            digester = hmac.new(self.__token_key.encode(), None, hashlib.sha256)
            digester.update(f'{method}{uri}'.encode())
            digester = hmac.new(digester.digest(), None, hashlib.sha256)
            datetime_formatted = datetime.datetime.now().astimezone().isoformat('T')
            digester.update(datetime_formatted[:13].encode())
            digester = hmac.new(digester.digest(), None, hashlib.sha256)

            urlparse(self.tenant_domain)
          
            headers = {
                'User-Agent': 'BloodHound Enterprise Integration',
                'Authorization': f'bhesignature {self.__token_id}',
                'RequestDate': datetime_formatted,
                'Signature': base64.b64encode(digester.digest()).decode(),
                'Content-Type': 'application/json',
            }

            return headers
        except Exception as e:
            error_msg: str = f"Error generating headers: {e}"
            self._log_error(error_msg)
            raise BloodHoundException(error_msg)

    @staticmethod
    def _validate_response(response, error_msg="An error occurred"):
        """
        Validates the HTTP response and raises relevant exceptions
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            try:
                json_resp = response.json()
            except Exception:
                raise BloodHoundException(f"{error_msg}: {error} - {response.content}")

            if response.status_code == BAD_REQUEST:
                raise BloodHoundBadRequestException(f"{error_msg}: {error} - {json_resp.get('message')}")
            elif response.status_code == NOT_FOUND:
                raise BloodHoundNotFoundException(f"{error_msg}: {error} - {json_resp.get('message')}")
            elif response.status_code == UNAUTHORIZE_REQUEST:
                raise BloodHoundUnauthorizedException(f"{error_msg}: Unauthorized - {json_resp.get('message')}")
            elif response.status_code == FORBIDDEN_REQUEST:
                raise BloodHoundForbiddenException(f"{error_msg}: Forbidden - {json_resp.get('message')}")
            elif response.status_code == TOO_MANY_REQUEST:
                raise BloodHoundRateLimitException(f"{error_msg}: Rate Limit - {json_resp.get('message')}")

            raise BloodHoundException(f"{error_msg}: {error} - {json_resp.get('message')}")

    def _api_request(self, endpoint_key: str, return_json=True, method: str = "GET", **kwargs):
        """
        Centralized function to handle API requests and error handling

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint_key: Key in ENDPOINTS dictionary
            return_json: Whether to return JSON response or raw response
            **kwargs: Includes format params, query params, post body, etc.

        Returns:
            Response data or None if request fails
        """
        # Construct URL and URI path
        url = self._get_full_url(endpoint_key, **kwargs)
        uri_path = ENDPOINTS[endpoint_key].format(**kwargs)
        
        # Prepare headers
        headers = self._get_headers(method, uri_path)
        
        # Extract query params and payload
        params = kwargs.get("params", None)
        data = kwargs.get("data", None)

        # Make the request
        response = requests.request(method, url, headers=headers, params=params, data=data)

        self._validate_response(response, f"API request to {endpoint_key} failed")

        return response.json() if return_json else response
    
    def test_connection(self):
        """
        Tests the connection to the BloodHound Enterprise API.

        Returns:
            Response object: Raw HTTP response from the test connection endpoint.
        """
        return self._api_request("test_connection", return_json=False)
            
    def get_finding_type_short_description(self, finding_type: str):
        """
        Fetches the short description markdown for a given finding type.

        Args:
            finding_type (str): Type of the finding to retrieve short description for.

        Returns:
            str: The markdown text if available, otherwise an empty string.
        """
        try:
            # Use centralized _api_request with return_json=False for raw text
            response = self._api_request(
                endpoint_key="short_description",
                return_json=False,
                finding_type=finding_type
            )

            if response:
                return response.text
            else:
                self._log_error("Received non-200 response or empty body.")
                return ""
        except BloodHoundException as e:
            self._log_error(f"Failed to fetch short_description for finding type {finding_type}: {e}")
            return ""
    
	# Get Finding type Short Remediations
    def get_finding_type_short_remediation(self, finding_type: str):
        """
        Fetches the short remediation markdown for a given finding type.

        Args:
            finding_type (str): Type of the finding to retrieve short remediation for.

        Returns:
            str: The markdown text if available, otherwise an empty string.
        """
        try:
            # Use centralized _api_request with return_json=False for raw text
            response = self._api_request(
                endpoint_key="short_remediation",
                return_json=False,
                finding_type=finding_type
            )

            if response:
                return response.text
            else:
                self._log_error("Received non-200 response or empty body.")
                return ""

        except BloodHoundException as e:
            self._log_error(f"Failed to fetch short_remediation for finding type {finding_type}: {e}")
            return ""

    def get_finding_type_long_remediation(self, finding_type: str):
        """
        Fetches the long remediation markdown for a given finding type.

        Args:
            finding_type (str): Type of the finding to retrieve long remediation for.

        Returns:
            str: The markdown text if available, otherwise an empty string.
        """
        try:
            # Use centralized _api_request with return_json=False for raw text
            response = self._api_request(
                endpoint_key="long_remediation",
                return_json=False,
                finding_type=finding_type
            )

            if response:
                return response.text
            else:
                self._log_error("Received non-200 response or empty body.")
                return ""

        except BloodHoundException as e:
            self._log_error(f"Failed to fetch long_remediation for finding type {finding_type}: {e}")
            return ""

    def get_available_domains(self):
        """
        Fetches the list of available domains from the BloodHound Enterprise API.
        Returns:
            Tuple (bool, response):
                - True and response object if successful
                - False and error/None if failed
        """
        try:
            # Make API request to the available_domain endpoint
            response = self._api_request("available_domain", return_json=False)
            if response:
                return True, response
            else:
                self._log_error("No response received while fetching available domains.")
                return False, None

        except Exception as e:
            self._log_error(f"Exception occurred while fetching available domains: {e}")
            return False, e

    def get_available_types_for_domain(self, domain: str) -> list:
        """Fetch available types for a single domain."""
        try:
            response = self._api_request("domain_available_types", domain=domain)
            if response:
                return response.get("data", [])
            else:
                self._log_error("Received non-200 response or empty body.")
                return []
        except Exception as e:
            self._log_error(f"Exception occurred while fetching attack path types for domain {domain}: {e}")
            return False, e

    def get_path_title(self, finding_type: str) -> str:
        """
        Fetches the path title markdown for a single finding type.
        Returns the markdown text or empty string if not found.
        """
        try:
            # Use centralized _api_request with return_json=False for raw text
            response = self._api_request(
                endpoint_key="path_title",
                return_json=False,
                finding_type=finding_type
            )

            if response:
                return response.text
            else:
                self._log_error("Received non-200 response or empty body.")
                return ""

        except BloodHoundException as e:
            self._log_error(f"Failed to fetch title for finding type {finding_type}: {e}")
            return ""

    def get_attack_path_details_page(
        self,
        domain_id: str,
        finding_type: str,
        skip: int = 0,
        created_at: str = None,
    ) -> list:
        """
        Fetches a single page of attack path details for the given domain and finding type.
        Pagination is handled outside this method using the `skip` parameter.
        Optionally filters results to only those created after a specified date.
        
        Args:
            domain_id: The domain ID to fetch attack paths for
            finding_type: The type of finding to fetch
            skip: Number of results to skip (for pagination)
            created_at: Optional date string in YYYY-MM-DD format to filter results by created date
            
        Returns:
            list: Attack path details data
        """
        try:
            params = {}
            
            # Add created_at filter if provided
            if created_at:
                # Add filter for created_at, filtering only attack paths created on or after the provided date
                # The exact format of this parameter depends on your API implementation
                params["created_at"] = created_at
            
            params['sort_by'] = 'created_at'
            
            response = self._api_request(
                "attack_path_details", 
                domain_id=domain_id, 
                finding_type=finding_type, 
                skip=skip,
                **params 
            )
            
            return response.get("data", []) if response else []
        except BloodHoundException as e:
            self._log_error(
                f"Failed to fetch attack path details for domain {domain_id}, "
                f"finding type {finding_type}: {e}"
            )
            return []

    def _handle_fetch_asset_information(self, object_id: str) -> dict:
        """
        Retrieves asset information based on the given object ID.

        Steps:
        - Searches for the object using its ID.
        - Determines the type of the object and fetches its primary details.
        - If the object is of Azure type, also fetches and appends related data.

        Args:
            object_id (str): The unique object ID to search.

        Returns:
            dict: Dictionary containing status, message, and asset data.
        """
        response = self._api_request("search", query=object_id)
        
        if not response.get("data"):
            return {"status": "error", "message": "Object Id not available", "data": {}}
        
        if response.get("data") == []:
            return {"status": "success", "message": "Received empty response from server.", "data": {}}

        obj_type = response["data"][0]["type"]

        primary_response = self._fetch_primary_response(object_id, obj_type)

        if not primary_response:
            return {"status": "error", "message": "Failed to fetch primary response", "data": {}}

        if obj_type.startswith("AZ"):
            self._handle_azure_types(object_id, obj_type, primary_response)

        return {"status": "success", "message": "Asset fetched", "data": primary_response.get("data", {})}

    def _fetch_primary_response(self, object_id, obj_type):
        """
        Fetches the primary asset data based on object type and ID.

        Args:
            object_id (str): The unique identifier for the asset.
            obj_type (str): The type of the object (e.g., AZApp, AZUser, etc.).

        Returns:
            dict: API response containing primary asset data.
        """                 
        if obj_type in DIRECTORY_TYPES:
            endpoint_type = "dictionary_types"
            params = {"obj_type": obj_type.lower(), "object_id": object_id}
        elif obj_type in AZURE_TYPES:
            endpoint_type = "azure_types"
            params = {"obj_type": self._get_azure_type_path(obj_type), "object_id": object_id}
        else:
            endpoint_type = "base"
            params = {"object_id": object_id}

        return self._api_request(endpoint_type, **params)

    def _get_azure_type_path(self, obj_type):
        """
        Converts Azure object type to appropriate API path component.

        Args:
            obj_type (str): Azure object type (e.g., AZServicePrincipal).

        Returns:
            str: Corresponding path segment for the API.
        """
        if obj_type == "AZServicePrincipal":
            return "service-principals"
        elif obj_type == "AZApp":
            return "applications"
        return (obj_type[2:] + "s").lower()

    def _handle_azure_types(self, object_id, obj_type, primary_response):
        """
        Enhances the primary response with Azure-specific related entity counts.

        Args:
            object_id (str): The object ID to enrich.
            obj_type (str): The Azure object type.
            primary_response (dict): The response dictionary to update.
        """
        if obj_type == "AZTenant":
            self._process_az_tenant(object_id, primary_response)
        else:
            related_types = AZURE_RELATED_TYPES.get(obj_type, {})

            for related_type, mapping_key in related_types.items():
                self._update_primary_response(
                    primary_response,
                    object_id,
                    obj_type,
                    related_type,
                    mapping_key,
                )

    def _process_az_tenant(self, object_id, primary_response):
        """
        Processes AZTenant-specific related entity counts and enriches primary response.

        Args:
            object_id (str): Object ID of the AZTenant.
            primary_response (dict): Dictionary to be enriched with counts.
        """
        descendent_count = 0
        inbound_control_count = 0

        for rel_type in AZ_TENANT_RELATED_TYPES:
            secondary_response = self._api_request("azure_related_types", rel_type=rel_type, object_id=object_id)

            if secondary_response and "count" in secondary_response:
                if rel_type == "inbound-control":
                    inbound_control_count = secondary_response["count"]
                else:
                    descendent_count += secondary_response["count"]
            else:
                self._log_error(f"Failed to fetch data for related type: {rel_type}")

        primary_response["data"]["inbound_object_control"] = inbound_control_count
        primary_response["data"]["descendents"] = {"descendent_counts": descendent_count}

    def _update_primary_response(self, primary_response, object_id, obj_type, related_type, mapping_key):
        """
        Fetches count of related entities and updates the primary response accordingly.

        Args:
            primary_response (dict): The original asset data to be enriched.
            object_id (str): Object identifier.
            obj_type (str): Object type.
            related_type (str): Type of related entity to query.
            mapping_key (str): Key under which to store the count in the response.
        """
        secondary_response = self._api_request(
            "update_primary_response",
            obj_type=obj_type,
            object_id=object_id,
            related_type=related_type,
        )

        if not secondary_response or "count" not in secondary_response:
            self._log_error(f"Failed to fetch data for related type: {related_type}")
            return

        primary_response["data"][mapping_key] = secondary_response["count"]

    def does_path_exists_between_nodes(self, start_node: str, end_node: str) -> dict:
        """
        Checks if a shortest path exists between two nodes in BloodHound Enterprise.
        Returns a dictionary with status, message, and data (True/False).
        """
        self._api_request(
            "shortest_path", 
            return_json=False,
            start_node=start_node, 
            end_node=end_node
        )

        return {
            "status": "success",
            "message": "Path exists between nodes.",
            "data": True
        }

    def get_object_id_by_name(self, name: str) -> dict:
        """
        Fetches the object_id of a node based on its name.
        Returns a dictionary with status, message, and object_id (if found).
        """
        response = self._api_request("search", query=name)
        return {"status": "success", "data": response.get("data")}

    def _log_error(self, message):
        """"
        Logs the provided error message using the logger if available, else prints it.

        Args:
            message (str): Error message to be logged or printed.
        """
        if self.logger:
            self.logger.error(message)
        else:
            print(f"[ERROR] {message}")