from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from .constants import (
    CENSYS_HOSTS_URL_TEMPLATE,
    CENSYS_PLATFORM_BASE_URL,
    DEFAULT_VALUE_NA,
    ENRICHMENT_PREFIX,
    ENRICHMENT_PREFIX_CERT,
    RESOURCE_TYPE_ENDPOINT_SCANNED,
    RESOURCE_TYPE_FORWARD_DNS_RESOLVED,
    RESOURCE_TYPE_JARM_SCANNED,
    RESOURCE_TYPE_LOCATION_UPDATED,
    RESOURCE_TYPE_REVERSE_DNS_RESOLVED,
    RESOURCE_TYPE_ROUTE_UPDATED,
    RESOURCE_TYPE_SERVICE_SCANNED,
    RESOURCE_TYPE_WHOIS_UPDATED,
)


class BaseModel(object):
    """
    Base data model class for all Censys API responses.
    Provides common functionality for data transformation and output formatting.
    """

    def __init__(self, raw_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the base model.

        Args:
            raw_data: Raw API response data
        """
        self.raw_data = raw_data or {}

    def to_json(self) -> Dict[str, Any]:
        """
        Convert the model to JSON format.

        Returns:
            Dict containing the raw API response data
        """
        return self.raw_data

    def to_csv(self) -> List[Dict[str, Any]]:
        """
        Convert the model to CSV format.
        Should be overridden by child classes.

        Returns:
            List of dictionaries suitable for CSV output
        """
        return [self.raw_data] if self.raw_data else []


class PingDatamodel(BaseModel):
    """
    Data model for Ping action results.
    Used to format and structure the data for output in the SOAR interface.
    """

    def __init__(self, success: bool = True) -> None:
        """
        Initialize the Ping data model.

        Args:
            success: Whether the connectivity test was successful
        """
        super().__init__()
        self.success = success

    def to_csv(self) -> List[Dict[str, str]]:
        """
        Convert ping result to CSV format.

        Returns:
            List containing a single dictionary with connection status
        """
        return [{"Status": "Connected" if self.success else "Failed"}]

    def to_json(self) -> Dict[str, Any]:
        """
        Convert ping result to JSON format.

        Returns:
            Dictionary with success status
        """
        return {"success": self.success, "status": "Connected" if self.success else "Failed"}


class HostHistoryEventModel(BaseModel):
    """
    Data model for Host History Event.
    Represents a single event from the host timeline.
    """

    def __init__(
        self, raw_data: Dict[str, Any], index: int, host_id: str = None, organization_id: str = None
    ) -> None:
        super().__init__(raw_data)
        self.index = index
        self.host_id = host_id
        self.organization_id = organization_id
        self.resource = raw_data.get("resource", {})
        self.event_time = self.resource.get("event_time", DEFAULT_VALUE_NA)

        # Parse resource type and key values
        self.resource_type = DEFAULT_VALUE_NA
        self.resource_key_values = DEFAULT_VALUE_NA
        self.historical_view_link = DEFAULT_VALUE_NA
        self._parse_resource_details()
        self._generate_historical_link()

    def _parse_resource_details(self) -> None:
        """Parse resource details based on resource type."""
        if RESOURCE_TYPE_SERVICE_SCANNED in self.resource:
            self.resource_type = RESOURCE_TYPE_SERVICE_SCANNED
            scan_data = self.resource[RESOURCE_TYPE_SERVICE_SCANNED].get("scan", {})
            port = scan_data.get("port", DEFAULT_VALUE_NA)
            protocol = scan_data.get("protocol", DEFAULT_VALUE_NA)
            transport_protocol = scan_data.get("transport_protocol", DEFAULT_VALUE_NA)
            self.resource_key_values = f"{port}/{protocol}/{transport_protocol}"

        elif RESOURCE_TYPE_REVERSE_DNS_RESOLVED in self.resource:
            self.resource_type = RESOURCE_TYPE_REVERSE_DNS_RESOLVED
            dns_data = self.resource[RESOURCE_TYPE_REVERSE_DNS_RESOLVED]
            names = dns_data.get("names", [])
            self.resource_key_values = names[0] if names else DEFAULT_VALUE_NA

        elif RESOURCE_TYPE_ENDPOINT_SCANNED in self.resource:
            self.resource_type = RESOURCE_TYPE_ENDPOINT_SCANNED
            scan_data = self.resource[RESOURCE_TYPE_ENDPOINT_SCANNED].get("scan", {})
            port = scan_data.get("port", DEFAULT_VALUE_NA)
            endpoint_type = scan_data.get("endpoint_type", DEFAULT_VALUE_NA)
            self.resource_key_values = f"{port}/{endpoint_type}"

        elif RESOURCE_TYPE_FORWARD_DNS_RESOLVED in self.resource:
            self.resource_type = RESOURCE_TYPE_FORWARD_DNS_RESOLVED
            dns_data = self.resource[RESOURCE_TYPE_FORWARD_DNS_RESOLVED]
            name = dns_data.get("name", DEFAULT_VALUE_NA)
            self.resource_key_values = name

        elif RESOURCE_TYPE_JARM_SCANNED in self.resource:
            self.resource_type = RESOURCE_TYPE_JARM_SCANNED
            scan_data = self.resource[RESOURCE_TYPE_JARM_SCANNED].get("scan", {})
            port = scan_data.get("port", DEFAULT_VALUE_NA)
            fingerprint = scan_data.get("fingerprint", DEFAULT_VALUE_NA)
            if len(str(fingerprint)) > 20:
                fingerprint = f"{str(fingerprint)[:20]}..."
            self.resource_key_values = f"{port}/{fingerprint}"

        elif RESOURCE_TYPE_LOCATION_UPDATED in self.resource:
            self.resource_type = RESOURCE_TYPE_LOCATION_UPDATED
            location = self.resource[RESOURCE_TYPE_LOCATION_UPDATED].get("location", {})
            city = location.get("city", DEFAULT_VALUE_NA)
            country = location.get("country", DEFAULT_VALUE_NA)
            self.resource_key_values = f"{city}/{country}"

        elif RESOURCE_TYPE_ROUTE_UPDATED in self.resource:
            self.resource_type = RESOURCE_TYPE_ROUTE_UPDATED
            route = self.resource[RESOURCE_TYPE_ROUTE_UPDATED].get("route", {})
            asn = route.get("asn", DEFAULT_VALUE_NA)
            organization = route.get("organization", DEFAULT_VALUE_NA)
            self.resource_key_values = f"{asn}/{organization}"

        elif RESOURCE_TYPE_WHOIS_UPDATED in self.resource:
            self.resource_type = RESOURCE_TYPE_WHOIS_UPDATED
            whois = self.resource[RESOURCE_TYPE_WHOIS_UPDATED].get("whois", {})
            org = whois.get("organization", {})
            org_name = org.get("name", DEFAULT_VALUE_NA)
            self.resource_key_values = org_name

    def _generate_historical_link(self) -> None:
        """Generate historical view link for the event."""
        if self.host_id and self.organization_id and self.event_time != DEFAULT_VALUE_NA:
            try:
                # URL encode the timestamp
                encoded_time = quote(self.event_time, safe="")
                self.historical_view_link = CENSYS_HOSTS_URL_TEMPLATE.format(
                    base_url=CENSYS_PLATFORM_BASE_URL,
                    host_id=self.host_id,
                    encoded_time=encoded_time,
                    organization_id=self.organization_id,
                )
            except Exception:
                self.historical_view_link = DEFAULT_VALUE_NA
        else:
            self.historical_view_link = DEFAULT_VALUE_NA

    def to_csv(self) -> Dict[str, Any]:
        """Convert event to CSV-compatible dictionary."""
        return {
            "Sr. No.": self.index,
            "Event Time": self.event_time,
            "Resource Type": self.resource_type,
            "Resource Values": self.resource_key_values,
            "Historical View Link": self.historical_view_link,
        }


class HostDatamodel(BaseModel):
    """
    Data model for Censys Host enrichment data.
    Extracts and formats host information for entity enrichment.
    """

    def __init__(self, raw_data: Dict[str, Any]) -> None:
        """
        Initialize the Host data model.

        Args:
            raw_data: Raw API response data from Censys host lookup
        """
        super().__init__(raw_data)
        self.host_data = raw_data.get("result", {}).get("resource", {})

    def is_found(self) -> bool:
        """
        Check if host data was found.

        Returns:
            bool: True if host data exists
        """
        return bool(self.host_data)

    def get_enrichment_data(self) -> Dict[str, Any]:
        """
        Extract enrichment data for entity properties.

        Returns:
            Dict with enrichment fields for entity
        """
        if not self.is_found():
            return {}

        services = self.host_data.get("services", [])
        dns_data = self.host_data.get("dns", {})
        location = self.host_data.get("location", {})
        asn = self.host_data.get("autonomous_system", {})
        whois = self.host_data.get("whois", {})

        enrichment = {
            f"{ENRICHMENT_PREFIX}service_count": self.host_data.get("service_count"),
            f"{ENRICHMENT_PREFIX}ports": self._get_top_values([
                str(s.get("port")) for s in services if s.get("port")
            ]),
            f"{ENRICHMENT_PREFIX}protocols": self._get_top_values([
                s.get("protocol") for s in services if s.get("protocol")
            ]),
            f"{ENRICHMENT_PREFIX}transport_protocols": self._get_top_values([
                s.get("transport_protocol") for s in services if s.get("transport_protocol")
            ]),
            f"{ENRICHMENT_PREFIX}host_labels": self._get_top_values([
                label.get("value")
                for label in self.host_data.get("labels", [])
                if label.get("value")
            ]),
            f"{ENRICHMENT_PREFIX}service_labels": self._get_top_values([
                label.get("value")
                for s in services
                for label in s.get("labels", [])
                if label.get("value")
            ]),
            f"{ENRICHMENT_PREFIX}threat_names": self._get_top_values([
                threat.get("name")
                for s in services
                for threat in s.get("threats", [])
                if threat.get("name")
            ]),
            f"{ENRICHMENT_PREFIX}vulnerabilities": self._get_top_values([
                vuln for s in services for vuln in s.get("vulns", [])
            ]),
            f"{ENRICHMENT_PREFIX}last_scan_time": self._get_latest_scan_time(services),
            f"{ENRICHMENT_PREFIX}dns_names": self._get_top_values(dns_data.get("names", [])),
            f"{ENRICHMENT_PREFIX}forward_dns": self._get_top_values(
                dns_data.get("forward_dns", {}).get("names", [])
            ),
            f"{ENRICHMENT_PREFIX}reverse_dns": self._get_top_values(
                dns_data.get("reverse_dns", {}).get("names", [])
            ),
            f"{ENRICHMENT_PREFIX}network_name": whois.get("network", {}).get("name"),
            f"{ENRICHMENT_PREFIX}network_cidrs": self._get_top_values(
                whois.get("network", {}).get("cidrs", [])
            ),
            f"{ENRICHMENT_PREFIX}asn_name": asn.get("name"),
            f"{ENRICHMENT_PREFIX}asn_id": asn.get("asn"),
            f"{ENRICHMENT_PREFIX}location_city": location.get("city"),
            f"{ENRICHMENT_PREFIX}location_province": location.get("province"),
            f"{ENRICHMENT_PREFIX}location_postal": location.get("postal_code"),
            f"{ENRICHMENT_PREFIX}location_country": location.get("country"),
            f"{ENRICHMENT_PREFIX}country_code": location.get("country_code"),
            f"{ENRICHMENT_PREFIX}continent": location.get("continent"),
            f"{ENRICHMENT_PREFIX}geo_lat": location.get("coordinates", {}).get("latitude"),
            f"{ENRICHMENT_PREFIX}geo_long": location.get("coordinates", {}).get("longitude"),
        }

        return {k: v for k, v in enrichment.items() if v is not None}

    def _get_top_values(self, values: List[Any], max_count: int = 5) -> Optional[str]:
        """
        Get top N unique values as comma-separated string.

        Args:
            values: List of values to process
            max_count: Maximum number of values to return

        Returns:
            Comma-separated string of top values or None
        """
        if not values:
            return None

        unique_values = []
        seen = set()
        for val in values:
            if not val:
                continue

            # Handle dict values (like vulnerability objects)
            if isinstance(val, dict):
                # Extract CVE ID or other identifier
                val_str = val.get("id") or str(val)
            else:
                val_str = str(val)

            # Use string representation for deduplication
            if val_str not in seen:
                unique_values.append(val_str)
                seen.add(val_str)
                if len(unique_values) >= max_count:
                    break

        return ", ".join(unique_values) if unique_values else None

    def _get_latest_scan_time(self, services: List[Dict]) -> Optional[str]:
        """
        Get the most recent scan time from services.

        Args:
            services: List of service dictionaries

        Returns:
            Latest scan time as ISO string or None
        """
        scan_times = [s.get("scan_time") for s in services if s.get("scan_time")]
        return max(scan_times) if scan_times else None


class WebPropertyDatamodel(BaseModel):
    """
    Data model for Censys Web Property enrichment data.
    Extracts and formats web property information for entity enrichment.
    """

    def __init__(self, raw_data: Dict[str, Any], port: int) -> None:
        """
        Initialize the Web Property data model.

        Args:
            raw_data: Raw API response data from Censys web property lookup
            port: Port number for this web property
        """
        super().__init__(raw_data)
        self.port = port
        self.web_data = raw_data.get("resource", {})

    def is_found(self) -> bool:
        """
        Check if web property data was found.

        Returns:
            bool: True if web property data exists
        """
        return bool(self.web_data)

    def get_enrichment_data(self) -> Dict[str, Any]:
        """
        Extract enrichment data for entity properties with port prefix.

        Returns:
            Dict with enrichment fields for entity (port-prefixed)
        """
        if not self.is_found():
            return {}

        port_prefix = f"{ENRICHMENT_PREFIX}{self.port}_"

        endpoints = self.web_data.get("endpoints", [])
        software_list = self.web_data.get("software", [])
        labels = self.web_data.get("labels", [])
        threats = self.web_data.get("threats", [])
        vulns = self.web_data.get("vulns", [])
        cert = self.web_data.get("cert", {})

        enrichment = {
            f"{port_prefix}web_hostname": self.web_data.get("hostname"),
            f"{port_prefix}web_port": self.web_data.get("port"),
            f"{port_prefix}endpoint_type": self._get_top_values([
                ep.get("endpoint_type") for ep in endpoints if ep.get("endpoint_type")
            ]),
            f"{port_prefix}endpoint_path": self._get_top_values([
                ep.get("path") for ep in endpoints if ep.get("path")
            ]),
            f"{port_prefix}web_labels": self._get_top_values([
                label.get("value") for label in labels if label.get("value")
            ]),
            f"{port_prefix}web_threats": self._get_top_values([
                threat.get("name") for threat in threats if threat.get("name")
            ]),
            f"{port_prefix}web_vulns": self._get_top_values([
                vuln.get("id") or vuln.get("name")
                for vuln in vulns
                if vuln.get("id") or vuln.get("name")
            ]),
            f"{port_prefix}web_scan_time": self.web_data.get("scan_time"),
            f"{port_prefix}software_vendor": self._get_top_values([
                sw.get("vendor") for sw in software_list if sw.get("vendor")
            ]),
            f"{port_prefix}software_product": self._get_top_values([
                sw.get("product") for sw in software_list if sw.get("product")
            ]),
            f"{port_prefix}software_version": self._get_top_values([
                sw.get("version") for sw in software_list if sw.get("version")
            ]),
            f"{port_prefix}last_enriched": (datetime.utcnow().isoformat() + "Z"),
        }

        if cert:
            cert_parsed = cert.get("parsed", {})
            cert_validity = cert_parsed.get("validity_period", {})
            cert_subject = cert_parsed.get("subject", {})
            cert_signature = cert_parsed.get("signature", {})

            cert_enrichment = {
                f"{port_prefix}web_cert_sha256": cert.get("fingerprint_sha256"),
                f"{port_prefix}web_cert_subject": cert_parsed.get("subject_dn"),
                f"{port_prefix}web_cert_issuer": cert_parsed.get("issuer_dn"),
                f"{port_prefix}web_cert_cn": self._get_first_value(
                    cert_subject.get("common_name", [])
                ),
                f"{port_prefix}web_cert_start": cert_validity.get("not_before"),
                f"{port_prefix}web_cert_end": cert_validity.get("not_after"),
                f"{port_prefix}web_cert_self_signed": cert_signature.get("self_signed"),
            }
            enrichment.update(cert_enrichment)

        return {k: v for k, v in enrichment.items() if v is not None}

    def _get_top_values(self, values: List[Any], max_count: int = 5) -> Optional[str]:
        """
        Get top N unique values as comma-separated string.

        Args:
            values: List of values to process
            max_count: Maximum number of values to return

        Returns:
            Comma-separated string of top values or None
        """
        if not values:
            return None

        unique_values = []
        seen = set()
        for val in values:
            if not val:
                continue

            if isinstance(val, dict):
                val_str = val.get("id") or val.get("name") or str(val)
            else:
                val_str = str(val)

            if val_str not in seen:
                unique_values.append(val_str)
                seen.add(val_str)
                if len(unique_values) >= max_count:
                    break

        return ", ".join(unique_values) if unique_values else None

    def _get_first_value(self, values: List[Any]) -> Optional[str]:
        """
        Get first non-empty value from list.

        Args:
            values: List of values

        Returns:
            First non-empty value or None
        """
        if not values:
            return None
        for val in values:
            if val:
                return str(val)
        return None


class CertificateDatamodel(BaseModel):
    """
    Data model for Censys Certificate enrichment.
    Handles certificate data from /v3/global/asset/certificate endpoint.
    """

    def __init__(self, raw_data: Dict[str, Any]) -> None:
        """
        Initialize the Certificate data model.

        Args:
            raw_data: Raw API response data from Censys certificate lookup
        """
        super().__init__(raw_data)
        self.cert_data = raw_data.get("result", {}).get("resource", {})

    def is_found(self) -> bool:
        """
        Check if certificate data was found.

        Returns:
            bool: True if certificate data exists
        """
        return bool(self.cert_data)

    def get_enrichment_data(self) -> Dict[str, Any]:
        """
        Extract enrichment data for entity properties.

        Returns:
            Dict with enrichment fields for entity
        """
        if not self.is_found():
            return {}

        parsed = self.cert_data.get("parsed", {})
        subject = parsed.get("subject", {})
        validity = parsed.get("validity_period", {})
        signature = parsed.get("signature", {})

        enrichment = {
            f"{ENRICHMENT_PREFIX_CERT}sha256": self.cert_data.get("fingerprint_sha256"),
            f"{ENRICHMENT_PREFIX_CERT}subject_dn": parsed.get("subject_dn"),
            f"{ENRICHMENT_PREFIX_CERT}issuer_dn": parsed.get("issuer_dn"),
            f"{ENRICHMENT_PREFIX_CERT}common_name": self._get_first_value(
                subject.get("common_name", [])
            ),
            f"{ENRICHMENT_PREFIX_CERT}not_before": validity.get("not_before"),
            f"{ENRICHMENT_PREFIX_CERT}not_after": validity.get("not_after"),
            f"{ENRICHMENT_PREFIX_CERT}is_self_signed": signature.get("self_signed"),
            f"{ENRICHMENT_PREFIX}last_enriched": (datetime.utcnow().isoformat() + "Z"),
        }

        return enrichment

    def _get_first_value(self, value_list: List[Any]) -> Optional[str]:
        """
        Get first value from a list.

        Args:
            value_list: List of values

        Returns:
            First value as string or None
        """
        if value_list and isinstance(value_list, list) and len(value_list) > 0:
            return str(value_list[0])
        return None

    def to_json(self) -> Dict[str, Any]:
        """
        Convert certificate data to JSON format for case wall.

        Returns:
            Dict containing full certificate data
        """
        if not self.is_found():
            return {}

        return self.cert_data
