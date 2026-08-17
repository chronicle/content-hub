from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from .constants import CLASSIFICATION_ACTIVITY_MESSAGE_FILTER


def _iso_to_unix_ms(iso_str: str) -> int:
    """Convert ISO 8601 timestamp to Unix epoch milliseconds (AlertInfo requirement)."""
    if not iso_str:
        return 0
    try:
        return int(datetime.fromisoformat(iso_str.replace("Z", "+00:00")).timestamp() * 1000)
    except Exception:
        return 0


class TurboIOCScanDatamodel:
    """
    Data model for Turbo IOC Scan results.
    Used to format and structure the data for output in the SOAR interface.

    Args:
        hunt_id (str): The ID of the created threat hunt scan
    """

    def __init__(self, hunt_id: str) -> None:
        self.hunt_id = hunt_id

    def to_csv(self) -> List[Dict[str, str]]:
        return [{"Turbo Threat Hunt ID": self.hunt_id}]


class AdvanceIOCScanDatamodel:
    """
    Data model for Advanced IOC Scan results.
    Accepts a list of hunts as returned by startBulkThreatHunt.
    """

    def __init__(self, hunts: Optional[List[Dict[str, Any]]]) -> None:
        self.hunts = hunts or []

    def to_csv(self) -> List[Dict[str, str]]:
        result = []
        for h in self.hunts:
            result.append({
                "Advance Threat Hunt ID": (h or {}).get("huntId") or "",
                "Hunt Name": (h or {}).get("huntName") or "",
                "Status": (h or {}).get("status") or "",
            })
        return result


class IOCScanResultsDatamodel:
    """
    Data model for IOC Scan Results (Threat Hunt Details).
    Displays: Hunt Name, Hunt Type, Status, IOC Details, Object Metrics,
    Scan Metrics, Start Time, End Time
    """

    def __init__(
        self,
        threat_hunt_detail: Optional[Dict[str, Any]],
        threat_hunt_metrics: Optional[Dict[str, Any]],
    ) -> None:
        self.detail = threat_hunt_detail or {}
        self.metrics = threat_hunt_metrics or {}
        self.base_config = self.detail.get("baseConfig") or {}

    def _format_ioc_details(self) -> str:
        """Format IOC details as a readable string"""
        ioc = self.base_config.get("ioc") or {}
        ioc_list = (ioc.get("iocList") or {}).get("indicatorsOfCompromise") or []
        if not ioc_list:
            return "N/A"
        ioc_strings = []
        for indicator in ioc_list:
            kind = indicator.get("iocKind", "")
            value = indicator.get("iocValue", "")
            ioc_strings.append(f"{kind}: {value}")
        return ",".join(ioc_strings)

    def _format_object_metrics(self) -> str:
        """Format object metrics as a readable string"""
        scanned = self.metrics.get("totalObjectsScanned", 0)
        affected = self.metrics.get("totalAffectedObjects", 0)
        unaffected = self.metrics.get("totalUnaffectedObjects", 0)
        unscannable = self.metrics.get("totalObjectsUnscannable", 0)
        return (
            f"Scanned:{scanned}|Affected:{affected}|"
            f"Unaffected:{unaffected}|Unscannable:{unscannable}"
        )

    def _format_scan_metrics(self) -> str:
        """Format scan metrics as a readable string"""
        matched = self.detail.get("totalMatchedSnapshots", 0)
        scanned = self.detail.get("totalScannedSnapshots", 0)
        unique_matches = self.detail.get("totalUniqueFileMatches", 0)
        return (
            f"MatchedSnapshots:{matched}|ScannedSnapshots:{scanned}|UniqueMatches:{unique_matches}"
        )

    def to_csv(self) -> List[Dict[str, str]]:
        hunt_name = self.base_config.get("name", "N/A")
        hunt_type = self.base_config.get("threatHuntType", "N/A")
        status = self.detail.get("status", "N/A")
        ioc_details = self._format_ioc_details()
        object_metrics = self._format_object_metrics()
        scan_metrics = self._format_scan_metrics()
        start_time = self.detail.get("startTime", "N/A")
        end_time = self.detail.get("endTime", "N/A")

        return [
            {
                "Hunt Name": hunt_name,
                "Hunt Type": hunt_type,
                "Status": status,
                "IOC Details": ioc_details,
                "Object Metrics": object_metrics,
                "Scan Metrics": scan_metrics,
                "Start Time": start_time,
                "End Time": end_time,
            }
        ]


class ObjectSnapshotsDatamodel:
    """
    Data model for Object Snapshots list.
    Displays: Snapshot ID, Creation Date, Cluster Name, SLA Domain Name
    """

    def __init__(self, snapshots_list: List[Dict[str, Any]], page_info: Dict[str, Any]) -> None:
        self.snapshots = snapshots_list or []
        self.page_info = page_info or {}

    def to_csv(self) -> List[Dict[str, str]]:
        result = []

        for snapshot in self.snapshots:
            node = snapshot.get("node", {})
            snapshot_id = node.get("id", "N/A")
            creation_date = node.get("date", "N/A")

            cluster_name = "N/A"
            cluster = node.get("cluster")
            if cluster:
                cluster_name = cluster.get("name", "N/A")

            sla_domain_name = "N/A"
            sla_domain = node.get("slaDomain")
            if sla_domain:
                sla_domain_name = sla_domain.get("name", "N/A")

            result.append({
                "Snapshot ID": snapshot_id,
                "Creation Date": creation_date,
                "Cluster Name": cluster_name,
                "SLA Domain Name": sla_domain_name,
            })

        return result


class SonarFileContextsDatamodel:
    """
    Data model for Sonar File Contexts list.
    Displays: File Name, File Size in Bytes, Total Sensitive Hits,
    Daily Hits Change, File Path, Access Type, Last Access Time,
    Last Modified Time
    """

    def __init__(self, file_results: List[Dict[str, Any]], page_info: Dict[str, Any]) -> None:
        self.file_results = file_results or []
        self.page_info = page_info or {}

    def to_csv(self) -> List[Dict[str, str]]:
        result = []

        for file_result in self.file_results:
            node = file_result.get("node", {})

            file_name = node.get("filename", "N/A")
            file_size = node.get("size", 0)

            hits = node.get("hits", {})
            total_hits = hits.get("violations", 0)
            daily_hits_change = hits.get("violationsDelta", 0)

            file_path = node.get("stdPath", "N/A")
            access_type = node.get("openAccessType", "N/A")
            last_access_time = node.get("lastAccessTime", "N/A")
            last_modified_time = node.get("lastModifiedTime", "N/A")

            result.append({
                "File Name": file_name,
                "File Size in Bytes": str(file_size),
                "Total Sensitive Hits": str(total_hits),
                "Daily Hits Change": str(daily_hits_change),
                "File Path": file_path,
                "Access Type": access_type,
                "Last Access Time": str(last_access_time),
                "Last Modified Time": str(last_modified_time),
            })

        return result


class ListEventsDatamodel:
    """
    Data model for List Events.
    Displays: Event ID, Activity Series ID, Cluster ID, Object ID,
    Object Name, Severity, Progress, Start Time
    """

    def __init__(self, events_list: List[Dict[str, Any]], page_info: Dict[str, Any]) -> None:
        self.events = events_list or []
        self.page_info = page_info or {}

    def to_csv(self) -> List[Dict[str, str]]:
        result = []

        for event in self.events:
            node = event.get("node", {})
            event_id = node.get("id", "N/A")
            activity_series_id = node.get("activitySeriesId", "N/A")

            cluster_id = "N/A"
            cluster = node.get("cluster")
            if cluster:
                cluster_id = cluster.get("id", "N/A")

            object_id = node.get("objectId", "N/A")
            object_name = node.get("objectName", "N/A")
            severity = node.get("severity", "N/A")
            progress = node.get("progress", "N/A")
            start_time = node.get("startTime", "N/A")

            result.append({
                "Event ID": str(event_id),
                "Activity Series ID": activity_series_id,
                "Cluster ID": cluster_id,
                "Object ID": object_id,
                "Object Name": object_name,
                "Severity": severity,
                "Progress": progress,
                "Start Time": start_time,
            })

        return result


class CDMClusterLocationDatamodel:
    """
    Data model for CDM Cluster Location.
    Displays: Cluster ID, Location
    """

    def __init__(self, cluster_id: str, nodes: List[Dict[str, Any]]) -> None:
        self.cluster_id = cluster_id
        self.nodes = nodes or []

    def to_csv(self) -> List[Dict[str, str]]:
        result = []

        for node in self.nodes:
            geo_location = node.get("geoLocation", {})
            location = geo_location.get("address", "N/A")

            result.append({
                "Cluster ID": self.cluster_id,
                "Location": location,
            })

        return result


class CDMClusterConnectionStateDatamodel:
    """
    Data model for CDM Cluster Connection State.
    Displays: Cluster ID, Connection State
    """

    def __init__(self, cluster_id: str, nodes: List[Dict[str, Any]]) -> None:
        self.cluster_id = cluster_id
        self.nodes = nodes or []

    def to_csv(self) -> List[Dict[str, str]]:
        result = []

        for node in self.nodes:
            state = node.get("state", {})
            connection_state = state.get("connectedState", "N/A")

            result.append({
                "Cluster ID": self.cluster_id,
                "Connection State": connection_state,
            })

        return result


class SonarSensitiveHitsDatamodel:
    """
    Data model for Sonar Sensitive Hits.
    Displays: Policy Object ID, Total Hits
    """

    def __init__(self, policy_obj: Optional[Dict[str, Any]]) -> None:
        self.policy_obj = policy_obj or {}

    def to_csv(self) -> List[Dict[str, Any]]:
        policy_object_id = self.policy_obj.get("id", "N/A")
        root_file_result = self.policy_obj.get("rootFileResult", {})
        hits = root_file_result.get("hits", {})
        total_hits = hits.get("totalHits", 0)
        analyzer_group_results = root_file_result.get("analyzerGroupResults", [])

        results = []

        for group_result in analyzer_group_results:
            analyzer_group = group_result.get("analyzerGroup", {})
            analyzer_group_name = analyzer_group.get("name", "N/A")

            analyzer_results = group_result.get("analyzerResults", [])

            for analyzer_result in analyzer_results:
                analyzer = analyzer_result.get("analyzer", {})
                analyzer_name = analyzer.get("name", "N/A")

                results.append({
                    "Policy Object ID": policy_object_id,
                    "Analyzer Group Name": analyzer_group_name,
                    "Analyzer Name": analyzer_name,
                    "Total Hits": str(total_hits),
                })

        if not results:
            results.append({
                "Policy Object ID": policy_object_id,
                "Analyzer Group Name": "N/A",
                "Analyzer Name": "N/A",
                "Total Hits": str(total_hits),
            })

        return results


class BaseModel:
    """Base model for all Rubrik datamodels."""

    def __init__(self, raw_data: Dict[str, Any]) -> None:
        self.raw_data = raw_data

    def to_json(self) -> Dict[str, Any]:
        """Return the raw data dict."""
        return self.raw_data

    @staticmethod
    def _stringify(value: Any) -> str:
        """Convert any value to a string suitable for CSV display."""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value)
        except TypeError:
            return str(value)


class DSPMViolation(BaseModel):
    """Model for a single DSPM violation from the list query."""

    def __init__(self, raw_data: Dict[str, Any]) -> None:
        super().__init__(raw_data)
        self.violation_id: str = raw_data.get("policyViolationId", "")
        self.status: str = raw_data.get("status", "")
        self.created_at: str = raw_data.get("createdAt", "")
        self.last_updated_at: str = raw_data.get("lastUpdatedAt", "")
        self.severity: str = raw_data.get("violationSeverity", "")
        policy = raw_data.get("policy") or {}
        self.policy_name: str = policy.get("name", "")
        self.policy_category: str = policy.get("policyCategory", "")
        self.policy_severity: str = policy.get("policySeverity", "")
        self.resource_id: str = raw_data.get("resourceId", "")
        metadata = (raw_data.get("resourceMetadata") or {}).get("metadata") or {}
        self.object_name: str = metadata.get("name", "")
        self.object_type: str = metadata.get("objectType", "")
        details = raw_data.get("details") or {}
        self.snapshot_id: str = details.get("snapshotId", "")

    def to_csv(self) -> Dict[str, Any]:
        """Return a flat dict suitable for SOAR data table display."""
        return {
            "Violation ID": self.violation_id,
            "Status": self.status,
            "Severity": self.severity,
            "Policy Name": self.policy_name,
            "Category": self.policy_category,
            "Resource Name": self.object_name,
            "Object Type": self.object_type,
            "Snapshot ID": self.snapshot_id,
            "Detected At": self.created_at,
            "Last Updated": self.last_updated_at,
        }


class DSPMViolationDetails(BaseModel):
    """Model for the full details of a single DSPM violation."""

    def __init__(self, raw_data: Dict[str, Any]) -> None:
        super().__init__(raw_data)
        self.violation_id: str = raw_data.get("policyViolationId", "")
        self.status: str = raw_data.get("status", "")
        self.severity: str = raw_data.get("violationSeverity", "")
        self.resource_id: str = raw_data.get("resourceId", "")
        policy = raw_data.get("policy") or {}
        self.policy_name: str = policy.get("name", "")
        self.policy_category: str = policy.get("policyCategory", "")
        details = raw_data.get("details") or {}
        self.snapshot_id: str = details.get("snapshotId", "")
        self.total_sensitive_hits: int = details.get("violatedSensitiveHits", 0) or 0
        metadata = (raw_data.get("resourceMetadata") or {}).get("metadata") or {}
        self.object_type: str = metadata.get("objectType", "")
        self.platform: str = metadata.get("platform", "")
        self.physical_host: str = metadata.get("physicalHost", "")

    def to_csv(self) -> Dict[str, Any]:
        """Return a flat dict suitable for SOAR data table display."""
        return {
            "Violation Id": self.violation_id,
            "Status": self.status,
            "Severity": self.severity,
            "Policy Name": self.policy_name,
            "Policy Category": self.policy_category,
            "Snapshot Id": self.snapshot_id,
            "Resource Id": self.resource_id,
            "Object Type": self.object_type,
            "Platform": self.platform,
            "Physical Host": self.physical_host,
            "Total Sensitive Hits": self.total_sensitive_hits,
        }


class IRViolation(BaseModel):
    """Model for a single IR violation from the list query."""

    def __init__(self, raw_data: Dict[str, Any]) -> None:
        super().__init__(raw_data)
        self.violation_id: str = raw_data.get("policyViolationId", "")
        self.status: str = raw_data.get("status", "")
        self.severity: str = raw_data.get("violationSeverity", "")
        self.created_at: str = raw_data.get("createdAt", "")
        policy = raw_data.get("policy") or {}
        self.policy_name: str = policy.get("name", "")
        self.policy_category: str = policy.get("policyCategory", "")
        metadata = (raw_data.get("resourceMetadata") or {}).get("metadata") or {}
        self.display_name: str = metadata.get("displayName", "")
        self.idp_type: str = metadata.get("idpType", "")
        self.user_principal_name: str = metadata.get("userPrincipalName", "")

    def to_csv(self) -> Dict[str, Any]:
        """Return a flat dict suitable for SOAR data table display."""
        return {
            "Violation ID": self.violation_id,
            "Status": self.status,
            "Severity": self.severity,
            "Policy Name": self.policy_name,
            "Category": self.policy_category,
            "Identity (Display Name)": self.display_name,
            "User Principal Name": self.user_principal_name,
            "IDP Type": self.idp_type,
            "Detected At": self.created_at,
        }


class IRViolationDetails(BaseModel):
    """Model for the full details of a single IR violation."""

    def __init__(self, raw_data: Dict[str, Any]) -> None:
        super().__init__(raw_data)
        self.violation_id: str = raw_data.get("policyViolationId", "")
        self.status: str = raw_data.get("status", "")
        self.severity: str = raw_data.get("violationSeverity", "")
        self.resource_id: str = raw_data.get("resourceId", "")
        self.resource_type: str = raw_data.get("resourceType", "")
        policy = raw_data.get("policy") or {}
        self.policy_name: str = policy.get("name", "")
        self.policy_category: str = policy.get("policyCategory", "")
        self.manual_remediation: str = policy.get("manualRemediationProcess", "")
        metadata = (raw_data.get("resourceMetadata") or {}).get("metadata") or {}
        self.display_name: str = metadata.get("displayName", "")
        self.idp_type: str = metadata.get("idpType", "")
        self.principal_type: str = metadata.get("principalType", "")
        self.user_principal_name: str = metadata.get("userPrincipalName", "")

    def to_csv(self) -> Dict[str, Any]:
        """Return a flat dict suitable for SOAR data table display."""
        return {
            "Violation ID": self.violation_id,
            "Status": self.status,
            "Severity": self.severity,
            "Policy Name": self.policy_name,
            "Policy Category": self.policy_category,
            "Resource ID": self.resource_id,
            "Resource Type": self.resource_type,
            "Display Name": self.display_name,
            "User Principal Name": self.user_principal_name,
            "IDP Type": self.idp_type,
            "Principal Type": self.principal_type,
            "Remediation Guidance": self.manual_remediation,
        }


class FileEntry(BaseModel):
    """Model for a single file entry from the violation file list query."""

    def __init__(self, raw_data: Dict[str, Any]) -> None:
        super().__init__(raw_data)
        self.filename: str = raw_data.get("filename", "")
        self.native_path: str = raw_data.get("nativePath", "")
        self.directory: str = raw_data.get("directory", "")
        self.size: int = raw_data.get("size", 0) or 0
        self.last_modified_time: str = raw_data.get("lastModifiedTime", "")
        self.last_access_time: str = raw_data.get("lastAccessTime", "")
        hits = raw_data.get("hits") or {}
        self.total_hits: int = hits.get("totalHits", 0) or 0
        sensitive_hits = raw_data.get("sensitiveHits") or {}
        high_risk = sensitive_hits.get("highRiskHits") or {}
        self.high_risk_hits: int = high_risk.get("violatedHits", 0) or 0
        medium_risk = sensitive_hits.get("mediumRiskHits") or {}
        self.medium_risk_hits: int = medium_risk.get("violatedHits", 0) or 0
        low_risk = sensitive_hits.get("lowRiskHits") or {}
        self.low_risk_hits: int = low_risk.get("violatedHits", 0) or 0
        self.open_access_type: str = raw_data.get("openAccessType", "")
        self.staleness_type: str = raw_data.get("stalenessType", "")

    def to_csv(self) -> Dict[str, Any]:
        """Return a flat dict suitable for SOAR data table display."""
        return {
            "File Name": self.filename,
            "Path": self.native_path,
            "Directory": self.directory,
            "Size (bytes)": self.size,
            "Last Modified": self.last_modified_time,
            "Last Accessed": self.last_access_time,
            "Total Hits": self.total_hits,
            "High Risk Hits": self.high_risk_hits,
            "Medium Risk Hits": self.medium_risk_hits,
            "Low Risk Hits": self.low_risk_hits,
            "Exposure Type": self.open_access_type,
            "Staleness": self.staleness_type,
        }


class UserFile:
    """Internal model for a file entry from allUserFiles (async polling only)."""

    def __init__(self, raw_data: Dict[str, Any]) -> None:
        self.external_id: Optional[str] = raw_data.get("externalId")
        self.filename: str = raw_data.get("filename", "")
        self.file_type: str = raw_data.get("type", "")
        self.state: str = raw_data.get("state", "")
        self.created_at: str = raw_data.get("createdAt", "")

    def is_ready(self) -> bool:
        return self.state == "READY"

    def is_failed(self) -> bool:
        return self.state == "FAILED"


class RubrikClassificationAlertDatamodel:
    """Data model for Rubrik Classification alerts in connectors."""

    def __init__(
        self, event_node: Dict[str, Any], policy_obj: Dict[str, Any], snapshot_id: str
    ) -> None:
        self.event_node = event_node
        self.policy_obj = policy_obj
        self.snapshot_id = snapshot_id

    def get_alert_info(
        self,
        alert_info: Any,
        environment_common: Any,
        event_field_parameter: str = "",
        product_field_name: str = "",
    ) -> Any:
        """Convert raw data to Siemplify AlertInfo format."""
        activity_series_id = self.event_node.get("activitySeriesId") or self.event_node.get(
            "id", ""
        )
        start_time = self.event_node.get("startTime", "")
        last_updated = self.event_node.get("lastUpdated", start_time)
        object_id = self.event_node.get("objectId", "")
        object_name = self.event_node.get("objectName", "")
        object_type = self.event_node.get("objectType", "")
        cluster_id = (self.event_node.get("cluster") or {}).get("id", "")
        cluster_name = (self.event_node.get("cluster") or {}).get("name", "")
        severity = self.event_node.get("severity", "Info")
        last_activity_type = self.event_node.get("lastActivityType", "Classification")
        last_activity_status = self.event_node.get("lastActivityStatus", "")
        location = self.event_node.get("location", "")
        progress = self.event_node.get("progress", "")
        fid = self.event_node.get("fid", "")

        # activityConnection node fields — select the "Results available" node specifically.
        # Falls back to nodes[0] if the expected message is not found.
        activity_nodes = self.event_node.get("activityConnection", {}).get("nodes", [])
        activity_node = next(
            (
                n for n in activity_nodes
                if CLASSIFICATION_ACTIVITY_MESSAGE_FILTER in n.get("message", "")
            ),
            activity_nodes[0] if activity_nodes else {},
        )
        # Field 1 / 8: individual activity node ID used as ticketId and DisplayId
        activity_node_id = activity_node.get("id", activity_series_id)
        # Field 3 / 5 / 7: message used as Name, RuleGenerator, Description
        message = activity_node.get("message", "")

        # policyObj fields
        root = self.policy_obj.get("rootFileResult", {})
        violations = root.get("hits", {}).get("violations", 0)
        total_hits = root.get("hits", {}).get("totalHits", 0)
        violation_delta = root.get("hits", {}).get("violationsDelta", 0)
        risk_level = self.policy_obj.get("riskLevel", "UNKNOWN")
        share_type = self.policy_obj.get("shareType", "")
        os_type = self.policy_obj.get("osType", "")

        analyzer_groups = [
            ag for ag in (root.get("analyzerGroupResults") or [])
            if (ag.get("hits") or {}).get("violations", 0) > 0
        ]
        policies_violated = ", ".join(
            (ag.get("analyzerGroup") or {}).get("name", "") for ag in analyzer_groups
        ) or risk_level
        policies_applied = ", ".join(
            p.get("name", "") for p in (self.policy_obj.get("policySummaries") or [])
        )

        # Priority from node.severity (Field 10)
        _priority_map = {"Critical": 1, "High": 1, "Warning": 2, "Medium": 2, "Info": 3, "Low": 3}
        priority = _priority_map.get(severity, 2)

        # --- AlertInfo fields (SecOps alert-level mapping) ---
        alert_info.ticket_id = activity_node_id                   # Field 1: ticketId (activityConnection.nodes[0].id)
        alert_info.display_id = activity_node_id
        alert_info.name = message                                  # Field 3: Name
        alert_info.rule_generator = message
        alert_info.description = message
        alert_info.start_time = _iso_to_unix_ms(last_updated)     # Field 6: StartTime (lastUpdated)
        alert_info.end_time = _iso_to_unix_ms(last_updated)
        alert_info.device_product = "RSC"                              # Field 9: DeviceProduct
        alert_info.device_vendor = "Rubrik Security Cloud"
        alert_info.priority = priority                             # Field 10: Priority
        alert_info.environment = environment_common.get_environment(self.event_node)
        alert_info.source_grouping_identifier = activity_series_id
        alert_info.event_field_name = event_field_parameter
        alert_info.source_system_name = product_field_name
        alert_info.event_product = last_activity_type
    
        # --- Event dict (SecOps EventsList — entire merged payload, Field 11) ---
        event = {
            # SecOps mapping fields
            "SourceSystemName":   "Rubrik Security Cloud",         # Field 2
            "DeviceVendor":       "Rubrik Security Cloud",         # Field 4
            "Description":        message,                         # Field 7
            "DisplayId":          activity_node_id,                  # Field 8 (activityConnection.nodes[0].id)
            "eventName":          "ClassficationResultsAvailable",
            "DeviceProduct":      "RSC",                           # Field 9
            "EventProduct":       last_activity_type,              # Field 12
            # SOAR required time fields
            "StartTime":          _iso_to_unix_ms(last_updated),
            "EndTime":            _iso_to_unix_ms(last_updated),
            "Name":               message,
            # activitySeriesConnection node fields
            "activitySeriesId":   activity_series_id,
            "fid":                fid,
            "startTime":          start_time,
            "lastUpdated":        last_updated,
            "lastActivityType":   last_activity_type,
            "lastActivityStatus": last_activity_status,
            "objectId":           object_id,
            "objectName":         object_name,
            "objectType":         object_type,
            "severity":           severity,
            "location":           location,
            "progress":           progress,
            "clusterId":          cluster_id,
            "clusterName":        cluster_name,
            "message":            message,
            # policyObj fields
            "riskLevel":          risk_level,
            "violations":         violations,
            "totalHits":          total_hits,
            "violationsDelta":    violation_delta,
            "snapshotId":         self.snapshot_id,
            "shareType":          share_type,
            "osType":             os_type,
            "policiesViolated":   policies_violated,
            "policiesApplied":    policies_applied,
        }
        alert_info.events = [event]

        return alert_info
