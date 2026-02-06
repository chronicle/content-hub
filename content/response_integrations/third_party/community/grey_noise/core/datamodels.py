from __future__ import annotations
from typing import Dict, Any
from datetime import datetime, timezone
import json

from dateutil import parser
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time
from TIPCommon.transformation import dict_to_flat
from .constants import SEVERITY_MAP, INTEGRATION_NAME, EVENT_TYPE


class BaseModel:
    """Base model for all GreyNoise datamodels."""

    def __init__(self, raw_data: Dict[str, Any]):
        self.raw_data = raw_data

    def to_json(self) -> Dict[str, Any]:
        """Return raw data as JSON."""
        return self.raw_data


class CVEResult(BaseModel):
    """CVE lookup result model with essential fields only."""

    def get_enrichment_data(self) -> Dict[str, Any]:
        """
        Get essential CVE enrichment data for Siemplify entity.

        Returns:
            dict: Key CVE information with GN_ prefix
        """
        details = self.raw_data.get("details", {})
        exploitation_details = self.raw_data.get("exploitation_details", {})
        exploitation_activity = self.raw_data.get("exploitation_activity", {})
        timeline = self.raw_data.get("timeline", {})

        enrichment = {
            "GN_last_enriched": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "GN_Exploit_Found": exploitation_details.get("exploit_found", False),
            "GN_Activity_Seen": exploitation_activity.get("activity_seen", False),
        }

        # Add optional fields only if they exist
        if self.raw_data.get("id"):
            enrichment["GN_CVE_ID"] = self.raw_data["id"]
        if details.get("cve_cvss_score") is not None:
            enrichment["GN_CVSS_Score"] = details["cve_cvss_score"]
        if details.get("vulnerability_description"):
            enrichment["GN_Vulnerability_Description"] = details["vulnerability_description"]
        if timeline.get("cve_published_date"):
            enrichment["GN_CVE_Published_Date"] = timeline["cve_published_date"]
        if exploitation_details.get("epss_score") is not None:
            enrichment["GN_EPSS_Score"] = exploitation_details["epss_score"]
        if exploitation_activity.get("threat_ip_count_1d"):
            enrichment["GN_Threat_IP_Count_1d"] = exploitation_activity["threat_ip_count_1d"]
        if exploitation_activity.get("threat_ip_count_30d"):
            enrichment["GN_Threat_IP_Count_30d"] = exploitation_activity["threat_ip_count_30d"]

        return enrichment

class IPTimelineResult(BaseModel):
    """IP Timeline lookup result model."""

    def get_enrichment_data(self) -> Dict[str, Any]:
        """
        Get essential IP Timeline enrichment data for Siemplify entity.

        Returns:
            dict: Key Timeline information with GN_ prefix
        """
        metadata = self.raw_data.get("metadata", {})
        results = self.raw_data.get("results", [])

        enrichment = {
            "GN_last_enriched": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }

        # Add optional fields only if they exist
        if metadata.get("field"):
            enrichment["GN_Timeline_Field"] = metadata["field"]
        if metadata.get("first_seen"):
            enrichment["GN_Timeline_First_Seen"] = metadata["first_seen"]
        if results:
            enrichment["GN_Timeline_Data"] = json.dumps(results)

        return enrichment


class IPLookupResult(BaseModel):
    """IP Lookup result model for Enterprise tier."""

    def get_enrichment_data(self) -> Dict[str, Any]:
        """
        Get essential IP enrichment data for Siemplify entity (Enterprise).

        Returns:
            dict: Key IP information with GN_ prefix
        """
        bsi = self.raw_data.get("business_service_intelligence", {})
        isi = self.raw_data.get("internet_scanner_intelligence", {})
        metadata = isi.get("metadata", {})

        # Extract tags names
        tags = isi.get("tags", [])
        tag_names = ", ".join([t.get("name", "") for t in tags[:10]])

        # Extract CVEs
        cves = isi.get("cves", [])
        cve_list = ", ".join(cves[:10]) if cves else ""

        enrichment = {
            "GN_last_enriched": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "GN_Classification": isi.get("classification", "unknown"),
            "GN_BOT": isi.get("bot", False),
            "GN_VPN": isi.get("vpn", False),
            "GN_is_business_service": bsi.get("found", False),
            "GN_is_internet_scanner": isi.get("found", False),
        }

        # Add optional fields only if they exist
        if isi.get("first_seen"):
            enrichment["GN_First_Seen"] = isi["first_seen"]
        if isi.get("last_seen"):
            enrichment["GN_Last_Seen"] = isi["last_seen"]
        if isi.get("actor"):
            enrichment["GN_Actor"] = isi["actor"]
        if tag_names:
            enrichment["GN_Tags"] = tag_names
        if cve_list:
            enrichment["GN_CVEs"] = cve_list
        if metadata.get("source_country"):
            enrichment["GN_Country"] = metadata["source_country"]
        if metadata.get("organization"):
            enrichment["GN_Organization"] = metadata["organization"]
        if bsi.get("name"):
            enrichment["GN_business_service_name"] = bsi["name"]
        if bsi.get("trust_level"):
            enrichment["GN_trust_level"] = bsi["trust_level"]

        return enrichment

    def is_found(self) -> bool:
        """Check if IP was found in GreyNoise dataset."""
        bsi = self.raw_data.get("business_service_intelligence", {})
        isi = self.raw_data.get("internet_scanner_intelligence", {})
        return bsi.get("found", False) or isi.get("found", False)

    def is_suspicious(self) -> bool:
        """
        Determine if IP is suspicious based on classification.

        Returns:
            bool: True if classification is 'suspicious' or 'malicious'
        """
        isi = self.raw_data.get("internet_scanner_intelligence", {})
        classification = isi.get("classification", "").lower()
        return classification in ["suspicious", "malicious"]


class QuickLookupResult(BaseModel):
    """Quick IP Lookup result model."""

    def get_enrichment_data(self) -> Dict[str, Any]:
        """
        Get essential Quick Lookup enrichment data for Siemplify entity.

        Returns:
            dict: Key Quick Lookup information with GN_ prefix
        """
        bsi = self.raw_data.get("business_service_intelligence", {})
        isi = self.raw_data.get("internet_scanner_intelligence", {})

        enrichment = {
            "GN_last_enriched": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "GN_is_business_service": bsi.get("found", False),
            "GN_is_internet_scanner": isi.get("found", False),
        }

        # Add optional fields only if they exist
        if bsi.get("trust_level"):
            enrichment["GN_trust_level"] = bsi["trust_level"]
        if isi.get("classification"):
            enrichment["GN_classification"] = isi["classification"]

        return enrichment

    def is_found(self) -> bool:
        """Check if IP has noise data in GreyNoise dataset."""
        bsi = self.raw_data.get("business_service_intelligence", {})
        isi = self.raw_data.get("internet_scanner_intelligence", {})
        return bsi.get("found", False) or isi.get("found", False)

    def is_suspicious(self) -> bool:
        """
        Determine if IP is suspicious based on classification.

        Returns:
            bool: True if classification is 'suspicious' or 'malicious'
        """
        isi = self.raw_data.get("internet_scanner_intelligence", {})
        classification = isi.get("classification", "").lower()
        return classification in ["suspicious", "malicious"]


class GNQLEventResult(BaseModel):
    """GNQL Event result model for connector."""

    def __init__(self, raw_data: Dict[str, Any]):
        raw_data["event_type"] = EVENT_TYPE
        super().__init__(raw_data)

        # Extract from root level
        self.ip = raw_data.get("ip", "")

        # Extract from internet_scanner_intelligence
        isi = raw_data.get("internet_scanner_intelligence", {})
        self.classification = isi.get("classification", "unknown")
        self.last_seen = isi.get("last_seen", "")
        self.first_seen = isi.get("first_seen", "")
        self.actor = isi.get("actor", "")
        self.tags = isi.get("tags", [])
        self.cves = isi.get("cves", [])
        self.vpn = isi.get("vpn", False)
        self.vpn_service = isi.get("vpn_service", "")
        self.tor = isi.get("tor", False)
        self.bot = isi.get("bot", False)
        self.spoofable = isi.get("spoofable", False)
        self.metadata = isi.get("metadata", {})
        self.last_seen_timestamp = isi.get("last_seen_timestamp", "")
        self.last_seen_malicious = isi.get("last_seen_malicious", "")
        self.last_seen_suspicious = isi.get("last_seen_suspicious", "")
        self.last_seen_benign = isi.get("last_seen_benign", "")
        self.event_type = raw_data.get("event_type")

        # Extract from business_service_intelligence
        bsi = raw_data.get("business_service_intelligence", {})
        self.is_business_service = bsi.get("found", False)
        self.business_service_name = bsi.get("name", "")
        self.trust_level = bsi.get("trust_level", "")

        # Generate unique event ID
        self.event_id = f"{self.ip}_{self.last_seen_timestamp}"

    def get_severity(self) -> int:
        """
        Calculate alert severity based on classification.

        Returns:
            int: Severity score (40=Low, 60=Medium, 80=High, 100=Critical)
        """
        classification_lower = self.classification.lower()

        # Map classification to severity
        if classification_lower == "malicious":
            return SEVERITY_MAP.get("high")
        elif classification_lower == "suspicious":
            return SEVERITY_MAP.get("medium")
        elif classification_lower == "benign":
            return SEVERITY_MAP.get("low")
        else:
            return SEVERITY_MAP.get("low")

    def get_alert_info(self, alert_info, environment_common, device_product_field=None):
        """
        Convert GNQL event to AlertInfo object.

        Args:
            alert_info: AlertInfo object to populate
            environment_common: Environment manager for determining alert environment
            device_product_field: Optional field name for device product

        Returns:
            AlertInfo: Populated alert object
        """
        # Set alert identifiers
        alert_info.display_id = self.event_id
        alert_info.ticket_id = self.event_id
        alert_info.source_grouping_identifier = self.ip
        alert_info.name = f"GreyNoise: {self.classification.title()} IP {self.ip} Detected was last seen on {self.last_seen_timestamp}"
        alert_info.description = (
            f"IP {self.ip} has been classified as {self.classification} "
            f"by GreyNoise and was last seen on {self.last_seen_timestamp}."
        )
        alert_info.rule_generator = f"GreyNoise: {self.classification.title()} IP {self.ip} Detected"
        alert_info.device_vendor = INTEGRATION_NAME
        alert_info.device_product = self.raw_data.get(device_product_field) or INTEGRATION_NAME

        # Set severity
        alert_info.priority = self.get_severity()

        # Set timestamps
        def parse_timestamp(timestamp_str):
            """Parse timestamp string and ensure it's timezone-aware (UTC)."""
            if not timestamp_str:
                return None

            # Handle date-only format (YYYY-MM-DD) using strptime
            if len(timestamp_str) == 10 and timestamp_str.count("-") == 2:
                parsed_dt = datetime.strptime(timestamp_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                return parsed_dt

            # Parse using dateutil (handles many formats automatically)
            parsed_dt = parser.parse(timestamp_str)

            # Ensure timezone-aware
            if parsed_dt.tzinfo is None:
                parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
            else:
                parsed_dt = parsed_dt.astimezone(timezone.utc)

            return parsed_dt

        first_seen_dt = parse_timestamp(self.first_seen)
        start_time_ms = convert_datetime_to_unix_time(first_seen_dt)

        last_seen_dt = parse_timestamp(self.last_seen_timestamp)
        end_time_ms = convert_datetime_to_unix_time(last_seen_dt)

        alert_info.start_time = start_time_ms
        alert_info.end_time = end_time_ms

        # Set environment
        alert_info.environment = environment_common.get_environment(self.raw_data)

        # Add events
        alert_info.events = [dict_to_flat(self.raw_data)]

        return alert_info
