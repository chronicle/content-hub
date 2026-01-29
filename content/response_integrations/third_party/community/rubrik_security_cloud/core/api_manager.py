from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

import requests
from TIPCommon.oauth import CredStorage

from .constants import (
    ADVANCE_IOC_SCAN_ACTION_IDENTIFIER,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_SONAR_FILE_SORT_ORDER,
    DEFAULT_TIMEZONE,
    GET_CDM_CLUSTER_CONNECTION_STATE_ACTION_IDENTIFIER,
    GET_CDM_CLUSTER_LOCATION_ACTION_IDENTIFIER,
    GET_SONAR_SENSITIVE_HITS_ACTION_IDENTIFIER,
    GRAPHQL_URL,
    INTERNAL_SERVER_ERROR_STATUS_CODES,
    IOC_SCAN_RESULTS_ACTION_IDENTIFIER,
    IOC_TYPE_MAP,
    LIST_EVENTS_ACTION_IDENTIFIER,
    LIST_OBJECT_SNAPSHOTS_ACTION_IDENTIFIER,
    LIST_SONAR_FILE_CONTEXTS_ACTION_IDENTIFIER,
    PING_ACTION_IDENTIFIER,
    RATE_LIMIT_EXCEEDED_STATUS_CODE,
    RETRY_COUNT,
    SORT_ORDER_ENUM,
    TURBO_IOC_SCAN_ACTION_IDENTIFIER,
    UNAUTHORIZED_STATUS_CODE,
    WAIT_TIME_FOR_RETRY,
)
from .graphql_queries import (
    CDM_CLUSTER_CONNECTION_STATE_QUERY,
    CDM_CLUSTER_LOCATION_QUERY,
    LIST_EVENTS_QUERY,
    OBJECT_SNAPSHOTS_QUERY,
    SONAR_FILE_CONTEXTS_QUERY,
    SONAR_OBJECT_DETAIL_QUERY,
    SONAR_POLICY_OBJECTS_LIST_QUERY,
    START_BULK_THREAT_HUNT_MUTATION,
    START_TURBO_THREAT_HUNT_MUTATION,
    TEST_CONNECTIVITY_QUERY,
    THREAT_HUNT_DETAILS_V2_QUERY,
)
from .rubrik_exceptions import (
    GraphQLQueryException,
    InternalSeverError,
    ItemNotFoundException,
    RateLimitException,
    RubrikException,
    UnauthorizedErrorException,
)
from .rubrik_oauth_adapter import RubrikOAuthAdapter, RubrikOAuthManager
from .utils import (
    HandleExceptions,
    extract_domain_from_uri,
    generate_encryption_key,
    validate_json,
)


class APIManager:
    def __init__(
        self,
        service_account_json: str,
        verify_ssl: bool = False,
        siemplify: Optional[Any] = None,
    ) -> None:
        """Initialize the APIManager with access token management.

        OAuth Token Flow:
        1. Fetch access_token from encrypted storage
        2. If found and valid, use it for API calls
        3. If not found, generate new access_token and save

        Args:
            service_account_json: Service account credentials
                                  (client_id, client_secret, access_token_uri)
            verify_ssl: Whether to verify SSL certificates
            siemplify: Chronicle SOAR SDK instance for logging and context storage
        """
        self.siemplify = siemplify
        self.service_account_json = validate_json(
            service_account_json, "service account", is_mandatory=True
        )
        self.client_id = self.service_account_json.get("client_id")
        if not self.client_id:
            raise RubrikException("Invalid Service Account JSON, Client ID is not present.")

        access_token_uri = self.service_account_json.get("access_token_uri")
        if not access_token_uri:
            raise RubrikException("Invalid Service Account JSON, Access Token URI is not present.")

        self.domain = extract_domain_from_uri(access_token_uri)
        self.graphql_url = GRAPHQL_URL.format(domain=self.domain)
        self.verify_ssl = verify_ssl
        self.token = ""

        self.oauth_adapter = RubrikOAuthAdapter(
            service_account_json=self.service_account_json,
            verify_ssl=self.verify_ssl,
            client_id=self.client_id,
        )

        self.cred_storage = CredStorage(
            encryption_password=generate_encryption_key(self.client_id, self.domain),
            chronicle_soar=self.siemplify,
        )

        self.oauth_manager = RubrikOAuthManager(
            oauth_adapter=self.oauth_adapter,
            cred_storage=self.cred_storage,
        )

        self.is_token_expired = self.oauth_manager._token_is_expired()
        if self.is_token_expired:
            self.siemplify.LOGGER.info("Access token is expired")
        self.token = (
            self.oauth_manager._token.access_token
            if self.oauth_manager._token and hasattr(self.oauth_manager._token, "access_token")
            else ""
        )
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

        if not self.token or self.is_token_expired:
            self.generate_token()

        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def generate_token(self) -> str:
        """Generate and save a new access token.

        This method refreshes the access token using the service account credentials,
        saves it to encrypted storage, and updates the session headers.
        """
        self.siemplify.LOGGER.info("Generating new token")

        token = self.oauth_adapter.refresh_token()
        self.oauth_manager._token = token  # Update manager's token reference
        self.oauth_manager.save_token()
        self.token = token.access_token
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

        self.siemplify.LOGGER.info("Token generated and saved successfully")

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
        """Make a REST call to the Rubrik API with automatic retry logic.

        Args:
            api_identifier: API action identifier for logging
            method: HTTP method (GET, POST, etc.)
            url: Target URL
            params: URL parameters
            body: JSON payload
            data: Raw data payload
            retry_count: Number of retries for rate limiting/auth errors

        Returns:
            JSON response as dictionary

        Raises:
            RateLimitException: If max retries exceeded
            UnauthorizedErrorException: If auth fails after token refresh
            GraphQLQueryException: If GraphQL response contains errors
        """

        request_kwargs = {"params": params, "timeout": DEFAULT_REQUEST_TIMEOUT}
        if data:
            request_kwargs["data"] = data
        elif body:
            request_kwargs["json"] = body

        response = self.session.request(method, url, **request_kwargs)

        try:
            self.validate_response(api_identifier, response)
        except (RateLimitException, InternalSeverError):
            if retry_count > 0:
                time.sleep(WAIT_TIME_FOR_RETRY)
                return self._make_rest_call(
                    api_identifier, method, url, params, body, data, retry_count - 1
                )
            raise RateLimitException(
                "Max retries exceeded. Please check your network connection and try again later."
            )
        except UnauthorizedErrorException:
            response_json = response.json()

            if not isinstance(response_json, dict):
                raise UnauthorizedErrorException(
                    f"Unauthorized, please verify your credentials: {response.text}"
                )

            message = response_json.get("message", "").lower()
            if retry_count > 0 and "jwt" in message:
                self.siemplify.LOGGER.info(
                    "JWT validation error detected, generating new access token"
                )
                time.sleep(WAIT_TIME_FOR_RETRY)
                self.generate_token()
                return self._make_rest_call(
                    api_identifier, method, url, params, body, data, retry_count - 1
                )

            raise UnauthorizedErrorException(
                "The access token has expired. Unable to regenerate, "
                "please verify your credentials."
            )

        try:
            return response.json()
        except Exception:
            self.siemplify.LOGGER.error(
                f"Exception occurred while parsing response JSON for {api_identifier} and URL {url}"
            )

    def validate_response(
        self,
        api_identifier: str,
        response: requests.Response,
        error_msg: str = "An error occurred",
    ) -> bool:
        """Validate API response for HTTP and GraphQL errors.

        Args:
            api_identifier: API action identifier
            response: HTTP response object
            error_msg: Custom error message

        Returns:
            True if response is valid

        Raises:
            RateLimitException: If API rate limit exceeded
            UnauthorizedErrorException: If authentication failed
            InternalSeverError: If server error occurred
            GraphQLQueryException: If GraphQL errors found
            RubrikException: For other errors
        """
        try:
            # Step 1: Check HTTP status code
            response.raise_for_status()

            # Step 2: Check for GraphQL errors (only if status is 200 OK)
            response_json = response.json()
            handler = HandleExceptions(
                api_identifier,
                Exception("GraphQL error in response"),
                response,
                f"GraphQL errors detected for {api_identifier}",
            )

            has_errors, error_tuple = handler._extract_graphql_errors(response_json)

            if has_errors:
                _, error_message = error_tuple
                self.siemplify.LOGGER.error(
                    f"GraphQL errors detected for API identifier {api_identifier}: {error_message}"
                )
                raise GraphQLQueryException(error_message)

        except GraphQLQueryException:
            raise
        except requests.HTTPError as error:
            if response.status_code == UNAUTHORIZED_STATUS_CODE:
                raise UnauthorizedErrorException()
            if response.status_code == RATE_LIMIT_EXCEEDED_STATUS_CODE:
                raise RateLimitException("API rate limit exceeded")
            if response.status_code in INTERNAL_SERVER_ERROR_STATUS_CODES:
                raise InternalSeverError(f"Internal server error: {response.status_code}")
            HandleExceptions(api_identifier, error, response, error_msg).do_process()
        except Exception as e:
            self.siemplify.LOGGER.error(f"Error validating response: {str(e)}")
            raise RubrikException(f"{str(e)}")

        return True

    def test_connectivity(self):
        """Test connectivity to the Rubrik Security Cloud GraphQL API.

        Returns:
            bool: True if connection is successful, raises exception otherwise.

        Raises:
            GraphQLQueryException: If there's an error in the GraphQL response.
        """
        payload = json.dumps({"query": TEST_CONNECTIVITY_QUERY, "variables": {}})

        self._make_rest_call(PING_ACTION_IDENTIFIER, "POST", self.graphql_url, data=payload)

        return True

    def start_turbo_ioc_scan(
        self,
        ioc_list: List[str],
        scan_name: Optional[str] = None,
        cluster_ids: Optional[List[str]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        max_snapshots_per_object: Optional[int] = None,
    ) -> str:
        """Start a new Turbo Threat Hunt scan.

        Args:
            ioc_list: IOC hash values to scan for (MD5, SHA1, SHA256)
            scan_name: Name for the scan
            cluster_ids: Cluster IDs to scan (empty = all clusters)
            start_time: Start time for filtering snapshots (ISO format)
            end_time: End time for filtering snapshots (ISO format)
            max_snapshots_per_object: Max snapshots to scan per object

        Returns:
            Hunt ID for the created scan

        Raises:
            GraphQLQueryException: If GraphQL query fails
        """
        formatted_iocs = [{"iocKind": "IOC_HASH", "iocValue": ioc} for ioc in ioc_list]

        base_config: Dict[str, Any] = {
            "name": scan_name,
            "ioc": {"iocList": {"indicatorsOfCompromise": formatted_iocs}},
            "threatHuntType": "TURBO_THREAT_HUNT",
            "snapshotScanLimit": {"scanConfig": {}},
        }

        if start_time or end_time or max_snapshots_per_object:
            scan_config: Dict[str, Any] = {}
            if start_time:
                scan_config["startTime"] = start_time
            if end_time:
                scan_config["endTime"] = end_time
            if max_snapshots_per_object:
                scan_config["maxSnapshotsPerObject"] = max_snapshots_per_object

            base_config["snapshotScanLimit"]["scanConfig"] = scan_config

        input_vars: Dict[str, Any] = {
            "config": {
                "baseConfig": base_config,
                "objectsToScan": [
                    {
                        "objectType": "CDM_CLUSTER",
                        "objectIds": [],
                    }
                ],
            }
        }

        if cluster_ids:
            input_vars["config"]["objectsToScan"][0]["objectIds"] = cluster_ids

        variables = {"input": input_vars}

        self.siemplify.LOGGER.info(
            f"Executing startTurboThreatHunt mutation with {len(formatted_iocs)} IOC values"
        )

        payload = json.dumps({"query": START_TURBO_THREAT_HUNT_MUTATION, "variables": variables})

        return self._make_rest_call(
            TURBO_IOC_SCAN_ACTION_IDENTIFIER, "POST", self.graphql_url, data=payload
        )

    def _process_ioc_value(self, mapped_kind: str, value: Any) -> List[Dict[str, str]]:
        """Process IOC value(s) into standardized indicator format.

        Args:
            mapped_kind: Mapped IOC kind/type
            value: IOC value (string or list of strings)

        Returns:
            List of IOC indicator dictionaries
        """
        indicators = []
        if isinstance(value, list):
            for item in value:
                if item:
                    indicators.append({"iocKind": mapped_kind, "iocValue": item})
        else:
            if value is not None and str(value).strip():
                indicators.append({"iocKind": mapped_kind, "iocValue": value})
        return indicators

    def _parse_advance_ioc_json(self, advance_ioc_json: dict) -> List[Dict[str, str]]:
        """Parse advanced IOC JSON and extract indicators.

        Args:
            advance_ioc_json: Dictionary containing IOC data

        Returns:
            List of IOC indicator dictionaries
        """
        indicators = []
        for k, v in advance_ioc_json.items():
            mapped_kind = IOC_TYPE_MAP.get(k, k)
            indicators.extend(self._process_ioc_value(mapped_kind, v))
        return indicators

    def _build_ioc_list(
        self,
        advance_ioc_json: Optional[str],
        ioc_type: Optional[str],
        ioc_value: Optional[str],
    ) -> List[Dict[str, str]]:
        """Build IOC indicators from JSON dict or individual type/value pair.

        Args:
            advance_ioc_json: Dictionary containing multiple IOCs
            ioc_type: Single IOC type
            ioc_value: Single IOC value

        Returns:
            List of IOC indicator dictionaries

        Raises:
            GraphQLQueryException: If JSON parsing fails
        """
        indicators: List[Dict[str, str]] = []

        if advance_ioc_json:
            try:
                if isinstance(advance_ioc_json, dict):
                    indicators = self._parse_advance_ioc_json(advance_ioc_json)
            except Exception as e:
                raise GraphQLQueryException(f"Invalid Advanced IOC JSON. Error: {str(e)}")
        elif ioc_type and ioc_value:
            mapped_kind = IOC_TYPE_MAP.get(ioc_type, ioc_type)
            indicators.append({"iocKind": mapped_kind, "iocValue": ioc_value})

        return indicators

    def _build_file_scan_criteria(
        self,
        min_file_size: Optional[int],
        max_file_size: Optional[int],
        paths_to_include: Optional[List[str]],
        paths_to_exclude: Optional[List[str]],
        paths_to_exempt: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Build file scan criteria configuration for threat hunts.

        Args:
            min_file_size: Minimum file size in bytes.
            max_file_size: Maximum file size in bytes.
            paths_to_include: File paths to include in scan.
            paths_to_exclude: File paths to exclude from scan.
            paths_to_exempt: File paths to exempt from scan.

        Returns:
            Dict with fileSizeLimits and pathFilter configurations.
        """
        file_size_limits: Dict[str, int] = {}
        if min_file_size:
            file_size_limits["minimumSizeInBytes"] = min_file_size
        if max_file_size:
            file_size_limits["maximumSizeInBytes"] = max_file_size

        path_filter: Dict[str, List[str]] = {}
        if paths_to_include:
            path_filter["inclusions"] = paths_to_include
        if paths_to_exclude:
            path_filter["exclusions"] = paths_to_exclude
        if paths_to_exempt:
            path_filter["exemptions"] = paths_to_exempt

        file_scan_criteria: Dict[str, Any] = {}
        if file_size_limits:
            file_scan_criteria["fileSizeLimits"] = file_size_limits
        if path_filter:
            file_scan_criteria["pathFilter"] = path_filter

        return file_scan_criteria

    def _build_scan_config(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        max_snapshots_per_object: Optional[int],
    ) -> Dict[str, Any]:
        """Build snapshot scan configuration for threat hunts.

        Args:
            start_date: Start date for snapshot filtering.
            end_date: End date for snapshot filtering.
            max_snapshots_per_object: Maximum snapshots to scan per object.

        Returns:
            Dict with startTime, endTime, and maxSnapshotsPerObject configuration.
        """
        scan_config: Dict[str, Any] = {}
        if start_date:
            scan_config["startTime"] = start_date
        if end_date:
            scan_config["endTime"] = end_date
        if max_snapshots_per_object:
            scan_config["maxSnapshotsPerObject"] = max_snapshots_per_object
        return scan_config

    def start_advance_ioc_scan(
        self,
        object_id: List[str],
        ioc_type: Optional[str] = None,
        ioc_value: Optional[str] = None,
        scan_name: Optional[str] = None,
        advance_ioc_json: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_snapshots_per_object: Optional[int] = None,
        min_file_size: Optional[int] = None,
        max_file_size: Optional[int] = None,
        paths_to_include: Optional[List[str]] = None,
        paths_to_exclude: Optional[List[str]] = None,
        paths_to_exempt: Optional[List[str]] = None,
        max_matches_per_snapshot: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Start an Advanced Threat Hunt (THREAT_HUNT_V2).

        Args:
            object_id: List of object FIDs to scan
            ioc_type: Single IOC type
            ioc_value: Single IOC value
            scan_name: Name for the scan
            advance_ioc_json: Dictionary with multiple IOCs
            start_date: Start date for snapshot filtering
            end_date: End date for snapshot filtering
            max_snapshots_per_object: Max snapshots per object
            min_file_size: Minimum file size in bytes
            max_file_size: Maximum file size in bytes
            paths_to_include: File paths to include
            paths_to_exclude: File paths to exclude
            paths_to_exempt: File paths to exempt
            max_matches_per_snapshot: Max matches per snapshot

        Returns:
            Full GraphQL response dictionary

        Raises:
            GraphQLQueryException: If no IOCs provided or query fails
        """
        indicators = self._build_ioc_list(advance_ioc_json, ioc_type, ioc_value)
        if not indicators:
            raise GraphQLQueryException(
                "At least one of the following is required: the Advanced IOC parameter, "
                "or the combination of IOC Type and IOC Value parameters.",
            )

        base_config: Dict[str, Any] = {
            "name": scan_name,
            "threatHuntType": "THREAT_HUNT_V2",
            "ioc": {"iocList": {"indicatorsOfCompromise": indicators}},
            "snapshotScanLimit": {"scanConfig": {}},
        }

        # Build file scan criteria
        file_scan_criteria = self._build_file_scan_criteria(
            min_file_size,
            max_file_size,
            paths_to_include,
            paths_to_exclude,
            paths_to_exempt,
        )
        if file_scan_criteria:
            base_config["fileScanCriteria"] = file_scan_criteria

        # Build scan config
        scan_config = self._build_scan_config(start_date, end_date, max_snapshots_per_object)
        if scan_config:
            base_config["snapshotScanLimit"] = {"scanConfig": scan_config}

        if max_matches_per_snapshot:
            base_config["maxMatchesPerSnapshot"] = max_matches_per_snapshot

        variables = {"input": {"baseConfig": base_config, "objectFids": object_id}}

        payload = json.dumps({"query": START_BULK_THREAT_HUNT_MUTATION, "variables": variables})

        return self._make_rest_call(
            ADVANCE_IOC_SCAN_ACTION_IDENTIFIER, "POST", self.graphql_url, data=payload
        )

    def get_ioc_scan_results(self, hunt_id: str) -> Dict[str, Any]:
        """Retrieve threat hunt details and metrics.

        Args:
            hunt_id: Threat hunt ID

        Returns:
            GraphQL response with threatHuntDetailV2 and metrics

        Raises:
            GraphQLQueryException: If hunt_id invalid or query fails
        """
        variables = {"huntId": hunt_id}

        payload = json.dumps({"query": THREAT_HUNT_DETAILS_V2_QUERY, "variables": variables})

        response = self._make_rest_call(
            IOC_SCAN_RESULTS_ACTION_IDENTIFIER, "POST", self.graphql_url, data=payload
        )

        return response

    def list_object_snapshots(
        self,
        object_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        snapshot_types: Optional[List[str]] = None,
        limit: Optional[int] = None,
        next_page_token: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List snapshots for a given object with optional filters and pagination.

        Args:
            object_id (str): The object ID (snappableId) to retrieve snapshots for
            start_date (str, optional): Start date for time range filter
            end_date (str, optional): End date for time range filter
            snapshot_types (List[str], optional): List of snapshot types to filter
            limit (int, optional): Number of results to retrieve (default: 50, max: 1000)
            next_page_token (str, optional): Cursor for pagination
            sort_order (str, optional): Sort order - "Asc" or "Desc" (default: "Asc")

        Returns:
            Dict[str, Any]: The full GraphQL response containing snapshots and pageInfo

        Raises:
            GraphQLQueryException: If object_id is invalid or response is malformed
            InvalidIntegerException: If limit is invalid
        """
        variables: Dict[str, Any] = {
            "snappableId": object_id,
            "first": limit,
            "sortBy": "CREATION_TIME",
        }

        if sort_order:
            sort_order_upper = sort_order.upper()
            if sort_order_upper == "DESC":
                variables["sortOrder"] = "DESC"
            else:
                variables["sortOrder"] = "ASC"

        if next_page_token:
            variables["after"] = next_page_token

        if start_date or end_date:
            time_range: Dict[str, str] = {}
            if start_date:
                time_range["start"] = start_date
            if end_date:
                time_range["end"] = end_date
            variables["timeRange"] = time_range

        if snapshot_types:
            snapshot_types = [snapshot_type.upper() for snapshot_type in snapshot_types]
            variables["snapshotFilter"] = [
                {"field": "SNAPSHOT_TYPE", "typeFilters": snapshot_types}
            ]

        payload = json.dumps({"query": OBJECT_SNAPSHOTS_QUERY, "variables": variables})

        return self._make_rest_call(
            LIST_OBJECT_SNAPSHOTS_ACTION_IDENTIFIER,
            "POST",
            self.graphql_url,
            data=payload,
        )

    def _build_sonar_filters(
        self,
        object_id: str,
        file_name: Optional[str],
        file_path: Optional[str],
        user_id: Optional[str],
        include_whitelisted: Optional[str],
    ) -> Dict[str, Any]:
        """
        Build filters for Sonar file contexts query.

        Args:
            object_id: The object ID
            file_name: File name to search for
            file_path: Standard file path to filter with
            user_id: User ID to filter with
            include_whitelisted: Include whitelisted results

        Returns:
            Dictionary of filters
        """
        filters: Dict[str, Any] = {"fileType": "HITS"}

        if file_name:
            filters["searchText"] = file_name

        if file_path:
            filters["snappablePaths"] = [{"snappableFid": object_id, "stdPath": file_path}]

        if user_id:
            filters["sids"] = [user_id]

        if include_whitelisted is not None:
            if include_whitelisted.lower() == "true":
                filters["whitelistEnabled"] = False
            elif include_whitelisted.lower() == "false":
                filters["whitelistEnabled"] = True

        return filters

    def _build_sonar_sort_config(
        self, sort_by: Optional[str], sort_order: Optional[str]
    ) -> Dict[str, str]:
        """
        Build sort configuration for Sonar file contexts query.

        Args:
            sort_by: Field to sort by
            sort_order: Sort order (ASC or DESC)

        Returns:
            Dictionary with sort configuration
        """
        sort_config: Dict[str, str] = {}

        # Set sort by field
        sort_config["sortBy"] = sort_by.upper() if sort_by else "HITS"

        # Set sort order
        if sort_order:
            sort_order_upper = sort_order.upper()
            sort_config["sortOrder"] = (
                sort_order_upper
                if sort_order_upper in SORT_ORDER_ENUM
                else DEFAULT_SONAR_FILE_SORT_ORDER
            )
        else:
            sort_config["sortOrder"] = DEFAULT_SONAR_FILE_SORT_ORDER

        return sort_config

    def list_sonar_file_contexts(
        self,
        object_id: str,
        snapshot_id: str,
        file_name: Optional[str] = None,
        file_path: Optional[str] = None,
        user_id: Optional[str] = None,
        include_whitelisted: Optional[str] = None,
        limit: Optional[int] = None,
        next_page_token: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
        timezone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List Sonar file contexts for a given object and snapshot with optional filters.

        Args:
            object_id (str): The object ID (snappableFid)
            snapshot_id (str): The snapshot ID (snapshotFid)
            file_name (str, optional): File name to search for
            file_path (str, optional): Standard file path to filter with
            user_id (str, optional): User ID to filter with
            include_whitelisted (str, optional): Include whitelisted results ("True"/"False")
            limit (int, optional): Number of results to retrieve (default: 50)
            next_page_token (str, optional): Cursor for pagination
            sort_by (str, optional): Field to sort by
            sort_order (str, optional): Sort order - "ASC" or "DESC" (default: "DESC")
            timezone (str, optional): Timezone for the query (default: "UTC")

        Returns:
            Dict[str, Any]: The full GraphQL response containing file results and pageInfo

        Raises:
            GraphQLQueryException: If required parameters are invalid or response is malformed
            InvalidIntegerException: If limit is invalid
        """
        variables: Dict[str, Any] = {
            "snappableFid": object_id,
            "snapshotFid": snapshot_id,
            "first": limit,
            "timezone": DEFAULT_TIMEZONE,
        }

        if next_page_token:
            variables["after"] = next_page_token

        # Build filters
        filters = self._build_sonar_filters(
            object_id, file_name, file_path, user_id, include_whitelisted
        )
        variables["filters"] = filters

        # Build sort configuration
        sort_config = self._build_sonar_sort_config(sort_by, sort_order)
        variables["sort"] = sort_config

        payload = json.dumps({"query": SONAR_FILE_CONTEXTS_QUERY, "variables": variables})

        return self._make_rest_call(
            LIST_SONAR_FILE_CONTEXTS_ACTION_IDENTIFIER,
            "POST",
            self.graphql_url,
            data=payload,
        )

    def _build_list_events_filters(
        self,
        activity_statuses: Optional[List[str]],
        activity_types: Optional[List[str]],
        severities: Optional[List[str]],
        object_name: Optional[str],
        object_types: Optional[List[str]],
        cluster_ids: Optional[List[str]],
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> Dict[str, Any]:
        """
        Build filters for list events query.

        Args:
            activity_statuses: Filter by activity statuses
            activity_types: Filter by activity types
            severities: Filter by severities
            object_name: Filter by object name
            object_types: Filter by object types
            cluster_ids: Filter by cluster IDs
            start_date: Start date for filtering
            end_date: End date for filtering

        Returns:
            Dictionary of filters
        """
        filters: Dict[str, Any] = {}

        if activity_statuses:
            filters["lastActivityStatus"] = [status.upper() for status in activity_statuses]

        if activity_types and len(activity_types) > 0:
            filters["lastActivityType"] = [
                activity_type.upper() for activity_type in activity_types
            ]

        if severities and len(severities) > 0:
            filters["severity"] = [severity.upper() for severity in severities]

        if object_name:
            filters["objectName"] = object_name

        if object_types and len(object_types) > 0:
            filters["objectType"] = [obj_type.upper() for obj_type in object_types]

        if cluster_ids:
            filters["clusterId"] = cluster_ids[0] if len(cluster_ids) == 1 else cluster_ids

        if start_date:
            filters["lastUpdatedTimeGt"] = start_date

        if end_date:
            filters["lastUpdatedTimeLt"] = end_date

        return filters

    def _build_list_events_sort_config(
        self, sort_by: Optional[str], sort_order: Optional[str]
    ) -> Dict[str, str]:
        """
        Build sort configuration for list events query.

        Args:
            sort_by: Field to sort by
            sort_order: Sort order (ASC or DESC)

        Returns:
            Dictionary with sort configuration
        """
        sort_config: Dict[str, str] = {}

        if sort_by:
            sort_config["sortBy"] = sort_by.upper().replace(" ", "_")

        if sort_order:
            if sort_order.upper() in SORT_ORDER_ENUM:
                sort_config["sortOrder"] = sort_order.upper()
            else:
                sort_config["sortOrder"] = DEFAULT_SONAR_FILE_SORT_ORDER

        return sort_config

    def list_events(
        self,
        activity_statuses: Optional[List[str]] = None,
        activity_types: Optional[List[str]] = None,
        severities: Optional[List[str]] = None,
        object_name: Optional[str] = None,
        object_types: Optional[List[str]] = None,
        cluster_ids: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
        limit: Optional[int] = None,
        next_page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List events with optional filters and pagination.

        Args:
            activity_statuses (List[str], optional): Filter by activity statuses
            activity_types (List[str], optional): Filter by activity types
            severities (List[str], optional): Filter by severities
            object_name (str, optional): Filter by object name
            object_types (List[str], optional): Filter by object types
            cluster_ids (List[str], optional): Filter by cluster IDs
            start_date (str, optional): Start date for filtering (lastUpdatedTimeGt)
            end_date (str, optional): End date for filtering (lastUpdatedTimeLt)
            sort_by (str, optional): Field to sort by
            sort_order (str, optional): Sort order - "Asc" or "Desc"
            limit (int, optional): Number of results to retrieve
            next_page_token (str, optional): Cursor for pagination

        Returns:
            Dict[str, Any]: The full GraphQL response containing events and pageInfo

        Raises:
            GraphQLQueryException: If response is malformed
        """
        variables: Dict[str, Any] = {
            "first": limit,
        }

        if next_page_token:
            variables["after"] = next_page_token

        filters = self._build_list_events_filters(
            activity_statuses,
            activity_types,
            severities,
            object_name,
            object_types,
            cluster_ids,
            start_date,
            end_date,
        )
        if filters:
            variables["filters"] = filters

        sort_config = self._build_list_events_sort_config(sort_by, sort_order)
        variables.update(sort_config)

        payload = json.dumps({"query": LIST_EVENTS_QUERY, "variables": variables})

        return self._make_rest_call(
            LIST_EVENTS_ACTION_IDENTIFIER,
            "POST",
            self.graphql_url,
            data=payload,
        )

    def get_cdm_cluster_location(self, cluster_id: str) -> Dict[str, Any]:
        """
        Get the CDM GeoLocation of a CDM Cluster.

        Args:
            cluster_id (str): The ID of the CDM cluster

        Returns:
            Dict[str, Any]: The full GraphQL response containing cluster location

        Raises:
            GraphQLQueryException: If cluster_id is invalid or response is malformed
        """
        variables = {"filter": {"id": cluster_id}}

        payload = json.dumps({"query": CDM_CLUSTER_LOCATION_QUERY, "variables": variables})

        return self._make_rest_call(
            GET_CDM_CLUSTER_LOCATION_ACTION_IDENTIFIER,
            "POST",
            self.graphql_url,
            data=payload,
        )

    def get_cdm_cluster_connection_state(self, cluster_id: str) -> Dict[str, Any]:
        """
        Get the CDM Connection State of a CDM Cluster.

        Args:
            cluster_id (str): The ID of the CDM cluster

        Returns:
            Dict[str, Any]: The full GraphQL response containing cluster connection state

        Raises:
            GraphQLQueryException: If cluster_id is invalid or response is malformed
        """
        variables = {"filter": {"id": cluster_id}}

        payload = json.dumps({"query": CDM_CLUSTER_CONNECTION_STATE_QUERY, "variables": variables})

        return self._make_rest_call(
            GET_CDM_CLUSTER_CONNECTION_STATE_ACTION_IDENTIFIER,
            "POST",
            self.graphql_url,
            data=payload,
        )

    def get_sonar_policy_objects_list(self, day: str, timezone: str) -> Dict[str, Any]:
        """
        Get the list of Sonar policy objects for a specific day.

        Args:
            day (str): The date to search for (format: YYYY-MM-DD)
            timezone (str): The timezone for the query

        Returns:
            Dict[str, Any]: The full GraphQL response containing policy objects list

        Raises:
            GraphQLQueryException: If response is malformed
        """
        variables = {"day": day, "timezone": timezone}

        payload = json.dumps({"query": SONAR_POLICY_OBJECTS_LIST_QUERY, "variables": variables})

        return self._make_rest_call(
            GET_SONAR_SENSITIVE_HITS_ACTION_IDENTIFIER,
            "POST",
            self.graphql_url,
            data=payload,
        )

    def get_sonar_object_detail(self, object_name: str, day: str, timezone: str) -> Dict[str, Any]:
        """
        Get detailed information about a Sonar policy object by name.
        This method internally calls two GraphQL queries:
        1. get_sonar_policy_objects_list to find the object by name
        2. SONAR_OBJECT_DETAIL_QUERY to get the object details

        Args:
            object_name (str): The name of the Rubrik object
            day (str): The date to search for (format: YYYY-MM-DD)
            timezone (str): The timezone for the query

        Returns:
            Dict[str, Any]: The full GraphQL response containing object details

        Raises:
            GraphQLQueryException: If object not found or response is malformed
        """
        # First GraphQL query: Get policy objects list
        objects_list_response = self.get_sonar_policy_objects_list(day, timezone)

        self.siemplify.LOGGER.info("Processing policy objects list")

        data = objects_list_response.get("data", {})
        policy_objs = data.get("policyObjs", {})
        edges = policy_objs.get("edges", [])

        # Find the matching object by name
        matching_object = None
        for edge in edges:
            node = edge.get("node", {})
            snappable = node.get("snappable", {})
            if snappable.get("name") == object_name:
                matching_object = node
                break

        if not matching_object:
            raise ItemNotFoundException(f"No object found with name: {object_name}")

        snappable_fid = matching_object.get("snappable", {}).get("id")
        snapshot_fid = matching_object.get("snapshotFid")

        if not snappable_fid or not snapshot_fid:
            raise ItemNotFoundException(f"No snapshots available for this object: {object_name}")

        self.siemplify.LOGGER.info(
            f"Retrieving object details for snappableFid: "
            f"{snappable_fid}, snapshotFid: {snapshot_fid}"
        )

        # Second GraphQL query: Get object details
        variables = {"snappableFid": snappable_fid, "snapshotFid": snapshot_fid}

        payload = json.dumps({"query": SONAR_OBJECT_DETAIL_QUERY, "variables": variables})

        return self._make_rest_call(
            GET_SONAR_SENSITIVE_HITS_ACTION_IDENTIFIER,
            "POST",
            self.graphql_url,
            data=payload,
        )
