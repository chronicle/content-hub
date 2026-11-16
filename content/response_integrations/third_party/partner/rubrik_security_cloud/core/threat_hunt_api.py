"""RSC threat hunt (IOC scan) client methods.

Mixed into APIManager, which supplies the HTTP session and REST call handling
these methods rely on.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .constants import (
    ADVANCE_IOC_SCAN_ACTION_IDENTIFIER,
    IOC_SCAN_RESULTS_ACTION_IDENTIFIER,
    IOC_TYPE_MAP,
    TURBO_IOC_SCAN_ACTION_IDENTIFIER,
)
from .graphql_queries import (
    START_BULK_THREAT_HUNT_MUTATION,
    START_TURBO_THREAT_HUNT_MUTATION,
    THREAT_HUNT_DETAILS_V2_QUERY,
)
from .rubrik_exceptions import GraphQLQueryException


class ThreatHuntApiMixin:
    """Turbo / advanced IOC scan calls for APIManager."""

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
