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
from threat_q.core.datamodels import (
    Indicator,
    Comment,
    Attribute,
    Source,
    IndicatorDetails,
    LinkedObject,
    Adversary,
    UniversalObject,
    MalwareDetails,
    DefaultObject,
    RelatedObject,
    Event,
    IndicatorScore,
    UpdateIndicator,
    LinkedEntities,
)


class ThreatQParser:

    @staticmethod
    def build_indicator_object(indicator_json):
        if not indicator_json:
            return None

        data = indicator_json[0]
        indicator_class = data.get("class")
        indicator_score = data.get("score")
        indicator_value = data.get("value")
        indicator_id = data.get("id")
        indicator_tags = ",".join(data.get("tags", []))
        indicator_description = data.get("description")
        indicator_type = data.get("type", {}).get("name")
        indicator_status = data.get("status", {}).get("name")
        indicator_status_id = data.get("status_id")
        indicator_updated_at = data.get("updated_at")
        indicator_created_at = data.get("created_at")

        comments = []
        if data.get("comments"):
            comments = [
                ThreatQParser.build_comment_object(comment_json)
                for comment_json in data.get("comments")
            ]
        attributes = []
        if data.get("attributes"):
            attributes = [
                ThreatQParser.build_attribute_object(attribute_json)
                for attribute_json in data.get("attributes")
            ]
        sources = []
        if data.get("sources"):
            sources = [
                ThreatQParser.build_source_object(source_json)
                for source_json in data.get("sources")
            ]

        indicator_json = {"total": len(indicator_json), "data": indicator_json}
        return Indicator(
            raw_data=indicator_json,
            indicator_class=indicator_class,
            indicator_score=indicator_score,
            indicator_value=indicator_value,
            indicator_id=indicator_id,
            indicator_tags=indicator_tags,
            indicator_description=indicator_description,
            indicator_type=indicator_type,
            indicator_status=indicator_status,
            indicator_status_id=indicator_status_id,
            indicator_updated_at=indicator_updated_at,
            indicator_created_at=indicator_created_at,
            comments=comments,
            attributes=attributes,
            sources=sources,
        )

    @staticmethod
    def build_updated_indicator_object(indicator_json):
        if not indicator_json:
            return None

        data = indicator_json
        indicator_id = data.get("id")
        indicator_type_id = data.get("type_id")
        indicator_class = data.get("class")
        indicator_hash = data.get("hash")
        indicator_value = data.get("value")
        indicator_description = data.get("description")
        indicator_created_at = data.get("created_at")
        indicator_expires_at = data.get("expires_at")
        indicator_expired_at = data.get("expired_at")
        indicator_expires_calculated_at = data.get("expires_calculated_at")
        indicator_last_detected_at = data.get("last_detected_at")
        indicator_updated_at = data.get("updated_at")
        indicator_touched_at = data.get("touched_at")

        return UpdateIndicator(
            raw_data=indicator_json,
            indicator_id=indicator_id,
            indicator_type_id=indicator_type_id,
            indicator_class=indicator_class,
            indicator_hash=indicator_hash,
            indicator_value=indicator_value,
            indicator_description=indicator_description,
            indicator_created_at=indicator_created_at,
            indicator_expires_at=indicator_expires_at,
            indicator_expired_at=indicator_expired_at,
            indicator_expires_calculated_at=indicator_expires_calculated_at,
            indicator_last_detected_at=indicator_last_detected_at,
            indicator_updated_at=indicator_updated_at,
            indicator_touched_at=indicator_touched_at,
        )

    @staticmethod
    def build_indicator_score_object(indicator_score_json):
        if not indicator_score_json:
            return None

        data = indicator_score_json
        indicator_id = data.get("indicator_id")
        generated_score = data.get("generated_score")
        manual_score = data.get("manual_score")
        score_config_hash = data.get("score_config_hash")
        indicator_created_at = data.get("created_at")
        indicator_updated_at = data.get("updated_at")

        return IndicatorScore(
            raw_data=indicator_score_json,
            indicator_id=indicator_id,
            generated_score=generated_score,
            manual_score=manual_score,
            score_config_hash=score_config_hash,
            indicator_created_at=indicator_created_at,
            indicator_updated_at=indicator_updated_at,
        )

    @staticmethod
    def build_event_object(event_json):
        if not event_json:
            return None

        data = event_json
        event_title = data.get("title")
        event_type_id = data.get("type_id")
        event_happened_at = data.get("happened_at")
        event_hash = data.get("hash")
        event_updated_at = data.get("updated_at")
        event_created_at = data.get("created_at")
        event_touched_at = data.get("touched_at")
        event_id = data.get("id")
        event_type = data.get("type", {}).get("name")
        event_description = data.get("description")

        return Event(
            raw_data=event_json,
            event_title=event_title,
            event_type_id=event_type_id,
            event_happened_at=event_happened_at,
            event_hash=event_hash,
            event_updated_at=event_updated_at,
            event_created_at=event_created_at,
            event_touched_at=event_touched_at,
            event_id=event_id,
            event_type=event_type,
            event_description=event_description,
        )

    @staticmethod
    def build_comment_object(comment_json):
        comment_value = comment_json.get("value")
        source = comment_json.get(
            "source_name",
            comment_json.get("creator_source_name"),
        )
        updated_at = comment_json.get("updated_at")
        created_at = comment_json.get("created_at")

        return Comment(
            raw_data=comment_json,
            comment_value=comment_value,
            source=source,
            created_at=created_at,
            updated_at=updated_at,
        )

    @staticmethod
    def build_attribute_object(attribute_json):
        value = attribute_json.get("value")
        name = attribute_json.get("name")
        updated_at = attribute_json.get("updated_at")
        created_at = attribute_json.get("created_at")

        return Attribute(
            raw_data=attribute_json,
            value=value,
            name=name,
            created_at=created_at,
            updated_at=updated_at,
        )

    @staticmethod
    def build_source_object(source_json):
        name = source_json.get("name")
        source_type = source_json.get("type")
        updated_at = source_json.get("updated_at")
        created_at = source_json.get("created_at")

        return Source(
            raw_data=source_json,
            name=name,
            source_type=source_type,
            updated_at=updated_at,
            created_at=created_at,
        )

    @staticmethod
    def build_link_object(link_json):
        link_json_data = link_json.get("data", [])[0]
        name = link_json_data.get("name")
        link_id = link_json_data.get("id")
        updated_at = link_json_data.get("updated_at")
        created_at = link_json_data.get("created_at")
        touched_at = link_json_data.get("touched_at")
        pivot = link_json_data.get("pivot")
        value = link_json_data.get("value")
        title = link_json_data.get("title")

        return LinkedEntities(
            raw_data=link_json,
            name=name,
            value=value,
            link_id=link_id,
            updated_at=updated_at,
            created_at=created_at,
            touched_at=touched_at,
            pivot=pivot,
            title=title,
        )

    @staticmethod
    def build_indicator_details_object(indicator_details_json):
        return IndicatorDetails(raw_data=indicator_details_json)

    @staticmethod
    def build_linked_object_object(linked_objects_json, related_object_type=None):
        linked_objects_data = linked_objects_json.get("data", [])
        return [
            LinkedObject(
                raw_data=linked_object_data,
                id=linked_object_data.get("id"),
                title=linked_object_data.get("title"),
                name=linked_object_data.get("name"),
                value=linked_object_data.get("value"),
                description=linked_object_data.get("description"),
                created_at=linked_object_data.get("created_at"),
                updated_at=linked_object_data.get("updated_at"),
                related_object_type=related_object_type,
            )
            for linked_object_data in linked_objects_data
        ]

    @staticmethod
    def build_adversary_object(adversary_json):
        name = adversary_json.get("name")
        updated_at = adversary_json.get("updated_at")
        created_at = adversary_json.get("created_at")
        id = adversary_json.get("id")

        return Adversary(
            raw_data=adversary_json,
            name=name,
            updated_at=updated_at,
            created_at=created_at,
            id=id,
        )

    @staticmethod
    def build_malware_details_object(malwares_details_json):
        malwares_details_data = malwares_details_json.get("data", [])
        return [
            MalwareDetails(
                raw_data=malware_details_data,
                id=malware_details_data.get("id"),
                status_id=malware_details_data.get("status_id"),
                type_id=malware_details_data.get("type_id"),
                description=malware_details_data.get("description"),
                created_at=malware_details_data.get("created_at"),
                updated_at=malware_details_data.get("updated_at"),
            )
            for malware_details_data in malwares_details_data
        ]

    @staticmethod
    def build_universal_object(object_json):
        if not object_json.get("data"):
            return None
        data = object_json.get("data", [])[0]
        return UniversalObject(
            raw_data=data,
            attribute_id=data.get("attribute_id"),
            value=data.get("value"),
            object_id=data.get("id"),
            name=data.get("name"),
            updated_at=data.get("updated_at"),
            created_at=data.get("created_at"),
            attribute=ThreatQParser.build_attribute_object(data.get("attribute", {})),
            sources=[
                ThreatQParser.build_source_object(source_json)
                for source_json in data.get("sources", [])
            ],
        )

    @staticmethod
    def build_default_object(object_json):
        data = object_json.get("data", {})
        return DefaultObject(
            raw_data=data,
            value=data.get("value"),
            description=data.get("description"),
            item_id=data.get("id"),
            object_id=data.get("object_id"),
            updated_at=data.get("updated_at"),
            created_at=data.get("created_at"),
            object_code=data.get("object_code"),
            object_name=data.get("object_name"),
            object_name_plural=data.get("object_name_plural"),
        )

    @staticmethod
    def build_entity_related_objects(related_objects_json, related_object_type=None):
        related_objects_data = related_objects_json.get("data", [])
        return [
            RelatedObject(
                raw_data=related_object_data,
                type_id=related_object_data.get("type_id"),
                value=related_object_data.get("value"),
                object_id=related_object_data.get("id"),
                status_id=related_object_data.get("status_id"),
                description=related_object_data.get("description"),
                title=related_object_data.get("title"),
                name=related_object_data.get("name"),
                started_at=related_object_data.get("started_at"),
                ended_at=related_object_data.get("ended_at"),
                updated_at=related_object_data.get("updated_at"),
                created_at=related_object_data.get("created_at"),
                touched_at=related_object_data.get("touched_at"),
                deleted_at=related_object_data.get("deleted_at"),
                related_object_type=related_object_type,
            )
            for related_object_data in related_objects_data
        ]
