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

from .constants import EXCLUDE_FIELDS_SET, MAX_INT_SENTINEL, PLURAL_MAPPING


def get_singular_type_key(group_type: str) -> str:
    """Map V3 group type to V2 singular camelCase style."""
    parts = group_type.split()
    if not parts:
        return ""
    first = parts[0].lower()
    others = [p.capitalize() for p in parts[1:]]
    return "".join([first] + others)


def get_plural_type_key(group_type: str) -> str:
    """Map V3 group type to V2 plural camelCase style."""
    if group_type in PLURAL_MAPPING:
        return PLURAL_MAPPING[group_type]

    key = get_singular_type_key(group_type)
    if key.endswith("y"):
        return key[:-1] + "ies"
    return key + "s"


def get_owner_type(owner_name: str | None) -> str:
    """Determine the type of owner based on its name.

    (Source, Organization, Community).
    """
    if not owner_name:
        return "Organization"
    owner_name_lower = owner_name.lower()
    if (
        "source" in owner_name_lower
        or "library" in owner_name_lower
        or "feed" in owner_name_lower
    ):
        return "Source"
    if "community" in owner_name_lower:
        return "Community"
    return "Organization"


def estimate_cal_status(rating: float | None, score: int | None) -> int | None:
    """Defensively estimate and map the legacy V2 calIndicatorStatus.

    Maps when missing in V3.
    """
    r = rating or 0.0
    s = score or 0

    if r > 1.0 or s > 500:
        return 3
    if s > 0 or r == 0.0:
        return 2
    return 1


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
        "associated_groups",
        "associated_indicators",
        "observations",
        "raw_attributes",
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

        self._parse_tags(raw_data.get("tags"))
        self._parse_attributes(raw_data.get("attributes"))
        self._parse_owners(raw_data)
        self._parse_security_labels(raw_data.get("securityLabels"))
        self._parse_associated_groups(raw_data)
        self._parse_associated_indicators(raw_data)
        self.observations = raw_data.get("observations")

    def _parse_tags(self, tags_data: Any) -> None:
        """Parse tags list from V3 tags container."""
        self.tags = []
        if isinstance(tags_data, dict):
            tags_list = tags_data.get("data", []) or []
            self.tags = [
                tag.get("name")
                for tag in tags_list
                if isinstance(tag, dict) and tag.get("name")
            ]
        elif isinstance(tags_data, list):
            for tag in tags_data:
                if isinstance(tag, dict) and tag.get("name"):
                    self.tags.append(tag.get("name"))
                elif isinstance(tag, str):
                    self.tags.append(tag)

    def _parse_attributes(self, attributes_data: Any) -> None:
        """Parse attributes container and mapped raw list."""
        self.attributes = {}
        self.raw_attributes = []
        if isinstance(attributes_data, dict):
            for attr in attributes_data.get("data", []) or []:
                if not isinstance(attr, dict):
                    continue
                attr_type = attr.get("type")
                attr_val = attr.get("value")
                if attr_type and attr_val:
                    if attr_type not in self.attributes:
                        self.attributes[attr_type] = []
                    self.attributes[attr_type].append(attr_val)
                self.raw_attributes.append({
                    "id": attr.get("id"),
                    "type": attr_type,
                    "value": attr_val,
                    "displayed": attr.get("displayed", True),
                })

    def _parse_owners(self, raw_data: dict[str, Any]) -> None:
        """Parse owner details container."""
        owner_list = []
        owner_name = raw_data.get("ownerName")
        if owner_name:
            owner_list.append({
                "name": owner_name,
                "id": raw_data.get("ownerId"),
                "type": get_owner_type(owner_name),
            })
        self.owners = {"owner": owner_list}

    def _parse_security_labels(self, labels_data: Any) -> None:
        """Parse security labels and mapped envelope count."""
        if isinstance(labels_data, dict):
            self.security_labels = {
                "resultCount": len(labels_data.get("data") or []),
                "securityLabel": [
                    {"name": label.get("name")}
                    for label in labels_data.get("data") or []
                    if isinstance(label, dict) and label.get("name")
                ]
            }
        else:
            self.security_labels = {
                "resultCount": 0,
                "securityLabel": []
            }

    def _parse_associated_groups(self, raw_data: dict[str, Any]) -> None:
        """Parse associated groups payload list."""
        self.associated_groups = []
        groups_data = raw_data.get("associatedGroups") or raw_data.get("groups")
        if isinstance(groups_data, dict):
            for grp in groups_data.get("data", []) or []:
                self.associated_groups.append(grp)
        elif isinstance(groups_data, list):
            for grp in groups_data:
                self.associated_groups.append(grp)

    def _parse_associated_indicators(self, raw_data: dict[str, Any]) -> None:
        """Parse associated indicators payload list."""
        self.associated_indicators = []
        indicators_data = (
            raw_data.get("associatedIndicators")
            or raw_data.get("indicators")
        )
        if isinstance(indicators_data, dict):
            for ind in indicators_data.get("data", []) or []:
                self.associated_indicators.append(ind)
            for ind in indicators_data.get("indicator", []) or []:
                self.associated_indicators.append(ind)
        elif isinstance(indicators_data, list):
            for ind in indicators_data:
                self.associated_indicators.append(ind)

    def _parse_sort_id(self, x: dict[str, Any]) -> tuple[int, str]:
        """Robust, homogeneous-type sorting helper utilizing static sentinels."""
        raw_id = x.get("id")
        if raw_id is None:
            return (0, "")
        str_id = str(raw_id).strip()
        if str_id.isdigit() or (str_id.startswith('-') and str_id[1:].isdigit()):
            return (int(str_id), "")
        return (MAX_INT_SENTINEL, str_id)

    def _map_v2_fields(self, indicator_value: str) -> dict[str, Any]:
        """Isolate and construct base legacy V2 indicator fields."""
        v2_fields = {
            "webLink": self.web_link,
            "description": self.description,
            "dateAdded": self.date_added,
            "lastModified": self.last_modified,
            "text": indicator_value,
            "summary": indicator_value,
            "id": self.id,
            "type": self.type,
            "ownerId": self.v3_raw_data.get("ownerId"),
            "ownerName": self.v3_raw_data.get("ownerName"),
            "privateFlag": self.v3_raw_data.get("privateFlag", False),
            "active": self.v3_raw_data.get("active", True),
            "activeLocked": self.v3_raw_data.get("activeLocked", False),
            "legacyLink": self.v3_raw_data.get("legacyLink"),
        }

        if self.type == "File" and "sha1" in self.v3_raw_data:
            v2_fields["sha1"] = self.v3_raw_data.get("sha1")

        self._backfill_v2_owner(v2_fields)
        self._backfill_threat_assess(v2_fields)
        self._backfill_cal_status(v2_fields)

        for k, v in self.v3_raw_data.items():
            if k not in EXCLUDE_FIELDS_SET and k not in v2_fields:
                v2_fields[k] = v

        return v2_fields

    def _backfill_v2_owner(self, v2_fields: dict[str, Any]) -> None:
        """Resolve and backfill owner details."""
        if self.owners and self.owners.get("owner"):
            v2_fields["owner"] = self.owners["owner"][0]
        elif self.v3_raw_data.get("ownerName"):
            owner_name = self.v3_raw_data.get("ownerName")
            v2_fields["owner"] = {
                "id": self.v3_raw_data.get("ownerId"),
                "name": owner_name,
                "type": get_owner_type(owner_name),
            }

    def _backfill_threat_assess(self, v2_fields: dict[str, Any]) -> None:
        """Extract and map raw threatAssess container fields recursively."""
        threat_assess = self.v3_raw_data.get("threatAssess", {})
        if isinstance(threat_assess, dict) and threat_assess:
            rating = (
                threat_assess.get("rating")
                if threat_assess.get("rating") is not None
                else threat_assess.get("threatAssessRating")
            )
            confidence = (
                threat_assess.get("confidence")
                if threat_assess.get("confidence") is not None
                else threat_assess.get("threatAssessConfidence")
            )
            score = (
                threat_assess.get("score")
                if threat_assess.get("score") is not None
                else threat_assess.get("threatAssessScore")
            )
            cal_status = threat_assess.get("calIndicatorStatus")
            
            if rating is not None:
                v2_fields["threatAssessRating"] = rating
                v2_fields["rating"] = rating
            if confidence is not None:
                v2_fields["threatAssessConfidence"] = confidence
                v2_fields["confidence"] = confidence
            if score is not None:
                v2_fields["threatAssessScore"] = score
            if cal_status is not None:
                v2_fields["calIndicatorStatus"] = cal_status

            v2_fields["threatAssessScoreObserved"] = threat_assess.get(
                "threatAssessScoreObserved", 0
            )
            v2_fields["threatAssessScoreFalsePositive"] = threat_assess.get(
                "threatAssessScoreFalsePositive", 0
            )

            for k, v in threat_assess.items():
                v2_key = (
                    f"threatAssess{k.capitalize()}"
                    if not k.startswith("threatAssess")
                    else k
                )
                if v2_key not in v2_fields:
                    v2_fields[v2_key] = v

        if "threatAssessRating" not in v2_fields:
            v2_fields["threatAssessRating"] = self.rating
            v2_fields["rating"] = self.rating
        if "threatAssessConfidence" not in v2_fields:
            v2_fields["threatAssessConfidence"] = self.confidence
            v2_fields["confidence"] = self.confidence
        if "threatAssessScore" not in v2_fields:
            v2_fields["threatAssessScore"] = self.v3_raw_data.get(
                "threatAssessScore", 0
            )

    def _backfill_cal_status(self, v2_fields: dict[str, Any]) -> None:
        """Resolve calIndicatorStatus fallback estimations."""
        cal_status = self.v3_raw_data.get("calIndicatorStatus")
        if cal_status is None:
            cal_status = v2_fields.get("calIndicatorStatus")
        if cal_status is None:
            ta_rating = v2_fields.get("threatAssessRating", self.rating)
            ta_score = v2_fields.get(
                "threatAssessScore", self.v3_raw_data.get("threatAssessScore")
            )
            cal_status = estimate_cal_status(ta_rating, ta_score)

        v2_fields["calIndicatorStatus"] = cal_status

    def _map_associated_groups(self) -> dict[str, list[dict]] | None:
        """Map and flatten the structured V3 associated groups."""
        mapped_groups: dict[str, list[dict]] = {}
        for grp in self.associated_groups:
            if not isinstance(grp, dict):
                continue
            grp_type = grp.get("type", "")
            if not grp_type:
                continue

            plural_key = get_plural_type_key(grp_type)
            singular_key = get_singular_type_key(grp_type)

            mapped_group = self._map_single_group(
                grp, grp_type, singular_key
            )

            if plural_key not in mapped_groups:
                mapped_groups[plural_key] = []
            mapped_groups[plural_key].append(mapped_group)

        for plural_key in mapped_groups:
            mapped_groups[plural_key].sort(key=self._parse_sort_id)

        return mapped_groups if mapped_groups else None

    def _map_single_group(
        self, grp: dict[str, Any], grp_type: str, singular_key: str
    ) -> dict[str, Any]:
        """Convert a single V3 group dict record to V2 schema layout."""
        group_attrs, raw_group_attrs = self._extract_group_attrs(grp)
        group_tags = self._extract_group_tags(grp)
        group_labels = self._extract_group_labels(grp)
        singular_dict = self._extract_group_report(
            grp, group_tags, group_labels, group_attrs, raw_group_attrs
        )

        mapped_group = {
            "id": grp.get("id"),
            "name": grp.get("name"),
            "type": grp_type,
            "ownerName": grp.get("ownerName"),
            "ownerId": grp.get("ownerId"),
            "dateAdded": grp.get("dateAdded"),
            "lastModified": grp.get("lastModified"),
            "webLink": grp.get("webLink"),
            "xid": grp.get("xid"),
            "createdBy": grp.get("createdBy"),
            "upVoteCount": grp.get("upVoteCount", "0"),
            "downVoteCount": grp.get("downVoteCount", "0"),
            singular_key: singular_dict,
            "securityLabels": group_labels,
            "tags": group_tags,
            "attributes": group_attrs,
            "attribute": raw_group_attrs,
        }

        generic_fields = {
            "id",
            "name",
            "type",
            "ownerId",
            "ownerName",
            "dateAdded",
            "lastModified",
            "webLink",
            "createdBy",
            "upVoteCount",
            "downVoteCount",
            "legacyLink",
            "xid",
            "tags",
            "attributes",
            "securityLabels",
            "report",
        }
        
        for k, v in grp.items():
            if k not in generic_fields:
                singular_dict[k] = v
            if k not in {"tags", "attributes", "securityLabels", singular_key}:
                mapped_group[k] = v

        return mapped_group

    def _extract_group_attrs(
        self, grp: dict[str, Any]
    ) -> tuple[dict[str, list[str]], list[dict[str, Any]]]:
        """Extract flat attributes dictionary and raw attribute objects list."""
        group_attrs = {}
        raw_group_attrs = []
        attrs_envelope = grp.get("attributes")
        if isinstance(attrs_envelope, dict):
            for attr in attrs_envelope.get("data", []) or []:
                if not isinstance(attr, dict):
                    continue
                attr_type = attr.get("type")
                attr_val = attr.get("value")
                if attr_type and attr_val:
                    if attr_type not in group_attrs:
                        group_attrs[attr_type] = []
                    group_attrs[attr_type].append(attr_val)
                raw_group_attrs.append({
                    "id": attr.get("id"),
                    "type": attr_type,
                    "value": attr_val,
                    "displayed": attr.get("displayed", True),
                })
        return group_attrs, raw_group_attrs

    def _extract_group_tags(self, grp: dict[str, Any]) -> dict[str, Any]:
        """Extract and package tag envelopes list."""
        group_tags_list = []
        tags_envelope = grp.get("tags")
        if isinstance(tags_envelope, dict):
            raw_tags = tags_envelope.get("data", []) or []
            group_tags_list = [
                {"name": tag.get("name")}
                for tag in raw_tags
                if isinstance(tag, dict) and tag.get("name")
            ]
        return {
            "resultCount": len(group_tags_list),
            "tag": group_tags_list
        }

    def _extract_group_labels(self, grp: dict[str, Any]) -> dict[str, Any]:
        """Extract and package security labels envelopes."""
        group_labels_list = []
        labels_envelope = grp.get("securityLabels")
        if isinstance(labels_envelope, dict):
            raw_labels = labels_envelope.get("data", []) or []
            group_labels_list = [
                {"name": label.get("name")}
                for label in raw_labels
                if isinstance(label, dict) and label.get("name")
            ]
        return {
            "resultCount": len(group_labels_list),
            "securityLabel": group_labels_list
        }

    def _extract_group_report(
        self,
        grp: dict[str, Any],
        group_tags: dict[str, Any],
        group_labels: dict[str, Any],
        group_attrs: dict[str, list[str]],
        raw_group_attrs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Construct the singular inner report details container map."""
        v3_report_raw = grp.get("report", {})
        v3_report = (
            v3_report_raw
            if isinstance(v3_report_raw, dict)
            else {}
        )
        return {
            "id": grp.get("id"),
            "name": grp.get("name"),
            "owner": {
                "id": grp.get("ownerId"),
                "name": grp.get("ownerName"),
                "type": get_owner_type(grp.get("ownerName")),
            },
            "dateAdded": grp.get("dateAdded"),
            "lastModified": grp.get("lastModified"),
            "webLink": grp.get("webLink"),
            "generatedReport": v3_report.get(
                "generatedReport", grp.get("generatedReport", False)
            ),
            "fileName": v3_report.get(
                "fileName", grp.get("fileName", "None")
            ),
            "status": v3_report.get(
                "status", grp.get("status", "Awaiting Upload")
            ),
            "documentType": v3_report.get(
                "documentType", grp.get("documentType", "None")
            ),
            "documentDateAdded": v3_report.get(
                "documentDateAdded", grp.get("documentDateAdded")
            ),
            "publishDate": v3_report.get("publishDate", grp.get("publishDate")),
            "securityLabels": group_labels,
            "tags": group_tags,
            "attributes": group_attrs,
            "attribute": raw_group_attrs,
        }

    def _map_associated_indicators(self) -> list[dict]:
        """Map and sort data records across associated indicators."""
        mapped_indicators = []
        for ind in self.associated_indicators:
            if not isinstance(ind, dict):
                continue
            mapped_ind = self._map_single_indicator(ind)
            mapped_indicators.append(mapped_ind)

        mapped_indicators.sort(key=self._parse_sort_id)
        return mapped_indicators

    def _map_single_indicator(self, ind: dict[str, Any]) -> dict[str, Any]:
        """Convert a single associated indicator V3 record to V2 schema."""
        ind_type = ind.get("type", "Address")
        ind_rating = ind.get("rating")
        ind_confidence = ind.get("confidence")
        ind_owner_name = ind.get("ownerName")

        ind_ta_raw = ind.get("threatAssess", {})
        ind_ta = ind_ta_raw if isinstance(ind_ta_raw, dict) else {}
        
        ind_ta_rating = (
            ind_ta.get("rating")
            if ind_ta.get("rating") is not None
            else ind_ta.get("threatAssessRating")
        )
        ind_ta_confidence = (
            ind_ta.get("confidence")
            if ind_ta.get("confidence") is not None
            else ind_ta.get("threatAssessConfidence")
        )
        ind_ta_score = (
            ind_ta.get("score")
            if ind_ta.get("score") is not None
            else ind_ta.get("threatAssessScore")
        )

        cal_status = ind.get("calIndicatorStatus", ind_ta.get("calIndicatorStatus"))
        if cal_status is None:
            cal_status = estimate_cal_status(
                ind_ta_rating if ind_ta_rating is not None else ind_rating,
                ind_ta_score,
            )

        mapped_ind = {
            "id": ind.get("id"),
            "ownerName": ind_owner_name,
            "ownerId": ind.get("ownerId"),
            "owner": {
                "id": ind.get("ownerId"),
                "name": ind_owner_name,
                "type": get_owner_type(ind_owner_name),
            } if ind_owner_name else None,
            "type": ind_type,
            "dateAdded": ind.get("dateAdded"),
            "lastModified": ind.get("lastModified"),
            "rating": ind_rating,
            "confidence": ind_confidence,
            "threatAssessRating": (
                ind.get("threatAssessRating")
                if ind.get("threatAssessRating") is not None
                else ind_ta_rating
            ),
            "threatAssessConfidence": (
                ind.get("threatAssessConfidence")
                if ind.get("threatAssessConfidence") is not None
                else ind_ta_confidence
            ),
            "threatAssessScore": (
                ind.get("threatAssessScore")
                if ind.get("threatAssessScore") is not None
                else ind_ta_score
            ),
            "threatAssessScoreObserved": ind_ta.get(
                "threatAssessScoreObserved", 0
            ),
            "threatAssessScoreFalsePositive": ind_ta.get(
                "threatAssessScoreFalsePositive", 0
            ),
            "calIndicatorStatus": cal_status,
            "webLink": ind.get("webLink"),
            "summary": ind.get("summary") or ind.get("text"),
            "text": ind.get("text") or ind.get("summary"),
            "privateFlag": ind.get("privateFlag", False),
            "active": ind.get("active", True),
            "activeLocked": ind.get("activeLocked", False),
        }

        if ind_type == "File" and "sha1" in ind:
            mapped_ind["sha1"] = ind.get("sha1")

        exclude_keys = {
            "tags",
            "attributes",
            "securityLabels",
            "associatedGroups",
            "associatedIndicators",
            "threatAssess",
            "owner",
        }
        for k, v in ind.items():
            if k not in exclude_keys:
                mapped_ind[k] = v

        return mapped_ind

    def _map_observations(self) -> tuple[int, list[dict]]:
        """Safely build out metrics structure tracking historical observations."""
        obs_data = self.v3_raw_data.get("observations")
        obs_count = 0
        if isinstance(obs_data, dict):
            obs_count = obs_data.get("count", 0)
        elif isinstance(obs_data, int):
            obs_count = obs_data

        observation_list = []
        if obs_count > 0:
            last_obs = (
                self.v3_raw_data.get("lastObserved")
                or self.v3_raw_data.get("dateAdded")
                or None
            )
            observation_list.append({
                "id": self.id,
                "date": last_obs,
                "count": obs_count,
            })
        return obs_count, observation_list

    def to_v2_json(self, indicator_value: str) -> dict[str, Any]:
        """Map to V2 format and merge all additional V3 fields for zero regression."""
        type_mapping = {
            "Address": "address",
            "EmailAddress": "address",
            "File": "file",
            "Host": "host",
            "URL": "url",
        }
        v2_type = type_mapping.get(
            self.type,
            self.type.lower() if self.type else "address"
        )

        v2_fields = self._map_v2_fields(indicator_value)
        mapped_groups = self._map_associated_groups()
        mapped_indicators = self._map_associated_indicators()
        obs_count, observation_list = self._map_observations()

        mapped_attributes = self.attributes.copy()
        mapped_attributes["attribute"] = self.raw_attributes

        v2_tags_envelope = None
        if self.tags:
            v2_tags_envelope = {
                "resultCount": len(self.tags),
                "tag": [{"name": tag_name} for tag_name in self.tags]
            }

        return {
            "general": {v2_type: v2_fields},
            "tags": v2_tags_envelope,
            "attributes": mapped_attributes,
            "owners": self.owners,
            "securityLabels": self.security_labels,
            "groups": mapped_groups,
            "indicators": {
                "resultCount": len(mapped_indicators),
                "indicator": mapped_indicators,
            },
            "observations": {"resultCount": obs_count, "observation": observation_list},
            "observationCount": {"observationCount": {"count": obs_count}},
            "victimAssets": {"resultCount": 0, "victimAsset": []},
            "victims": {"resultCount": 0, "victim": []},
        }
