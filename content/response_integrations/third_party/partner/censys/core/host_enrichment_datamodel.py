from __future__ import annotations

from typing import Any

from TIPCommon.types import SingleJson

from .base_model import BaseModel
from .constants import ENRICHMENT_PREFIX
from .reputation import ReputationExtractor


class HostEnrichmentDatamodel(BaseModel):
    """
    Data model for the new Censys host enrichment endpoint.
    Handles responses from GET /v3/global/asset/enrichment/host/{host_ip}.
    """

    def __init__(self, raw_data: SingleJson) -> None:
        super().__init__(raw_data)
        self.host_data = (raw_data.get("result") or {}).get("resource") or {}
        self._resource_data = self.host_data

    def get_enrichment_data(self) -> SingleJson:
        if not self.is_found():
            return {}

        enrichment: SingleJson = {}
        enrichment.update(self._get_core_host_fields())
        enrichment.update(self._get_location_and_network_fields())
        enrichment.update(self._get_risk_and_privacy_fields())
        enrichment.update(self._get_mallory_fields())

        return {k: v for k, v in enrichment.items() if v is not None}

    def _get_core_host_fields(self) -> SingleJson:
        """Extract service, DNS, and label fields from the host data."""
        services = self.host_data.get("services") or []
        dns_data = self.host_data.get("dns") or {}

        return {
            f"{ENRICHMENT_PREFIX}service_count": self.host_data.get("service_count"),
            f"{ENRICHMENT_PREFIX}ports": self._get_top_values(
                [str(s.get("port")) for s in services if s.get("port")]
            ),
            f"{ENRICHMENT_PREFIX}protocols": self._get_top_values(
                [s.get("protocol") for s in services if s.get("protocol")]
            ),
            f"{ENRICHMENT_PREFIX}host_labels": self._get_top_values(
                [
                    label.get("value")
                    for label in self.host_data.get("labels") or []
                    if label.get("value")
                ]
            ),
            f"{ENRICHMENT_PREFIX}service_labels": self._get_top_values(
                [
                    label.get("value")
                    for s in services
                    for label in s.get("labels") or []
                    if label.get("value")
                ]
            ),
            f"{ENRICHMENT_PREFIX}threat_names": self._get_top_values(
                [
                    threat.get("name")
                    for s in services
                    for threat in s.get("threats") or []
                    if threat.get("name")
                ]
            ),
            f"{ENRICHMENT_PREFIX}dns_names": self._get_top_values(
                dns_data.get("names") or []
            ),
            f"{ENRICHMENT_PREFIX}reverse_dns": self._get_top_values(
                (dns_data.get("reverse_dns") or {}).get("names") or []
            ),
        }

    def _get_location_and_network_fields(self) -> SingleJson:
        """Extract ASN, WHOIS, and geolocation fields from the host data."""
        location = self.host_data.get("location") or {}
        asn = self.host_data.get("autonomous_system") or {}
        whois = self.host_data.get("whois") or {}
        network_info = whois.get("network") or {}
        coordinates = location.get("coordinates") or {}

        return {
            f"{ENRICHMENT_PREFIX}network_name": network_info.get("name"),
            f"{ENRICHMENT_PREFIX}network_cidrs": self._get_top_values(
                network_info.get("cidrs") or []
            ),
            f"{ENRICHMENT_PREFIX}asn_name": asn.get("name"),
            f"{ENRICHMENT_PREFIX}asn_id": asn.get("asn"),
            f"{ENRICHMENT_PREFIX}location_city": location.get("city"),
            f"{ENRICHMENT_PREFIX}location_province": location.get("province"),
            f"{ENRICHMENT_PREFIX}location_postal": location.get("postal_code"),
            f"{ENRICHMENT_PREFIX}location_country": location.get("country"),
            f"{ENRICHMENT_PREFIX}country_code": location.get("country_code"),
            f"{ENRICHMENT_PREFIX}continent": location.get("continent"),
            f"{ENRICHMENT_PREFIX}geo_lat": coordinates.get("latitude"),
            f"{ENRICHMENT_PREFIX}geo_long": coordinates.get("longitude"),
        }

    def _get_risk_and_privacy_fields(self) -> SingleJson:
        """Extract reputation, GreyNoise, privacy, and network-type fields."""
        reputation = self.host_data.get("reputation") or {}
        greynoise = self.host_data.get("greynoise") or {}
        privacy = self.host_data.get("privacy") or []
        network = self.host_data.get("network") or []
        first_privacy = privacy[0] if privacy else {}
        first_network = network[0] if network else {}

        fields = {
            f"{ENRICHMENT_PREFIX}reputation_score": reputation.get("score"),
            f"{ENRICHMENT_PREFIX}reputation_score_level": (
                reputation.get("score_level") or None
            ),
            # GreyNoise Fields
            f"{ENRICHMENT_PREFIX}greynoise_actor": greynoise.get("actor") or None,
            f"{ENRICHMENT_PREFIX}greynoise_classification": (
                greynoise.get("classification") or None
            ),
            f"{ENRICHMENT_PREFIX}greynoise_last_observed": greynoise.get(
                "last_observed_time"
            ),
            # IPInfo Fields
            f"{ENRICHMENT_PREFIX}privacy_tor": first_privacy.get("tor"),
            f"{ENRICHMENT_PREFIX}privacy_vpn": first_privacy.get("vpn"),
            f"{ENRICHMENT_PREFIX}privacy_proxy": first_privacy.get("proxy"),
            f"{ENRICHMENT_PREFIX}privacy_anonymous": first_privacy.get("anonymous"),
            f"{ENRICHMENT_PREFIX}privacy_relay": first_privacy.get("relay"),
            f"{ENRICHMENT_PREFIX}network_hosting": first_network.get("hosting"),
            f"{ENRICHMENT_PREFIX}network_mobile": first_network.get("mobile"),
            f"{ENRICHMENT_PREFIX}network_satellite": first_network.get("satellite"),
        }
        fields.update(ReputationExtractor.get_entity_enrichment_fields(reputation))
        return fields

    def _get_mallory_fields(self) -> SingleJson:
        """Extract Mallory/third-party observable and opinion fields."""
        third_party = self.host_data.get("third_party") or {}
        mallory = third_party.get("mallory") or []
        first_mallory = mallory[0] if mallory else {}
        first_observable = first_mallory.get("observable") or {}
        opinions = first_mallory.get("opinions") or []
        first_opinion = opinions[0] if opinions else {}

        return {
            f"{ENRICHMENT_PREFIX}mallory_name": first_observable.get("name"),
            f"{ENRICHMENT_PREFIX}mallory_type": first_observable.get("type"),
            f"{ENRICHMENT_PREFIX}mallory_last_updated_at": self._get_latest_value(
                [
                    first_mallory.get("last_seen_at"),
                    first_mallory.get("updated_at"),
                    first_observable.get("updated_at"),
                    first_opinion.get("updated_at"),
                ]
            ),
            f"{ENRICHMENT_PREFIX}mallory_description": (
                first_observable.get("description")
                or first_opinion.get("description")
            ),
            f"{ENRICHMENT_PREFIX}mallory_verdict": first_opinion.get("verdict"),
            f"{ENRICHMENT_PREFIX}mallory_confidence": first_opinion.get("confidence"),
            f"{ENRICHMENT_PREFIX}mallory_source": (
                first_opinion.get("source")
                or first_opinion.get("reference_source_slug")
            ),
        }

    def _get_latest_value(self, values: list[Any]) -> str | None:
        values = [value for value in values if value]
        return max(values) if values else None
