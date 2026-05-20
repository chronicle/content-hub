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

"""ThreatConnect V3 indicator data models."""

from __future__ import annotations

from typing import Any

from TIPCommon.data_models import BaseDataModel


class IndicatorData(BaseDataModel):
    """ThreatConnect V3 Indicator Data Model."""

    __slots__ = (
        "id",
        "type",
        "rating",
        "confidence",
        "description",
        "date_added",
        "last_modified",
        "web_link",
        "tags",
        "attributes",
        "owners",
        "security_labels",
        "v3_raw_data",
    )

    @classmethod
    def from_json(cls, json_data: dict[str, Any]) -> IndicatorData:
        """Create IndicatorData from JSON dict."""
        return cls(json_data)

    def __init__(self, raw_data: dict[str, Any]) -> None:
        """Initialize IndicatorData from raw V3 API payload."""
        super().__init__(raw_data)
        self.v3_raw_data = raw_data
        self.id = raw_data.get("id")
        self.type = raw_data.get("type", "Address")
        self.rating = raw_data.get("rating")
        self.confidence = raw_data.get("confidence")
        self.description = raw_data.get("description")
        self.date_added = raw_data.get("dateAdded")
        self.last_modified = raw_data.get("lastModified")
        self.web_link = raw_data.get("webLink")

        self.tags = [tag.get("name") for tag in raw_data.get("tags", {}).get("data", []) if tag.get("name")]

        self.attributes: dict[str, list[str]] = {}
        for attr in raw_data.get("attributes", {}).get("data", []):
            attr_type = attr.get("type")
            attr_val = attr.get("value")
            if attr_type and attr_val:
                if attr_type not in self.attributes:
                    self.attributes[attr_type] = []
                self.attributes[attr_type].append(attr_val)

        owner_list = []
        if raw_data.get("ownerName"):
            owner_list.append({
                "name": raw_data.get("ownerName"),
                "id": raw_data.get("ownerId"),
                "type": "Organization",
            })
        self.owners = {"owner": owner_list}

        self.security_labels = {
            "securityLabel": [
                {"name": label.get("name")}
                for label in raw_data.get("securityLabels", {}).get("data", [])
                if label.get("name")
            ]
        }

    def to_v2_json(self, indicator_value: str) -> dict[str, Any]:
        """Map to V2 format and merge all additional V3 fields for zero regression."""
        type_mapping = {
            "Address": "address",
            "EmailAddress": "address",
            "File": "file",
            "Host": "host",
            "URL": "url",
        }
        v2_type = type_mapping.get(self.type, "address")

        v2_fields = {
            "webLink": self.web_link,
            "threatAssessRating": self.rating,
            "rating": self.rating,
            "threatAssessConfidence": self.confidence,
            "confidence": self.confidence,
            "description": self.description,
            "dateAdded": self.date_added,
            "lastModified": self.last_modified,
            "text": indicator_value,
            "id": self.id,
        }

        for k, v in self.v3_raw_data.items():
            if k not in ["tags", "attributes", "associatedGroups", "securityLabels"]:
                v2_fields[k] = v

        return {
            "general": {v2_type: v2_fields},
            "tags": self.tags,
            "attributes": self.attributes,
            "owners": self.owners,
            "securityLabels": self.security_labels,
            "groups": None,
            "indicators": {"indicator": [], "resultCount": 0},
            "observations": {"observation": [], "resultCount": 0},
            "observationCount": {"observationCount": {"count": 0}},
            "victimAssets": {"victimAsset": [], "resultCount": 0},
            "victims": {"victim": [], "resultCount": 0},
        }
