from __future__ import annotations

from typing import Any, Dict


class BaseModel:
    """Base model for all Cyjax datamodels."""

    def __init__(self, raw_data: Dict[str, Any]):
        self.raw_data = raw_data

    def to_json(self) -> Dict[str, Any]:
        """Return raw data as JSON."""
        return self.raw_data


class EnrichedIOC(BaseModel):
    """Model for Enriched IOC."""

    def __init__(self, enrichment_data: Dict[str, Any], entity):
        super().__init__(enrichment_data)
        self.type = enrichment_data.get("type", "N/A")
        self.last_seen_timestamp = enrichment_data.get("last_seen_timestamp", "N/A")
        self.geoip = enrichment_data.get("geoip", {})
        self.asn = enrichment_data.get("asn", {})
        self.sightings = enrichment_data.get("sightings", [])
        self.ioc = entity
        sources = [src.get("source") for src in self.sightings if src.get("source")]
        sources_str = "; ".join(sources[:3]) or "N/A"

        if len(sources) > 3:
            sources_str += f" ... (+{len(sources) - 3} more)"
        self.sources = sources_str

    def to_csv(self) -> Dict[str, Any]:
        """Return data formatted for CSV/table output."""
        enriched_data = {
            "Entity": self.ioc,
            "Type": self.type,
            "Last Seen": self.last_seen_timestamp,
            "Sources": self.sources,
        }

        parts = []
        if self.geoip:
            if self.geoip.get("city"):
                parts.append(self.geoip.get("city"))
            if self.geoip.get("country_name"):
                parts.append(self.geoip.get("country_name"))
            if self.geoip.get("country_code"):
                parts.append(f"({self.geoip.get('country_code')})")

        enriched_data["GeoIPAddress"] = (
            f"{self.geoip.get('ip_address', 'N/A')}" if self.geoip else "N/A"
        )
        enriched_data["GeoIPLocation"] = " ".join(parts) if parts else "N/A"

        if self.asn:
            org = self.asn.get("organization")
            num = self.asn.get("number")
            if org and num:
                enriched_data["ASN"] = f"{org} (AS{num})"
            elif org:
                enriched_data["ASN"] = org
            elif num:
                enriched_data["ASN"] = f"AS{num}"
        else:
            enriched_data["ASN"] = "N/A"

        count = len(self.sightings)
        enriched_data["Sightings Count"] = count

        return enriched_data

    def get_entity_enrichment(self) -> Dict[str, Any]:
        """Return data formatted for entity enrichment."""
        enrichment_data = {
            "Cyjax_Last_Seen": self.last_seen_timestamp,
            "Cyjax_Sightings_Count": len(self.sightings),
        }
        if self.geoip:
            enrichment_data.update({
                "Cyjax_GeoIP_Country_Code": self.geoip.get("country_code"),
                "Cyjax_GeoIP_Country_Name": self.geoip.get("country_name"),
                "Cyjax_GeoIP_City": self.geoip.get("city"),
            })
        if self.asn:
            enrichment_data.update({
                "Cyjax_ASN_Organization": self.asn.get("organization"),
                "Cyjax_ASN_Number": self.asn.get("number"),
            })
        if self.sources != "N/A":
            enrichment_data["Cyjax_Sources"] = self.sources
        return enrichment_data


class DomainMonitorResult(BaseModel):
    """Model for Domain Monitor result."""

    def __init__(self, raw_data: Dict[str, Any]):
        super().__init__(raw_data)
        self.domains = raw_data.get("domains", [])
        self.matched_domains = raw_data.get("matched_domains", [])
        self.keyword = raw_data.get("keyword", [])
        self.type = raw_data.get("type", "N/A")
        self.discovery_date = raw_data.get("discovery_date", "N/A")
        self.expiration_timestamp = raw_data.get("expiration_timestamp", "N/A")
        self.source = raw_data.get("source", "N/A")

    def to_csv(self) -> Dict[str, Any]:
        """Return data formatted for CSV/table output."""
        domains_str = ", ".join(self.domains[:3]) if self.domains else "N/A"
        if len(self.domains) > 3:
            domains_str += f" ... (+{len(self.domains) - 3} more)"

        matched_str = ", ".join(self.matched_domains[:3]) if self.matched_domains else "N/A"
        if len(self.matched_domains) > 3:
            matched_str += f" ... (+{len(self.matched_domains) - 3} more)"

        keywords_str = ", ".join(self.keyword) if self.keyword else "N/A"

        return {
            "Type": self.type,
            "Domains": domains_str,
            "Matched Domains": matched_str,
            "Keywords": keywords_str,
            "Discovery Date": self.discovery_date,
            "Expiration Time": self.expiration_timestamp,
            "Source": self.source,
        }


class DataBreachListResult(BaseModel):
    """Model for Data Breach list result."""

    def __init__(self, raw_data: Dict[str, Any]):
        super().__init__(raw_data)
        self.id = raw_data.get("id", "N/A")
        self.email = raw_data.get("email", "N/A")
        self.source = raw_data.get("source", "N/A")
        self.data_breach = raw_data.get("data_breach", {})
        self.breach_name = self.data_breach.get("name", "N/A")
        self.breach_id = self.data_breach.get("id", "N/A")
        self.breach_url = self.data_breach.get("url", "N/A")
        self.data_classes = raw_data.get("data_classes", [])
        self.discovered_at = raw_data.get("discovered_at", "N/A")

    def to_csv(self) -> Dict[str, Any]:
        """Return data formatted for CSV/table output."""
        data_classes_for_csv = self.data_classes
        if data_classes_for_csv and len(data_classes_for_csv) > 10:
            data_classes_for_csv = data_classes_for_csv[:10] + ["... (more)"]
        data_classes_str = "| ".join(data_classes_for_csv) if data_classes_for_csv else "N/A"

        return {
            "ID": self.id,
            "Email": self.email,
            "Source": self.source,
            "Breach Name": self.breach_name,
            "Breach ID": self.breach_id,
            "Breach URL": self.breach_url,
            "Data Classes": data_classes_str,
            "Discovered At": self.discovered_at,
        }
