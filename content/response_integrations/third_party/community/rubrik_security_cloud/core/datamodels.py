from __future__ import annotations

from typing import Any, Dict, List, Optional


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
