# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, quote

from TIPCommon import dict_to_flat, add_prefix_to_dict
from .constants import (
    ENRICHMENT_PREFIX,
    MALWARE_URL,
    INDICATOR_URL,
    ACTOR_URL,
    VULNERABILITY_URL,
)


class BaseModel:
    """
    Base model for inheritance
    """

    id: str
    report_link: Optional[str]
    report_link_template: str

    def __init__(self, raw_data: Dict[str, Any]):
        self.raw_data = raw_data

    def to_json(self) -> dict:
        if self.report_link:
            return {**self.raw_data, "report_link": self.report_link}
        return self.raw_data

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_flat(self):
        return dict_to_flat(self.raw_data)

    def set_report_link(self, ui_root: str) -> None:
        self.report_link = urljoin(
            ui_root, self.report_link_template.format(**self.get_report_link_args())
        )

    def get_report_link_args(self) -> dict:
        return {"id": self.id}


class Indicator(BaseModel):
    report_link_template = INDICATOR_URL

    def __init__(
        self,
        raw_data: Dict[str, Any],
        id: str,
        associated_hashes: Optional[List[Dict[str, Any]]] = None,
        first_seen: Optional[str] = None,
        last_seen: Optional[str] = None,
        sources: Optional[List[Dict[str, Any]]] = None,
        attributed_associations: Optional[List[Dict[str, Any]]] = None,
        type: Optional[str] = None,
        mscore: Optional[int] = None,
        value: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(raw_data)
        self.associated_hashes = associated_hashes
        if self.associated_hashes:
            self.associated_hashes_values = [
                value.get("value") for value in self.associated_hashes
            ]
        else:
            self.associated_hashes_values = []
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.type = type
        self.sources = sources
        self.mscore = mscore
        self.attributed_associations = (
            attributed_associations if attributed_associations else []
        )
        self.value = value
        self.id = id
        self.value = value
        self.report_link = None

    def to_table(self):
        data = {
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "sources": (
                ",".join(
                    list(
                        set([source.get("source_name", "") for source in self.sources])
                    )
                )
                if self.sources
                else ""
            ),
            "mscore": self.mscore,
            "report_link": self.report_link,
        }

        associations = self._get_associations_grouped_by_type()

        for type, association_names in associations.items():
            if association_names:
                data.update(
                    {f"attributed_associations_{type}": ",".join(association_names)}
                )

        return data

    def _get_associations_grouped_by_type(self):
        data = {}
        for association in self.attributed_associations:
            if not data.get(association.get("type"), ""):
                data[association.get("type")] = []

            data[association.get("type")].append(association.get("name", ""))

        return data

    def to_enrichment(self):
        enrichment_data = self.to_table()
        return add_prefix_to_dict(dict_to_flat(enrichment_data), ENRICHMENT_PREFIX)

    def to_insight(self):
        html_content = ""
        html_content += "<h2><strong>Score: "
        html_content += f"<span {self._get_insight_score_color()}>{self.mscore}</span>"
        html_content += "</strong></h2>"
        html_content += f"<p><strong>First Seen: </strong> {self.first_seen}<br/>"
        html_content += f"<strong>Last Seen: </strong> {self.last_seen}<br/>"
        html_content += (
            f"<strong>Sources: </strong> "
            f"{','.join(list(set([source.get('source_name', '') for source in self.sources]))) if self.sources else ''}"
            "<br/></p>"
        )
        html_content += (
            f"<p>For more details visit the following link: <a href='{self.report_link}' target='_blank'>"
            f"{self.report_link}&nbsp;</a></p>"
        )

        return html_content

    def _get_insight_score_color(self):
        if self.mscore in range(0, 24):
            return "style='color: #000000'"
        elif self.mscore in range(25, 49):
            return "style='color: #ffff00'"
        elif self.mscore in range(50, 74):
            return "style='color: #ff9900'"
        elif self.mscore in range(75, 100):
            return "style='color: #ff0000'"

    def get_report_link_args(self) -> dict:
        return {"value": quote(self.value, safe=""), "type": self.type}


class ThreatActor(BaseModel):
    report_link_template = ACTOR_URL

    def __init__(
        self,
        raw_data: dict,
        id: str,
        locations: Dict[str, Any],
        motivations: List[Dict[str, Any]] = None,
        aliases: List[Dict[str, Any]] = None,
        industries: List[Dict[str, Any]] = None,
        malware: List[Dict[str, Any]] = None,
        cve: List[Dict[str, Any]] = None,
        description: str = None,
        last_activity_time: str = None,
        **kwargs: dict,
    ):
        super().__init__(raw_data)
        self.motivations = motivations
        self.aliases = aliases
        self.industries = industries
        self.malware = malware
        self.locations = locations
        self.location_sources = self.locations.get("source", [])
        self.location_targets = self.locations.get("target", [])
        self.cve = cve
        self.id = id
        self.description = description
        self.last_activity_time = last_activity_time
        self.report_link = None

    def to_table(self):
        return {
            "motivations": (
                ", ".join([m.get("name", "") for m in self.motivations])
                if self.motivations
                else ""
            ),
            "aliases": (
                ", ".join([a.get("name", "") for a in self.aliases])
                if self.aliases
                else ""
            ),
            "industries": (
                ", ".join([i.get("name", "") for i in self.industries])
                if self.industries
                else ""
            ),
            "malware": (
                ", ".join([m.get("name", "") for m in self.malware])
                if self.malware
                else ""
            ),
            "locations_source": (
                ", ".join(
                    [
                        source.get("country", {}).get("name", {})
                        for source in self.location_sources
                    ]
                )
                if self.location_sources
                else ""
            ),
            "locations_target": (
                ", ".join([target.get("name", "") for target in self.location_targets])
                if self.location_targets
                else ""
            ),
            "cve": (
                ", ".join([cve.get("cve_id", "") for cve in self.cve])
                if self.cve
                else ""
            ),
            "description": self.description,
            "last_activity_time": self.last_activity_time,
            "report_link": self.report_link,
        }

    def to_enrichment(self):
        enrichment_data = self.to_table()
        return add_prefix_to_dict(dict_to_flat(enrichment_data), ENRICHMENT_PREFIX)

    def to_insight(self):
        html_content = ""
        html_content += "<h2>Description</h2>"
        html_content += f"<p>{self.description}</p>"
        html_content += f"<h2>Details</h2>"
        html_content += (
            f"<p><strong>Motivation:</strong> "
            f"{', '.join([m.get('name', '') for m in self.motivations]) if self.motivations else 'N/A'}<br/>"
        )
        html_content += (
            f"<strong>Aliases:</strong> "
            f"{', '.join([a.get('name', '') for a in self.aliases]) if self.aliases else 'N/A'}<br/>"
        )
        html_content += (
            f"<strong>Industries:</strong> "
            f"{', '.join([i.get('name', '') for i in self.industries]) if self.industries else 'N/A'}<br/>"
        )
        html_content += (
            f"<strong>Source Location:</strong> "
            f"{', '.join([source.get('country', {}).get('name', {}) for source in self.location_sources]) if self.location_sources else 'N/A'}<br/>"
        )
        html_content += (
            f"<strong>Target Location:</strong> "
            f"{', '.join([target.get('name', '') for target in self.location_targets]) if self.location_targets else 'N/A'}<br/>"
        )
        html_content += (
            f"<strong>Related Malware:</strong> "
            f"{', '.join([m.get('name', '') for m in self.malware]) if self.malware else 'N/A'}<br/>"
        )
        html_content += (
            f"<strong>Related CVEs:</strong> "
            f"{', '.join([cve.get('cve_id', '') for cve in self.cve]) if self.cve else 'N/A'}<br/>"
        )
        html_content += (
            f"<strong>Last Activity Time:</strong> {self.last_activity_time}<br/></p>"
        )

        html_content += (
            f"<p>For more details visit the following link: <a href='{self.report_link}' target='_blank'>"
            f"{self.report_link}&nbsp;</a></p>"
        )

        return html_content


class Vulnerability(BaseModel):
    report_link_template = VULNERABILITY_URL

    def __init__(
        self,
        raw_data: dict,
        id: str,
        sources: Dict[str, Any] = None,
        exploitation_state: str = None,
        date_of_disclosure: str = None,
        title: str = None,
        vendor_fix_references: List[Dict[str, Any]] = None,
        exploitation_vectors: List[str] = None,
        description: str = None,
        risk_rating: str = None,
        available_mitigation: List[str] = None,
        exploitation_consequence: str = None,
        executive_summary: str = None,
        analysis: str = None,
        **kwargs: dict,
    ):
        super().__init__(raw_data)
        self.sources = sources
        self.exploitation_state = exploitation_state
        self.date_of_disclosure = date_of_disclosure
        self.title = title
        self.vendor_fix_references = vendor_fix_references
        self.exploitation_vectors = exploitation_vectors
        self.description = description
        self.risk_rating = risk_rating
        self.id = id
        self.available_mitigation = available_mitigation
        self.exploitation_consequence = exploitation_consequence
        self.executive_summary = executive_summary
        self.analysis = analysis
        self.report_link = None

    def to_table(self):
        return {
            "sources": (
                ", ".join([source.get("source_name", "") for source in self.sources])
                if self.sources
                else ""
            ),
            "exploitation_state": self.exploitation_state,
            "date_of_disclosure": self.date_of_disclosure,
            "vendor_fix_references": (
                ", ".join([v.get("url", {}) for v in self.vendor_fix_references])
                if self.vendor_fix_references
                else ""
            ),
            "title": self.title,
            "exploitation_vectors": (
                ", ".join(self.exploitation_vectors)
                if self.exploitation_vectors
                else ""
            ),
            "description": self.description,
            "risk_rating": self.risk_rating,
            "available_mitigation": (
                ", ".join(self.available_mitigation)
                if self.available_mitigation
                else ""
            ),
            "report_link": self.report_link,
        }

    def to_enrichment(self):
        enrichment_data = self.to_table()
        return add_prefix_to_dict(dict_to_flat(enrichment_data), ENRICHMENT_PREFIX)

    def to_insight(self):
        html_content = ""
        html_content += f"<h2>Risk Rating: "
        html_content += (
            f"<span {self._get_insight_score_color()}>{self.risk_rating}</span></h2>"
        )
        html_content += f"<h2>{self.title}</h2>"
        html_content += "<h2>Description</h2>"
        html_content += f"<p>{self.description or 'N/A'}</p>"
        html_content += "<h2>Executive Summary</h2>"
        html_content += f"<p>{self.executive_summary}</p>"
        html_content += "<h2>Analysis</h2>"
        html_content += f"<p>{self.analysis}</p>"
        html_content += "<h2>Vendor Fix References</h2><ol>"
        for ref in self.vendor_fix_references:
            html_content += f"<li>{ref.get('url', '')}</li>"
        html_content += "</ol><h2>Details</h2>"
        html_content += (
            f"<p><strong>Exploitation State:</strong> {self.exploitation_state}<br/>"
        )
        html_content += (
            f"<strong>Date Of Disclosure:</strong> {self.date_of_disclosure}<br/>"
        )
        html_content += (
            f"<strong>Exploitation Vectors:</strong> "
            f"{', '.join(self.exploitation_vectors) if self.exploitation_vectors else 'N/A'}<br/>"
        )
        html_content += f"<strong>Exploitation Consequence:</strong> {self.exploitation_consequence}<br/></p>"
        html_content += (
            f"<p>For more details visit the following link: <a href='{self.report_link}' target='_blank'>"
            f"{self.report_link}&nbsp;</a></p>"
        )

        return html_content

    def _get_insight_score_color(self):
        color_picker = {
            "LOW": "#33cccc",
            "MEDIUM": "#ffcc00",
            "HIGH": "#ff9900",
            "CRITICAL": "#ff0000",
        }

        return f"style='color: {color_picker[self.risk_rating.upper()]}'"


class Malware(BaseModel):
    report_link_template = MALWARE_URL

    def __init__(
        self,
        raw_data: dict,
        id: str,
        name: str = None,
        description: str = None,
        aliases: List[Dict[str, Any]] = None,
        last_activity_time: str = None,
        capabilities: List[Dict[str, Any]] = None,
        industries: List[Any] = None,
        **kwargs: dict,
    ):
        super().__init__(raw_data)
        self.id = id
        self.name = name
        self.description = description
        self.aliases = aliases
        self.last_activity_time = last_activity_time
        self.capabilities = capabilities
        self.industries = industries
        self.report_link = None

    def to_table(self):
        return {
            "Name": self.name,
            "Description": self.description,
            "Aliases": (
                ", ".join([alias.get("name", "") for alias in self.aliases])
                if self.aliases
                else ""
            ),
            "Last Activity Time": self.last_activity_time,
        }

    def to_insight(self):
        html_content = ""
        html_content += "<h2>Description</h2>"
        html_content += f"<p>{self.description}</p>"
        html_content += "<h2>Capabilities</h2><ol>"
        for capability in self.capabilities:
            html_content += f"<li>{capability.get('name', '')}</li>"
        html_content += "</ol>"
        html_content += "<h2>Industries</h2><ol>"
        for industry in self.industries:
            html_content += f"<li>{industry.get('name', '')}</li>"
        html_content += "</ol>"
        html_content += "<h2>Details</h2>"
        html_content += (
            f"<p><strong>Aliases:</strong> "
            f"{', '.join([alias.get('name', '') for alias in self.aliases]) if self.aliases else 'N/A'}"
            f"<br/>"
        )
        html_content += (
            f"<strong>Last Activity Time:</strong> {self.last_activity_time}<br/></p>"
        )
        html_content += (
            f"<p>For more details visit the following link: <a href='{self.report_link}' target='_blank'>"
            f"{self.report_link}&nbsp;</a></p>"
        )

        return html_content
