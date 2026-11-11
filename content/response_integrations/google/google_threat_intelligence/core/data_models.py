from __future__ import annotations

import base64
import dataclasses
import re
import zlib
from collections import defaultdict
from typing import Any, Optional

from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from TIPCommon.transformation import add_prefix_to_dict, dict_to_flat
from TIPCommon.types import SingleJson
from google_threat_intelligence.core.constants import (
    CASE_WALL_LINK,
    COLLECTIONS_CASE_WALL_LINK,
    DATA_ENRICHMENT_PREFIX,
    GTI_ALERT_ENTITY_KEYS,
    GTI_ENTITY_KEY_ALIASES,
    GTI_ENTITY_USER_KEYS,
    NOTIFICATION_ALLOWED_VERDICTS,
    PRIVATE_CASE_WALL_LINK,
    PRIVATE_URL_DATA_TYPE,
    SEVERITY_GTI_MAPPING,
)


@dataclasses.dataclass(frozen=True, slots=True)
class BaseModel:
    raw_data: SingleJson

    def to_json(self) -> SingleJson:
        return dataclasses.asdict(self)

    def to_flat(self) -> dict[str, Any]:
        return dict_to_flat(self.to_json()["raw_data"])


@dataclasses.dataclass(frozen=True)
class BaseObject(BaseModel):
    """Class to create data model for Base Object"""

    @classmethod
    def from_json(cls, raw_data: SingleJson) -> BaseObject:
        """Create a BaseObject object from JSON data.

        Args:
            raw_data (SingleJson): raw data to create BaseObject from

        Returns:
            BaseObject: Base object

        """
        return cls(raw_data=raw_data)


@dataclasses.dataclass(frozen=True)
class GraphDetails(BaseModel):
    """Class to create data model for GraphDetails object"""

    graph_id: str
    links: [Link]

    @classmethod
    def from_json(cls, raw_data: dict, links: [Link]) -> GraphDetails:
        """Create GraphDetails object from raw json data.

        Args:
            raw_data (dict): raw data of graph details
            links ([Link]): list of Link objects

        Returns:
            GraphDetails: GraphDetails object

        """
        return cls(
            raw_data=raw_data,
            graph_id=raw_data.get("id"),
            links=links,
        )


@dataclasses.dataclass(frozen=True)
class Link(BaseModel):
    """Class to create data model for Link object"""

    source: str
    target: str
    connection_type: str

    @classmethod
    def from_json(cls, raw_data: dict) -> Link:
        """Create Link object from raw json data.

        Args:
            raw_data (dict): raw data of link

        Returns:
            Link: Link object

        """
        return cls(
            raw_data=raw_data,
            source=raw_data.get("source"),
            target=raw_data.get("target"),
            connection_type=raw_data.get("connection_type"),
        )

    def to_csv(self):
        return {
            "Source": self.source,
            "Target": self.target,
            "Connection Type": self.connection_type,
        }


@dataclasses.dataclass(frozen=True)
class Graph(BaseModel):
    """Class to create data model for Graph object"""

    @classmethod
    def from_json(cls, raw_data: dict) -> Graph:
        """Create Graph object from raw json data.

        Args:
            raw_data (dict): raw data of graph

        Returns:
            Graph: Graph object

        """
        return cls(raw_data=raw_data)

    def to_json_shorten(self) -> SingleJson:
        """Prepare shorten json data from raw data

        Returns:
            SingleJson: SingleJson data

        """
        return {
            "attributes": self.raw_data.get("attributes", {}),
            "id": self.raw_data.get("id"),
        }


@dataclasses.dataclass(frozen=True)
class DTMAlert(BaseModel):
    """Class to create data model for DTM Alert object"""

    raw_flat_data: dict
    alert_id: str
    status: str
    title: str
    created_at: str
    severity: int
    alert_type: str
    alert_summary: str
    aggregated_under_id: str
    monitor_name: str
    topics: [Topic]

    @classmethod
    def from_json(cls, raw_data: dict, topics: [Topic]) -> DTMAlert:
        """Create DTMAlert object from raw json data.

        Args:
            raw_data (dict): raw data of graph
            topics ([Topic]): list of Topic objects

        Returns:
            DTMAlert: DTMAlert object

        """
        return cls(
            raw_data=raw_data,
            raw_flat_data=dict_to_flat(raw_data),
            alert_id=raw_data.get("id"),
            status=raw_data.get("status"),
            title=raw_data.get("title"),
            created_at=convert_string_to_unix_time(raw_data.get("created_at")),
            severity=raw_data.get("severity"),
            alert_type=raw_data.get("alert_type"),
            alert_summary=raw_data.get("alert_summary"),
            aggregated_under_id=raw_data.get("aggregated_under_id"),
            monitor_name=raw_data.get("monitor_name"),
            topics=topics,
        )


@dataclasses.dataclass(frozen=True)
class Topic(BaseModel):
    """Class to create data model for Topic object"""

    @classmethod
    def from_json(cls, raw_data: dict) -> Topic:
        """Create Topic object from raw json data.

        Args:
            raw_data (dict): raw data of alert

        Returns:
            Topic: Topic object

        """
        return cls(raw_data=raw_data)


@dataclasses.dataclass(frozen=True)
class ASMEntity(BaseModel):
    """Class to create data model for ASMEntity object"""

    name: str

    @classmethod
    def from_json(cls, raw_data: dict) -> ASMEntity:
        """Create ASMEntity object from raw json data.

        Args:
            raw_data (dict): raw data of alert

        Returns:
            ASMEntity: ASMEntity object

        """
        cls._sanitize_raw_data(raw_data)
        return cls(raw_data=raw_data, name=raw_data.get("name"))

    @staticmethod
    def _sanitize_raw_data(raw_data: dict) -> None:
        """Sanitize raw data to prevent HTML parsing errors in widgets by escaping script tags."""
        details = raw_data.get("details")
        if isinstance(details, dict):
            body = details.get("extended_response_body")
            if isinstance(body, str):
                # Replace case-insensitive </script> with <\/script>
                details["extended_response_body"] = re.sub(
                    r"</script>",
                    r"<\\/script>",
                    body,
                    flags=re.IGNORECASE,
                )


@dataclasses.dataclass(frozen=True)
class ASMIssue(BaseModel):
    """Class to create data model for ASM Issues object"""

    alert_id: str
    raw_flat_data: dict
    issue_id: str
    pretty_name: str
    proof: str
    description: str
    severity: int
    category: str
    first_seen: str
    last_seen: str
    last_seen_ms: str
    first_seen_ms: str

    @staticmethod
    def extract_category(raw_data: dict) -> Optional[str]:
        """Extract category from the raw data."""
        return raw_data.get("category") or raw_data.get("summary", {}).get("category")

    @classmethod
    def from_json(cls, raw_data: dict) -> ASMIssue:
        """Create ASMIssues object from raw json data.

        Args:
            raw_data (dict): raw data of issue
        Returns:
            ASMIssues: ASMIssues object

        """
        return cls(
            raw_data=raw_data,
            alert_id=raw_data.get("id") or raw_data.get("uid"),
            raw_flat_data=dict_to_flat(raw_data),
            issue_id=raw_data.get("id") or raw_data.get("uid"),
            pretty_name=raw_data.get("pretty_name"),
            proof=raw_data.get("details", {}).get("proof"),
            description=raw_data.get("description"),
            severity=raw_data.get("severity"),
            category=cls.extract_category(raw_data),
            first_seen=raw_data.get("first_seen"),
            last_seen=raw_data.get("last_seen"),
            last_seen_ms=convert_string_to_unix_time(raw_data.get("last_seen")),
            first_seen_ms=convert_string_to_unix_time(raw_data.get("first_seen")),
        )


@dataclasses.dataclass(frozen=True)
class RelatedIOC(BaseModel):
    """Class to create data model for RelatedIOC object"""

    id: str
    type: str
    url: str

    @classmethod
    def from_json(cls, raw_data: dict) -> RelatedIOC:
        """Create RelatedIOC object from raw json data.

        Args:
            raw_data (dict): raw data of alert

        Returns:
            Issue: RelatedIOC object

        """
        return cls(
            raw_data=raw_data,
            id=raw_data.get("id"),
            type=raw_data.get("type"),
            url=raw_data.get("context_attributes", {}).get("url", ""),
        )


@dataclasses.dataclass(frozen=True)
class IOC(BaseModel):
    last_analysis_results: dict

    def to_json_shorten(
        self,
        entity_type: str | None = None,
        comments: list[Comment] | None = None,
        widget_link: str | None = None,
        cached_html_widget: str | None = None,
        sandboxes_data: dict[str, Sandbox] | None = None,
        mitre_response: Mitre | None = None,
    ) -> SingleJson:
        """Prepare shorten json data from raw data

        Returns:
            SingleJson: SingleJson data

        """
        if comments:
            self.raw_data["comments"] = [comment.raw_data for comment in comments]
        if sandboxes_data:
            self.raw_data["sandboxes_data"] = {
                key: value.raw_data if value else None
                for key, value in sandboxes_data.items()
            }
        if mitre_response:
            if mitre_response.mitre_tactics:
                self.raw_data["related_mitre_tactics"] = mitre_response.mitre_tactics
            if mitre_response.mitre_techniques:
                self.raw_data["related_mitre_techniques"] = (
                    mitre_response.mitre_techniques
                )

        if widget_link:
            self.raw_data["widget_link"] = widget_link
        if cached_html_widget:
            compressed = zlib.compress(cached_html_widget.encode("utf-8"))
            b64_compressed = base64.b64encode(compressed).decode("utf-8")
            self.raw_data["widget_html"] = f"COMPRESSED_ZLIB:{b64_compressed}"
        if entity_type in [EntityTypes.THREATACTOR, EntityTypes.CVE]:
            attributes = self.raw_data.get("attributes", {})
            if entity_type == EntityTypes.THREATACTOR:
                if "aggregations" in attributes:
                    attributes.pop("aggregations")
                attributes["threat_actor_id"] = self.raw_data.get("id", "")
            return attributes

        return self.raw_data

    def get_enrichment_data(self):
        raise NotImplementedError

    def to_enrichment_data(self, widget_link=None):
        """Returns cleaned and prefixed enrichment data,
        optionally with a widget link.
        """
        clean_enrichment_data = {
            k: v for k, v in self.get_enrichment_data().items() if v
        }

        if widget_link:
            clean_enrichment_data["widget_link"] = widget_link

        return add_prefix_to_dict(clean_enrichment_data, DATA_ENRICHMENT_PREFIX)

    def to_csv(self) -> list[dict]:
        """Converts last analysis results to a list of dictionaries s
           uitable for CSV export.

        Transforms the 'last_analysis_results' dictionary into a list of dictionaries,
        where each dictionary represents an engine's analysis results with keys
        "Name", "Category", "Method", and "Result".

        Returns:
            list: A list of dictionaries, each representing an engine's analysis
                  results.

        """
        engine_csvs = []
        for key, engine in self.last_analysis_results.items():
            engine_csvs.append(
                {
                    "Name": key,
                    "Category": engine.get("category", ""),
                    "Method": engine.get("method", ""),
                    "Result": engine.get("result", ""),
                }
            )

        return engine_csvs


@dataclasses.dataclass(frozen=True)
class ThreatActor(IOC):
    """Class to create data model for RelatedIOC object"""

    id: str
    type: str
    name: str
    origin: str
    motivations: dict
    aliases: list
    industries: list
    malware: list
    source_region: list
    target_region: list
    description: str
    last_activity_time: str
    report_link: str

    @classmethod
    def from_json(cls, raw_data: dict) -> ThreatActor:
        """Create ThreatActor object from raw json data.

        Args:
            raw_data (dict): raw data

        Returns:
            ThreatActor: ThreatActor object

        """
        return cls(
            raw_data=raw_data,
            last_analysis_results=raw_data.get("attributes", {}).get(
                "last_analysis_results", {}
            ),
            id=raw_data.get("id"),
            type=raw_data.get("type"),
            name=raw_data.get("attributes", {}).get("name", ""),
            origin=raw_data.get("attributes", {}).get("origin", ""),
            motivations=raw_data.get("attributes", {}).get("motivations", {}),
            aliases=raw_data.get("attributes", {}).get("alt_names_details", []),
            industries=raw_data.get("attributes", {}).get("targeted_industries", []),
            malware=raw_data.get("attributes", {}).get("malware", []),
            source_region=raw_data.get("attributes", {}).get(
                "source_regions_hierarchy", []
            ),
            target_region=raw_data.get("attributes", {}).get(
                "targeted_regions_hierarchy", []
            ),
            description=raw_data.get("attributes", {}).get("description", ""),
            last_activity_time=raw_data.get("attributes", {}).get(
                "last_activity_time", ""
            ),
            report_link=COLLECTIONS_CASE_WALL_LINK.format(ioc=raw_data.get("id")),
        )

    def get_enrichment_data(self):
        enrichment_data = {
            "motivations": ", ".join(
                [
                    motivation.get("value", "")
                    for motivation in self.motivations
                    if motivation.get("value") is not None
                ]
            ),
            "aliases": ", ".join(
                [
                    alias.get("value", "")
                    for alias in self.aliases
                    if alias.get("value") is not None
                ]
            ),
            "industries": ", ".join(self.industries),
            "malware": ", ".join(
                [
                    malware.get("name", "")
                    for malware in self.malware
                    if malware.get("name") is not None
                ]
            ),
            "source_region": ", ".join(
                [
                    source.get("country", "")
                    for source in self.source_region
                    if source.get("country") is not None
                ]
            ),
            "target_region": ", ".join(
                [
                    target.get("country", "")
                    for target in self.target_region
                    if target.get("country") is not None
                ]
            ),
            "origin": self.origin,
            "description": self.description,
            "last_activity_time": self.last_activity_time,
            "report_link": self.report_link,
        }

        return enrichment_data


@dataclasses.dataclass(frozen=True)
class IP(IOC):
    """Class to create data model for IP object"""

    ioc_type: str
    ioc: str
    entity_id: str
    as_owner: str
    asn: str
    continent: str
    country: str
    last_analysis_stats: dict
    harmless: int
    malicious: int
    suspicious: int
    undetected: int
    not_after: str
    not_before: str
    reputation: int
    tags: list
    total_votes_harmless: int
    total_votes_malicious: int
    report_link: str
    threat_score: int
    severity: str
    normalised_categories: list
    verdict: str
    description: str

    @classmethod
    def from_json(cls, raw_data: dict, ioc_type: str, ioc: str) -> IP:
        """Create IP object from raw json data.

        Args:
            raw_data (dict): raw data of IP
            ioc_type (str): ioc type
            ioc (str): ioc identifier

        Returns:
            IP: IP object

        """
        return cls(
            raw_data=raw_data,
            last_analysis_results=raw_data.get("attributes", {}).get(
                "last_analysis_results", {}
            ),
            ioc_type=ioc_type,
            ioc=ioc,
            entity_id=raw_data.get("id", ""),
            as_owner=raw_data.get("attributes", {}).get("as_owner", ""),
            asn=raw_data.get("attributes", {}).get("asn", ""),
            continent=raw_data.get("attributes", {}).get("continent", ""),
            country=raw_data.get("attributes", {}).get("country", ""),
            last_analysis_stats=raw_data.get("attributes", {}).get(
                "last_analysis_stats", {}
            ),
            harmless=raw_data.get("attributes", {})
            .get("last_analysis_stats", {})
            .get("harmless", 0),
            malicious=raw_data.get("attributes", {})
            .get("last_analysis_stats", {})
            .get("malicious", 0),
            suspicious=raw_data.get("attributes", {})
            .get("last_analysis_stats", {})
            .get("suspicious", 0),
            undetected=raw_data.get("attributes", {})
            .get("last_analysis_stats", {})
            .get("undetected", 0),
            not_after=raw_data.get("attributes", {})
            .get("last_https_certificate", {})
            .get("validity", {})
            .get("not_after", ""),
            not_before=raw_data.get("attributes", {})
            .get("last_https_certificate", {})
            .get("validity", {})
            .get("not_before", ""),
            reputation=raw_data.get("attributes", {}).get("reputation", 0),
            tags=raw_data.get("attributes", {}).get("tags", []),
            total_votes_harmless=raw_data.get("attributes", {})
            .get("total_votes", {})
            .get("harmless", 0),
            total_votes_malicious=raw_data.get("attributes", {})
            .get("total_votes", {})
            .get("malicious", 0),
            report_link=CASE_WALL_LINK.format(entity_type=ioc_type, entity=ioc),
            threat_score=raw_data.get("attributes", {})
            .get("gti_assessment", {})
            .get("threat_score", {})
            .get("value", 0),
            severity=raw_data.get("attributes", {})
            .get("gti_assessment", {})
            .get("severity", {})
            .get("value", ""),
            normalised_categories=raw_data.get("attributes", {})
            .get("gti_assessment", {})
            .get("contributing_factors", {})
            .get("normalised_categories", []),
            verdict=raw_data.get("attributes", {})
            .get("gti_assessment", {})
            .get("verdict", {})
            .get("value", ""),
            description=raw_data.get("attributes", {})
            .get("gti_assessment", {})
            .get("description", ""),
        )

    def get_enrichment_data(self):
        enrichment_data = {
            "id": self.entity_id,
            "owner": self.as_owner,
            "asn": self.asn,
            "continent": self.continent,
            "country": self.country,
            "harmless_count": self.harmless,
            "malicious_count": self.malicious,
            "suspicious_count": self.suspicious,
            "undetected_count": self.undetected,
            "certificate_valid_not_after": self.not_after,
            "certificate_valid_not_before": self.not_before,
            "reputation": self.reputation,
            "tags": ", ".join(self.tags),
            "malicious_vote_count": self.total_votes_malicious,
            "harmless_vote_count": self.total_votes_harmless,
            "report_link": self.report_link,
            "threat_score": self.threat_score,
            "severity": self.severity,
            "normalised_categories": ", ".join(self.normalised_categories),
            "verdict": self.verdict,
            "description": self.description,
        }

        return enrichment_data


@dataclasses.dataclass(frozen=True)
class URL(IOC):
    """Class to create data model for URL object"""

    ioc_type: str
    ioc: str
    entity_id: str
    title: str
    categories: dict
    last_http_response_code: str
    last_http_response_content_length: str
    threat_names: list
    last_analysis_stats: dict
    harmless: int
    malicious: int
    suspicious: int
    undetected: int
    reputation: int
    tags: list
    total_votes_harmless: int
    total_votes_malicious: int
    report_link: str
    last_analysis_date: int
    threat_score: int
    severity: str
    normalised_categories: list
    verdict: str
    description: str

    @classmethod
    def from_json(cls, raw_data: dict, ioc_type: str, ioc: str) -> URL:
        """Create URL object from raw json data.

        Args:
            raw_data (dict): raw data of URL
            ioc_type (str): ioc type
            ioc (str): ioc identifier

        Returns:
            URL: URL object

        """

        if raw_data.get("type") == PRIVATE_URL_DATA_TYPE:
            report_link = PRIVATE_CASE_WALL_LINK.format(entity_type="url", entity=ioc)
        else:
            report_link = CASE_WALL_LINK.format(entity_type=ioc_type, entity=ioc)

        return cls(
            raw_data=raw_data,
            last_analysis_results=raw_data.get("attributes", {}).get(
                "last_analysis_results", {}
            ),
            ioc_type=ioc_type,
            ioc=ioc,
            entity_id=raw_data.get("id", ""),
            title=raw_data.get("attributes", {}).get("title", ""),
            categories=raw_data.get("attributes", {}).get("categories", {}),
            last_http_response_code=raw_data.get("attributes", {}).get(
                "last_http_response_code", ""
            ),
            last_http_response_content_length=raw_data.get("attributes", {}).get(
                "last_http_response_content_length", ""
            ),
            threat_names=raw_data.get("attributes", {}).get("threat_names", []),
            last_analysis_stats=raw_data.get("attributes", {}).get(
                "last_analysis_stats", {}
            ),
            harmless=raw_data.get("attributes", {})
            .get("last_analysis_stats", {})
            .get("harmless", 0),
            malicious=raw_data.get("attributes", {})
            .get("last_analysis_stats", {})
            .get("malicious", 0),
            suspicious=raw_data.get("attributes", {})
            .get("last_analysis_stats", {})
            .get("suspicious", 0),
            undetected=raw_data.get("attributes", {})
            .get("last_analysis_stats", {})
            .get("undetected", 0),
            reputation=raw_data.get("attributes", {}).get("reputation", 0),
            tags=raw_data.get("attributes", {}).get("tags", []),
            total_votes_harmless=raw_data.get("attributes", {})
            .get("total_votes", {})
            .get("harmless", 0),
            total_votes_malicious=raw_data.get("attributes", {})
            .get("total_votes", {})
            .get("malicious", 0),
            report_link=report_link,
            last_analysis_date=raw_data.get("attributes", {}).get(
                "last_analysis_date", 0
            ),
            threat_score=raw_data.get("attributes", {})
            .get("gti_assessment", {})
            .get("threat_score", {})
            .get("value", 0),
            severity=raw_data.get("attributes", {})
            .get("gti_assessment", {})
            .get("severity", {})
            .get("value", ""),
            normalised_categories=raw_data.get("attributes", {})
            .get("gti_assessment", {})
            .get("contributing_factors", {})
            .get("normalised_categories", []),
            verdict=raw_data.get("attributes", {})
            .get("gti_assessment", {})
            .get("verdict", {})
            .get("value", ""),
            description=raw_data.get("attributes", {})
            .get("gti_assessment", {})
            .get("description", ""),
        )

    def get_enrichment_data(self):
        enrichment_data = {
            "id": self.entity_id,
            "title": self.title,
            "last_http_response_code": self.last_http_response_code,
            "last_http_response_content_length": self.last_http_response_content_length,
            "threat_names": ", ".join(self.threat_names),
            "harmless_count": self.harmless,
            "malicious_count": self.malicious,
            "suspicious_count": self.suspicious,
            "undetected_count": self.undetected,
            "reputation": self.reputation,
            "tags": ", ".join(self.tags),
            "malicious_vote_count": self.total_votes_malicious,
            "harmless_vote_count": self.total_votes_harmless,
            "report_link": self.report_link,
            "threat_score": self.threat_score,
            "severity": self.severity,
            "normalised_categories": ", ".join(self.normalised_categories),
            "verdict": self.verdict,
            "description": self.description,
        }
        for key, value in self.categories.items():
            enrichment_data[f"category_{key}"] = value

        return enrichment_data


@dataclasses.dataclass(frozen=True)
class Hash(IOC):
    """Class to create data model for Hash object"""

    raw_data: SingleJson
    last_analysis_results: dict
    ioc_type: str
    ioc: str
    entity_id: str
    magic: str
    md5: str
    sha1: str
    sha256: str
    ssdeep: str
    tlsh: str
    vhash: str
    meaningful_name: str
    names: list
    harmless: int
    malicious: int
    suspicious: int
    undetected: int
    reputation: int
    tags: list
    total_votes_harmless: int
    total_votes_malicious: int
    report_link: str
    private_report_link: str
    exiftool: dict
    threat_score: int
    severity: str
    normalised_categories: list
    verdict: str
    description: str
    last_analysis_date: int

    @classmethod
    def from_json(cls, raw_data: dict, ioc_type: str, ioc: str) -> Hash:
        """Create Hash object from raw json data.

        Args:
            raw_data (dict): raw data of Hash
            ioc_type (str): ioc type
            ioc (str): ioc identifier

        Returns:
            Hash: Hash object

        """
        return cls(
            raw_data=raw_data,
            last_analysis_results=raw_data.get("attributes", {}).get(
                "last_analysis_results", {}
            ),
            ioc_type=ioc_type,
            ioc=ioc,
            entity_id=raw_data.get("id", ""),
            magic=raw_data.get("attributes", {}).get("magic", ""),
            md5=raw_data.get("attributes", {}).get("md5", ""),
            sha1=raw_data.get("attributes", {}).get("sha1", ""),
            sha256=raw_data.get("attributes", {}).get("sha256", ""),
            ssdeep=raw_data.get("attributes", {}).get("ssdeep", ""),
            tlsh=raw_data.get("attributes", {}).get("tlsh", ""),
            vhash=raw_data.get("attributes", {}).get("vhash", ""),
            meaningful_name=raw_data.get("attributes", {}).get("meaningful_name", ""),
            names=raw_data.get("attributes", {}).get("names", []),
            harmless=raw_data.get("attributes", {})
            .get("last_analysis_stats", {})
            .get("harmless", 0),
            malicious=raw_data.get("attributes", {})
            .get("last_analysis_stats", {})
            .get("malicious", 0),
            suspicious=raw_data.get("attributes", {})
            .get("last_analysis_stats", {})
            .get("suspicious", 0),
            undetected=raw_data.get("attributes", {})
            .get("last_analysis_stats", {})
            .get("undetected", 0),
            reputation=raw_data.get("attributes", {}).get("reputation", 0),
            tags=raw_data.get("attributes", {}).get("tags", []),
            total_votes_harmless=raw_data.get("attributes", {})
            .get("total_votes", {})
            .get("harmless", 0),
            total_votes_malicious=raw_data.get("attributes", {})
            .get("total_votes", {})
            .get("malicious", 0),
            report_link=CASE_WALL_LINK.format(entity_type=ioc_type, entity=ioc),
            private_report_link=PRIVATE_CASE_WALL_LINK.format(
                entity_type=ioc_type, entity=ioc
            ),
            exiftool=raw_data.get("attributes", {}).get("exiftool", {}),
            threat_score=raw_data.get("attributes", {})
            .get("gti_assessment", {})
            .get("threat_score", {})
            .get("value", 0),
            severity=raw_data.get("attributes", {})
            .get("gti_assessment", {})
            .get("severity", {})
            .get("value", ""),
            normalised_categories=raw_data.get("attributes", {})
            .get("gti_assessment", {})
            .get("contributing_factors", {})
            .get("normalised_categories", []),
            verdict=raw_data.get("attributes", {})
            .get("gti_assessment", {})
            .get("verdict", {})
            .get("value", ""),
            description=raw_data.get("attributes", {})
            .get("gti_assessment", {})
            .get("description", ""),
            last_analysis_date=raw_data.get("attributes", {}).get(
                "last_analysis_date", 0
            ),
        )

    def get_enrichment_data(self):
        enrichment_data = {
            "id": self.entity_id,
            "magic": self.magic,
            "md5": self.md5,
            "sha1": self.sha1,
            "sha256": self.sha256,
            "ssdeep": self.ssdeep,
            "tlsh": self.tlsh,
            "vhash": self.vhash,
            "meaningful_name": self.meaningful_name,
            "names": ", ".join(self.names),
            "harmless_count": self.harmless,
            "malicious_count": self.malicious,
            "suspicious_count": self.suspicious,
            "undetected_count": self.undetected,
            "reputation": self.reputation,
            "tags": ", ".join(self.tags),
            "malicious_vote_count": self.total_votes_malicious,
            "harmless_vote_count": self.total_votes_harmless,
            "report_link": self.report_link,
            "threat_score": self.threat_score,
            "severity": self.severity,
            "normalised_categories": ", ".join(self.normalised_categories),
            "verdict": self.verdict,
            "description": self.description,
        }
        enrichment_data.update(self.exiftool)

        return enrichment_data


@dataclasses.dataclass(frozen=True)
class Domain(IOC):
    """Class to create data model for Domain object"""

    ioc_type: str
    ioc: str
    entity_id: str
    tags: list
    categories: dict
    last_analysis_stats: dict
    harmless: int
    malicious: int
    suspicious: int
    undetected: int
    reputation: int
    total_votes_harmless: int
    total_votes_malicious: int
    report_link: str
    threat_score: int
    severity: str
    normalised_categories: list
    verdict: str
    description: str

    @classmethod
    def from_json(cls, raw_data: dict, ioc_type: str, ioc: str) -> Domain:
        """Create Domain object from raw json data.

        Args:
            raw_data (dict): raw data of Domain
            ioc_type (str): ioc type
            ioc (str): ioc identifier

        Returns:
            Domain: Domain object

        """
        return cls(
            raw_data=raw_data,
            last_analysis_results=raw_data.get("attributes", {}).get(
                "last_analysis_results", {}
            ),
            ioc_type=ioc_type,
            ioc=ioc,
            entity_id=raw_data.get("id", ""),
            categories=raw_data.get("attributes", {}).get("categories", {}),
            tags=raw_data.get("attributes", {}).get("tags", []),
            last_analysis_stats=raw_data.get("attributes", {}).get(
                "last_analysis_stats", {}
            ),
            harmless=raw_data.get("attributes", {})
            .get("last_analysis_stats", {})
            .get("harmless", 0),
            malicious=raw_data.get("attributes", {})
            .get("last_analysis_stats", {})
            .get("malicious", 0),
            suspicious=raw_data.get("attributes", {})
            .get("last_analysis_stats", {})
            .get("suspicious", 0),
            undetected=raw_data.get("attributes", {})
            .get("last_analysis_stats", {})
            .get("undetected", 0),
            reputation=raw_data.get("attributes", {}).get("reputation", 0),
            total_votes_harmless=raw_data.get("attributes", {})
            .get("total_votes", {})
            .get("harmless", 0),
            total_votes_malicious=raw_data.get("attributes", {})
            .get("total_votes", {})
            .get("malicious", 0),
            report_link=CASE_WALL_LINK.format(entity_type=ioc_type, entity=ioc),
            threat_score=raw_data.get("attributes", {})
            .get("gti_assessment", {})
            .get("threat_score", {})
            .get("value", 0),
            severity=raw_data.get("attributes", {})
            .get("gti_assessment", {})
            .get("severity", {})
            .get("value", ""),
            normalised_categories=raw_data.get("attributes", {})
            .get("gti_assessment", {})
            .get("contributing_factors", {})
            .get("normalised_categories", []),
            verdict=raw_data.get("attributes", {})
            .get("gti_assessment", {})
            .get("verdict", {})
            .get("value", ""),
            description=raw_data.get("attributes", {})
            .get("gti_assessment", {})
            .get("description", ""),
        )

    def get_enrichment_data(self):
        enrichment_data = {
            "id": self.entity_id,
            "harmless_count": self.harmless,
            "malicious_count": self.malicious,
            "suspicious_count": self.suspicious,
            "undetected_count": self.undetected,
            "reputation": self.reputation,
            "tags": ", ".join(self.tags),
            "malicious_vote_count": self.total_votes_malicious,
            "harmless_vote_count": self.total_votes_harmless,
            "report_link": self.report_link,
            "threat_score": self.threat_score,
            "severity": self.severity,
            "normalised_categories": ", ".join(self.normalised_categories),
            "verdict": self.verdict,
            "description": self.description,
        }
        for key, value in self.categories.items():
            enrichment_data[f"category_{key}"] = value

        return enrichment_data


@dataclasses.dataclass(frozen=True)
class Comment(BaseModel):
    """Class to create data model for Comment object"""

    comment_id: str
    comment: str
    date: str
    abuse_votes: int
    positive_votes: dict
    negative_votes: dict

    @classmethod
    def from_json(cls, raw_data: dict) -> Comment:
        """Create Comment object from raw json data.

        Args:
            raw_data (dict): raw data

        Returns:
            Comment: Comment object

        """
        return cls(
            raw_data=raw_data,
            comment_id=raw_data.get("id", ""),
            comment=raw_data.get("attributes", {}).get("text", ""),
            date=raw_data.get("attributes", {}).get("date", ""),
            abuse_votes=raw_data.get("attributes", {}).get("votes", {}).get("abuse", 0),
            positive_votes=raw_data.get("attributes", {}),
            negative_votes=raw_data.get("attributes", {})
            .get("votes", {})
            .get("negative", 0),
        )

    def to_csv(self):
        return {
            "Date": self.date,
            "Comment": self.comment,
            "Abuse Votes": self.abuse_votes,
            "Negative Votes": self.negative_votes,
            "Positive Votes": self.positive_votes,
            "ID": self.comment_id,
        }


@dataclasses.dataclass(frozen=True)
class Vulnerability(IOC):
    """Class to create data model for Vulnerability object"""

    sources: list
    exploitation_state: str
    date_of_disclosure: str
    vendor_fix_references: list
    exploitation_vectors: list
    description: str
    risk_rating: str
    available_mitigation: list
    exploitation_consequence: str
    report_link: str

    @classmethod
    def from_json(cls, raw_data: dict) -> Vulnerability:
        """Create Vulnerability object from raw json data.

        Args:
            raw_data (dict): raw data of Vulnerability

        Returns:
            Vulnerability: Vulnerability object

        """
        return cls(
            raw_data=raw_data,
            last_analysis_results=raw_data.get("attributes", {}).get(
                "last_analysis_results", {}
            ),
            sources=raw_data.get("attributes", {}).get("sources", []),
            exploitation_state=raw_data.get("attributes", {}).get(
                "exploitation_state", ""
            ),
            date_of_disclosure=raw_data.get("attributes", {}).get(
                "date_of_disclosure", ""
            ),
            vendor_fix_references=raw_data.get("attributes", {}).get(
                "vendor_fix_references", []
            ),
            exploitation_vectors=raw_data.get("attributes", {}).get(
                "exploitation_vectors", []
            ),
            description=raw_data.get("attributes", {}).get("description", ""),
            risk_rating=raw_data.get("attributes", {}).get("risk_rating", ""),
            available_mitigation=raw_data.get("attributes", {}).get(
                "available_mitigation", []
            ),
            exploitation_consequence=raw_data.get("attributes", {}).get(
                "exploitation_consequence", ""
            ),
            report_link=COLLECTIONS_CASE_WALL_LINK.format(
                ioc=raw_data.get("attributes", {}).get("id", "")
            ),
        )

    def get_enrichment_data(self):
        enrichment_data = {
            "sources": ", ".join(
                [
                    source.get("name")
                    for source in self.sources
                    if source.get("name") is not None
                ]
            ),
            "exploitation_state": self.exploitation_state,
            "date_of_disclosure": self.date_of_disclosure,
            "vendor_fix_references": ", ".join(
                [
                    vendor.get("url", "")
                    for vendor in self.vendor_fix_references
                    if vendor.get("url") is not None
                ]
            ),
            "exploitation_vectors": ", ".join(self.exploitation_vectors),
            "description": self.description,
            "risk_rating": self.risk_rating,
            "available_mitigation": ", ".join(self.available_mitigation),
            "exploitation_consequence": self.exploitation_consequence,
            "report_link": self.report_link,
        }

        return enrichment_data


@dataclasses.dataclass(frozen=True)
class Sandbox(BaseModel):
    """Class to create data model for Sandbox object"""

    @classmethod
    def from_json(cls, raw_data: dict) -> Sandbox:
        """Create Sandbox object from raw json data.

        Args:
            raw_data (dict): raw data

        Returns:
            Sandbox: Sandbox object

        """
        return cls(raw_data=raw_data)


@dataclasses.dataclass(frozen=True)
class Mitre(BaseModel):
    """Class to create data model for Sandbox object"""

    status: str
    mitre_tactics: list[dict]
    mitre_techniques: list[dict]

    @classmethod
    def from_json(cls, mitre_data: dict) -> Mitre:
        """Create Mitre object from raw json data.

        Args:
            mitre_data (dict): mitre data

        Returns:
            Mitre: Sandbox object

        """
        return cls(
            raw_data=mitre_data.get("raw_data", {}),
            status=mitre_data.get("status", ""),
            mitre_tactics=mitre_data.get("mitre_tactics", []),
            mitre_techniques=mitre_data.get("mitre_techniques", []),
        )


@dataclasses.dataclass(frozen=True)
class IOCSearchResult(BaseModel):
    """Class to create data model for IOCSearchResult object."""

    @classmethod
    def from_json(cls, raw_data: dict) -> IOCSearchResult:
        """Create IOCSearchResult object from raw json data.

        Args:
            raw_data: Parsed JSON input to construct the object.

        Returns:
            IOCSearchResult: The resulting search result object.

        """
        return cls(raw_data=raw_data)

    def to_json_shorten(self) -> SingleJson:
        return self.raw_data


@dataclasses.dataclass(frozen=True)
class Notification(BaseModel):
    """Class to create data model for Notification object"""

    raw_flat_data: dict
    alert_id: str
    meaningful_name: str
    malicious: int
    suspicious: int
    rule_name: str
    timestamp: int
    verdict: str
    severity: str

    @classmethod
    def from_json(cls, raw_data: dict) -> Notification:
        """Create Notification object from raw json data

        Args:
            raw_data (dict): raw data of notification

        Returns:
            Notification: Notification object

        """
        context_attributes = raw_data.get("context_attributes", {})
        attributes = raw_data.get("attributes", {})
        hunting_info = context_attributes.get("hunting_info", {})
        return cls(
            raw_data=raw_data,
            raw_flat_data=dict_to_flat(raw_data),
            alert_id=context_attributes.get("notification_id", ""),
            meaningful_name=attributes.get("meaningful_name", ""),
            malicious=attributes.get("last_analysis_stats", {}).get("malicious", 0),
            suspicious=attributes.get("last_analysis_stats", {}).get("suspicious", 0),
            rule_name=hunting_info.get("rule_name", "") if hunting_info else "",
            timestamp=context_attributes.get("notification_date", 0) * 1000,
            verdict=(
                attributes.get("gti_assessment", {}).get("verdict", {}).get("value")
            ),
            severity=(
                attributes.get("gti_assessment", {}).get("severity", {}).get("value")
            ),
        )

    def get_severity(self):
        """Get the severity value based on gti_assessment severity values

        Returns:
            int: severity value

        """
        return SEVERITY_GTI_MAPPING.get(self.severity, -1)

    def pass_filter(self):
        """Check if filtering is passed

        Returns:
            bool: True if filtering is passed, False otherwise

        """
        return self.verdict in NOTIFICATION_ALLOWED_VERDICTS


@dataclasses.dataclass(frozen=True)
class FileHashExistence:
    """Data class to represent the existence of a file hash
    in public and private submissions.

    Attributes:
        exists_public (bool): Whether the file hash exists in public submissions.
        exists_private (bool): Whether the file hash exists in private submissions.
        file_hash (str): The file hash.
        last_submission_date (int): Last submission date.

    """

    exists_public: bool
    exists_private: bool
    file_hash: str
    last_submission_date: int


@dataclasses.dataclass(frozen=True)
class AssociationAttributes(BaseModel):
    collection_type: str
    name: str
    shortened_attributes: dict

    @classmethod
    def from_dict(cls, attributes: dict) -> AssociationAttributes:
        """Creates an instance from a raw dict, filtering out 'aggregations'."""
        return cls(
            collection_type=attributes.get("collection_type", ""),
            name=attributes.get("name", ""),
            shortened_attributes={
                k: v for k, v in attributes.items() if k != "aggregations"
            },
            raw_data=attributes,
        )


@dataclasses.dataclass(frozen=True)
class AssociationItem(BaseModel):
    id: str
    type: str
    links: dict[str, str]
    context_attributes: dict[str, Any]

    attributes: AssociationAttributes

    @classmethod
    def from_dict(cls, raw_data: dict) -> AssociationItem:
        """Creates an instance from a single association item dictionary."""
        return cls(
            id=raw_data.get("id"),
            type=raw_data.get("type"),
            links=raw_data.get("links"),
            context_attributes=raw_data.get("context_attributes", {}),
            attributes=AssociationAttributes.from_dict(raw_data.get("attributes", {})),
            raw_data=raw_data,
        )

    def to_shortened_dict(self) -> dict:
        """Converts the AssociationItem instance to a shortened dict."""
        return {
            "id": self.id,
            "type": self.type,
            "links": self.links,
            "context_attributes": self.context_attributes,
            "attributes": self.attributes.shortened_attributes,
        }


@dataclasses.dataclass(frozen=True)
class IOCRelatedAssociations(BaseModel):
    associations: list[AssociationItem]
    raw_data: list[SingleJson]

    @classmethod
    def from_association_items(
        cls,
        associations: list[AssociationItem],
    ) -> IOCRelatedAssociations:
        """Creates an instance from a list of AssociationItem objects."""
        return cls(
            associations=associations, raw_data=[item.raw_data for item in associations]
        )

    def group_by_collection_type(self) -> dict:
        """Groups the instance's items by collection type."""
        grouped_results = defaultdict(list)
        for item in self.associations:
            grouped_results[item.attributes.collection_type].append(
                item.to_shortened_dict()
            )
        return dict(grouped_results)


@dataclasses.dataclass(frozen=True)
class EntityAssociations:
    """A structured container for entity association results."""

    entities_with_associations: dict[str, IOCRelatedAssociations]
    entities_without_associations: list[str]
    failed_entities: list[str]


def _first_str(*candidates: object) -> str:
    """Return the first non-empty string among candidates."""
    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c.strip()

    return ""


def _apply_user_aliases(event: SingleJson, user: str) -> None:
    """Populate canonical user fields on an event dictionary."""
    if not user:
        return

    event["author"] = user
    event["user_name"] = user
    event["userName"] = user
    event["username"] = user
    event["user"] = user


def _apply_cve_aliases(event: SingleJson, cve: str) -> None:
    """Populate canonical CVE fields on an event dictionary."""
    if not cve:
        return

    event["cve"] = cve
    event["cve_id"] = cve
    event["cveId"] = cve


def _parse_audit_timestamps(raw_data: SingleJson) -> tuple[str, int, int]:
    """Parse create and update audit timestamps from raw data.

    Returns:
        Tuple of (create_time_str, create_time_unix, update_time_unix).

    """
    audit: SingleJson = raw_data.get("audit", {})
    create_time_str: str = audit.get("createTime", "")
    create_time_unix: int = (
        convert_string_to_unix_time(create_time_str) if create_time_str else 0
    )
    update_time_str: str = audit.get("updateTime", "")
    update_time_unix: int = (
        convert_string_to_unix_time(update_time_str)
        if update_time_str
        else create_time_unix
    )

    return create_time_str, create_time_unix, update_time_unix


def _extract_priority(raw_data: SingleJson) -> str:
    """Extract normalized priority from raw alert payload."""
    priority_analysis: SingleJson = (
        raw_data.get("priorityAnalysis")
        or raw_data.get("priority_analysis")
        or {}
    )
    priority: str = (
        priority_analysis.get("priorityLevel")
        or priority_analysis.get("priority_level")
        or priority_analysis.get("priority")
        or ""
    )
    if priority:
        return (
            str(priority)
            .replace("PRIORITY_LEVEL_", "")
            .replace("SEVERITY_LEVEL_", "")
            .strip()
            .upper()
        )

    return ""


def _extract_cve_from_vuln(vuln: SingleJson) -> str:
    """Extract CVE ID from vulnerability match dictionary."""
    cve_id: str = vuln.get("cveId") or vuln.get("cve_id") or ""
    return cve_id.strip() if isinstance(cve_id, str) else ""


def _extract_cve_from_detail(detail: SingleJson) -> str:
    """Extract CVE identifier from alert detail payload.

    Args:
        detail: The alert detail dictionary.

    Returns:
        The extracted CVE identifier, or empty string.

    """
    if not isinstance(detail, dict):
        return ""
    vuln: SingleJson = (
        detail.get("vulnerabilityMatch")
        or detail.get("vulnerability_match")
        or {}
    )
    if isinstance(vuln, dict):
        cve_id: str = _extract_cve_from_vuln(vuln)
        if cve_id:
            return cve_id

    for sub_val in detail.values():
        if isinstance(sub_val, dict):
            sub_vuln: SingleJson = (
                sub_val.get("vulnerabilityMatch")
                or sub_val.get("vulnerability_match")
                or {}
            )
            if isinstance(sub_vuln, dict):
                cve_id = _extract_cve_from_vuln(sub_vuln)
                if cve_id:
                    return cve_id
            for k in ("cveId", "cve_id", "cve", "cveID", "CVE"):
                val: Any = sub_val.get(k)
                if val and isinstance(val, str):
                    return val.strip()
    return ""


def _extract_cve(data: SingleJson) -> str:
    """Extract CVE identifier from an alert, finding, or document across all alert types."""
    if not isinstance(data, dict):
        return ""

    cve_from_detail: str = _extract_cve_from_detail(data.get("detail", {}))
    if cve_from_detail:
        return cve_from_detail

    vuln_direct: SingleJson = (
        data.get("vulnerabilityMatch")
        or data.get("vulnerability_match")
        or {}
    )
    if isinstance(vuln_direct, dict):
        cve_id = _extract_cve_from_vuln(vuln_direct)
        if cve_id:
            return cve_id

    for key in ("cveId", "cve", "cve_id", "cveID", "CVE"):
        val = data.get(key)
        if val and isinstance(val, str):
            return val.strip()

    flat_cve: str = data.get("detail_targetTechnology_vulnerabilityMatch_cveId", "")
    if flat_cve and isinstance(flat_cve, str):
        return flat_cve.strip()

    return ""


def extract_gti_alert_severity(raw_data: SingleJson) -> str:
    """Extract severity across all polymorphic GTI alert types."""
    if not isinstance(raw_data, dict):
        return "MEDIUM"

    resolved_detail: SingleJson = raw_data.get("detail", {})
    resolved_type: str = (
        str(resolved_detail.get("detailType", "")).strip().lower()
        if isinstance(resolved_detail, dict)
        else ""
    )
    camel_key: str = (
        re.sub(r"_([a-z])", lambda m: m.group(1).upper(), resolved_type)
        if resolved_type
        else ""
    )
    sub_detail: SingleJson | None = (
        (resolved_detail.get(resolved_type) or resolved_detail.get(camel_key))
        if isinstance(resolved_detail, dict)
        else None
    )
    if isinstance(sub_detail, dict):
        severity: str = (
            sub_detail.get("severity")
            or sub_detail.get("riskRating")
            or (
                sub_detail.get("vulnerabilityMatch", {}).get("riskRating")
                if isinstance(sub_detail.get("vulnerabilityMatch"), dict)
                else ""
            )
            or ""
        )
        if severity and isinstance(severity, str):
            return severity.strip().upper()

    raw_sev: Any = raw_data.get("severity")
    if isinstance(raw_sev, str) and raw_sev.strip():
        return raw_sev.strip().upper()

    sev_analysis: Any = raw_data.get("severityAnalysis")
    if isinstance(sev_analysis, dict):
        sev_level: Any = sev_analysis.get("severityLevel", "")
        if isinstance(sev_level, str) and sev_level:
            return sev_level.replace("SEVERITY_LEVEL_", "").strip().upper()

    return "MEDIUM"


def _extract_finding_priority(finding: SingleJson, fallback: str) -> str:
    """Extract and format priority level from finding payload.

    Args:
        finding: The raw finding dictionary.
        fallback: Fallback priority string.

    Returns:
        Formatted priority level string.

    """
    priority_analysis: SingleJson = finding.get("priorityAnalysis") or {}
    priority_level: str = (
        (priority_analysis.get("priorityLevel") or "")
        if isinstance(priority_analysis, dict)
        else ""
    )
    return priority_level.replace("PRIORITY_LEVEL_", "").strip().upper() or fallback


def _extract_finding_user(finding: SingleJson, finding_event: SingleJson) -> str:
    """Extract user identifier across finding raw and flattened fields.

    Args:
        finding: The raw finding dictionary.
        finding_event: The flattened finding dictionary.

    Returns:
        First non-empty user identifier string.

    """
    return _first_str(
        finding.get("author"),
        finding.get("user_name"),
        finding.get("userName"),
        finding.get("username"),
        finding.get("user"),
        finding_event.get("author"),
        finding_event.get("user_name"),
        finding_event.get("userName"),
        finding_event.get("username"),
        finding_event.get("user"),
    )


@dataclasses.dataclass(slots=True, frozen=True)
class GTIAlert(BaseModel):
    """Class to create data model for Google Threat Intelligence (GTI) Alert object."""

    raw_flat_data: SingleJson
    alert_id: str
    display_name: str
    detail_type: str
    severity: str
    priority: str
    ai_summary: str
    create_time_unix: int
    update_time_unix: int
    create_time_str: str
    cve: str = ""
    findings_details: list[SingleJson] = dataclasses.field(default_factory=list)
    documents_details: list[SingleJson] = dataclasses.field(default_factory=list)

    @classmethod
    def from_json(
        cls,
        raw_data: SingleJson,
        findings_details: list[SingleJson] | None = None,
        documents_details: list[SingleJson] | None = None,
    ) -> GTIAlert:
        """Construct a GTIAlert dataclass object.

        Args:
            raw_data: Raw JSON dictionary from the Alerts API endpoint.
            findings_details: List of JSON dictionaries from Findings API.
            documents_details: List of JSON dictionaries from Documents API.

        Returns:
            GTIAlert dataclass instance.

        """
        create_time_str, create_time_unix, update_time_unix = _parse_audit_timestamps(raw_data)
        detail: SingleJson = raw_data.get("detail", {})
        detail_type: str = str(detail.get("detailType", "")).strip().lower()
        severity: str = extract_gti_alert_severity(raw_data)
        priority: str = _extract_priority(raw_data)
        raw_flat: SingleJson = dict_to_flat(raw_data)
        cve: str = _extract_cve(raw_data) or _extract_cve(raw_flat)

        return cls(
            raw_data=raw_data,
            raw_flat_data=raw_flat,
            alert_id=raw_data.get("name", ""),
            display_name=raw_data.get("displayName", ""),
            detail_type=detail_type,
            severity=severity,
            priority=priority,
            ai_summary=raw_data.get("aiSummary", ""),
            create_time_unix=create_time_unix,
            update_time_unix=update_time_unix,
            create_time_str=create_time_str,
            cve=cve,
            findings_details=findings_details or [],
            documents_details=documents_details or [],
        )

    @property
    def timestamp(self) -> int:
        """Return alert timestamp for TIPCommon filtering."""
        return self.update_time_unix

    @property
    def summary(self) -> str:
        """Return the AI summary, falling back to the display name when it is absent."""
        return self.ai_summary or self.display_name

    def _build_alert_event(self) -> SingleJson:
        main_event: SingleJson = dict(self.raw_flat_data)
        main_event.update(
            {
                "eventType": "Alert",
                "id": self.alert_id,
                "title": self.display_name,
                "alert_type": self.detail_type,
                "severity": self.severity,
                "priority": self.priority,
                "ai_summary": self.summary,
                "created_at": self.create_time_str,
            }
        )
        if self.cve:
            _apply_cve_aliases(main_event, self.cve)

        alert_user: str = _first_str(
            main_event.get("author"),
            main_event.get("user_name"),
            main_event.get("userName"),
            main_event.get("username"),
            main_event.get("user"),
        )
        if alert_user:
            _apply_user_aliases(main_event, alert_user)

        return main_event

    def _build_single_finding_event(self, idx: int, finding: SingleJson) -> SingleJson:
        """Construct a standardized finding event dictionary from raw finding payload.

        Args:
            idx: The finding index within the alert.
            finding: The raw finding dictionary.

        Returns:
            The flattened and enriched finding event dictionary.

        """
        finding_name: str = finding.get("name", f"{self.alert_id}_finding_{idx}")
        finding_event: SingleJson = dict_to_flat(finding)
        finding_severity: str = (
            extract_gti_alert_severity(finding) or self.severity
        )
        finding_priority: str = _extract_finding_priority(finding, self.priority)
        finding_updates: SingleJson = {
            "eventType": "Finding",
            "id": finding_name,
            "alert_id": self.alert_id,
            "alert_type": self.detail_type,
            "title": finding.get("displayName") or self.display_name,
            "provider": finding.get("provider", ""),
            "severity": finding_severity,
            "priority": finding_priority,
            "ai_summary": finding.get("aiSummary") or self.summary,
            "created_at": (
                finding.get("audit", {}).get("createTime")
                or self.create_time_str
            ),
        }
        finding_cve: str = _extract_cve(finding) or self.cve
        if finding_cve:
            _apply_cve_aliases(finding_updates, finding_cve)

        finding_user: str = _extract_finding_user(finding, finding_event)
        if finding_user:
            _apply_user_aliases(finding_updates, finding_user)

        finding_event.update(finding_updates)
        return finding_event

    def _build_finding_events(self) -> list[SingleJson]:
        return [
            self._build_single_finding_event(idx, finding)
            for idx, finding in enumerate(self.findings_details)
        ]

    def _build_document_events(self) -> list[SingleJson]:
        events: list[SingleJson] = []
        for idx, document in enumerate(self.documents_details):
            doc_name: str = document.get("name", f"{self.alert_id}_document_{idx}")
            doc_event: SingleJson = dict_to_flat(document)
            doc_author: str = _first_str(
                document.get("author"),
                document.get("user_name"),
                document.get("userName"),
                document.get("username"),
                document.get("user"),
                doc_event.get("author"),
                doc_event.get("user_name"),
                doc_event.get("userName"),
                doc_event.get("username"),
                doc_event.get("user"),
            )
            doc_updates: SingleJson = {
                "eventType": "Document",
                "id": doc_name,
                "alert_id": self.alert_id,
                "alert_type": self.detail_type,
                "title": (
                    document.get("title")
                    or document.get("displayName")
                    or self.display_name
                ),
                "severity": self.severity,
                "priority": self.priority,
                "ai_summary": self.summary,
                "sourceUri": document.get("sourceUri", ""),
                "url": document.get("sourceUri", ""),
                "destination_url": document.get("sourceUri", ""),
                "created_at": (
                    document.get("createTime") or self.create_time_str
                ),
            }
            if doc_author:
                _apply_user_aliases(doc_updates, doc_author)

            doc_cve: str = _extract_cve(document) or self.cve
            if doc_cve:
                _apply_cve_aliases(doc_updates, doc_cve)

            doc_event.update(doc_updates)
            events.append(doc_event)

        return events

    def _create_single_entity_event(self, key: str, item: object) -> SingleJson:
        """Create a discrete Entity event dictionary for a multi-value list item."""
        item_str: str = str(item) if isinstance(item, (str, int, float)) else ""
        entity_event: SingleJson = {
            "eventType": "Entity",
            "entity_key": key,
            "alert_id": self.alert_id,
            "alert_type": self.detail_type,
            "title": (
                f"{self.display_name} - {key}: {item_str}"
                if item_str
                else self.display_name
            ),
            "displayName": item_str or self.display_name,
            "severity": self.severity,
            "priority": self.priority,
            "ai_summary": self.summary,
            "created_at": self.create_time_str,
            "createTime": self.create_time_str,
            "updateTime": self.create_time_str,
        }
        if item_str:
            entity_event["entity_value"] = item_str
            entity_event[key] = item_str
            lower_key: str = key.lower()
            for keys, aliases in GTI_ENTITY_KEY_ALIASES:
                if lower_key in keys:
                    entity_event.update(dict.fromkeys(aliases, item_str))
                    if lower_key in GTI_ENTITY_USER_KEYS and "@" in item_str:
                        entity_event["email"] = item_str
                    break
        elif isinstance(item, dict):
            entity_event.update(dict_to_flat(item))
        return entity_event

    def _build_entity_events(self, raw_data: SingleJson) -> list[SingleJson]:
        events: list[SingleJson] = []
        dicts_to_check: list[SingleJson] = [raw_data]
        if self.findings_details:
            dicts_to_check.extend(self.findings_details)
        if self.documents_details:
            dicts_to_check.extend(self.documents_details)

        for payload in dicts_to_check:
            for key, value in payload.items():
                if (
                    key.lower() not in GTI_ALERT_ENTITY_KEYS
                    or not isinstance(value, list)
                    or len(value) <= 1
                ):
                    continue
                for item in value:
                    events.append(self._create_single_entity_event(key, item))
        return events

    def to_events(self) -> list[SingleJson]:
        """Convert GTIAlert object into discrete events for SecOps ingestion."""
        raw_data: SingleJson = self.raw_data
        events: list[SingleJson] = [self._build_alert_event()]
        events.extend(self._build_finding_events())
        events.extend(self._build_document_events())
        events.extend(self._build_entity_events(raw_data))
        return events


@dataclasses.dataclass(slots=True, frozen=True)
class AgenticSession(BaseModel):
    """Class to create data model for GTI Agentic Session."""

    session_id: str
    title: str | None = None
    response_text: str | None = None
    is_completed: bool = False

    def to_json(self) -> SingleJson:
        """Convert AgenticSession to JSON."""
        return {
            "session_id": self.session_id,
            "title": self.title,
            "response_text": self.response_text,
        }
