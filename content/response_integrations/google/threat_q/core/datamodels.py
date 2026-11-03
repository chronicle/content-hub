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
from TIPCommon import dict_to_flat, flat_dict_to_csv


class Indicator:
    def __init__(
        self,
        raw_data,
        indicator_class=None,
        indicator_score=None,
        indicator_value=None,
        indicator_id=None,
        indicator_tags=None,
        indicator_description=None,
        indicator_type=None,
        indicator_status=None,
        indicator_status_id=None,
        indicator_updated_at=None,
        indicator_created_at=None,
        comments=None,
        attributes=None,
        sources=None,
    ):
        self.raw_data = raw_data
        self.indicator_class = indicator_class
        self.indicator_score = indicator_score
        self.indicator_value = indicator_value
        self.indicator_id = indicator_id
        self.indicator_tags = indicator_tags
        self.indicator_description = indicator_description
        self.indicator_type = indicator_type
        self.indicator_status = indicator_status
        self.indicator_status_id = indicator_status_id
        self.indicator_updated_at = indicator_updated_at
        self.indicator_created_at = indicator_created_at

        self.comments = comments or []
        self.attributes = attributes or []
        self.sources = sources or []

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat_dict())

    def to_dict(self):
        ret = {}
        ret["indicator_class"] = self.indicator_class
        ret["indicator_score"] = self.indicator_score
        ret["indicator_value"] = self.indicator_value
        ret["indicator_id"] = self.indicator_id
        ret["indicator_tags"] = self.indicator_tags
        ret["indicator_description"] = self.indicator_description
        ret["indicator_type"] = self.indicator_type
        ret["indicator_status"] = self.indicator_status
        ret["indicator_update_at"] = self.indicator_updated_at
        ret["indicator_created_at"] = self.indicator_created_at
        return ret

    def comments_table(self):
        flat_comments = [comment.to_flat_dict() for comment in self.comments]
        return flat_comments

    def attributes_table(self):
        flat_attributes = [comment.to_flat_dict() for comment in self.attributes]
        return flat_attributes

    def sources_table(self):
        flat_sources = [comment.to_flat_dict() for comment in self.sources]
        return flat_sources


class UpdateIndicator:
    def __init__(
        self,
        raw_data,
        indicator_id=None,
        indicator_type_id=None,
        indicator_class=None,
        indicator_hash=None,
        indicator_value=None,
        indicator_description=None,
        indicator_created_at=None,
        indicator_expires_at=None,
        indicator_expired_at=None,
        indicator_expires_calculated_at=None,
        indicator_last_detected_at=None,
        indicator_updated_at=None,
        indicator_touched_at=None,
    ):
        self.raw_data = raw_data
        self.indicator_id = indicator_id
        self.indicator_type_id = indicator_type_id
        self.indicator_class = indicator_class
        self.indicator_hash = indicator_hash
        self.indicator_value = indicator_value
        self.indicator_description = indicator_description
        self.indicator_created_at = indicator_created_at
        self.indicator_expires_at = indicator_expires_at
        self.indicator_expired_at = indicator_expired_at
        self.indicator_expires_calculated_at = indicator_expires_calculated_at

        self.indicator_last_detected_at = indicator_last_detected_at
        self.indicator_updated_at = indicator_updated_at
        self.indicator_touched_at = indicator_touched_at

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat_dict())


class LinkedEntities:
    def __init__(
        self,
        raw_data,
        link_id=None,
        name=None,
        created_at=None,
        updated_at=None,
        touched_at=None,
        pivot=None,
        value=None,
        title=None,
    ):

        self.raw_data = raw_data
        self.link_id = link_id
        self.value = value
        self.name = name
        self.created_at = created_at
        self.updated_at = updated_at
        self.touched_at = touched_at
        self.pivot = pivot
        self.title = title

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat_dict())


class IndicatorScore:
    def __init__(
        self,
        raw_data,
        indicator_id=None,
        generated_score=None,
        manual_score=None,
        score_config_hash=None,
        indicator_created_at=None,
        indicator_updated_at=None,
    ):
        self.raw_data = raw_data
        self.indicator_id = indicator_id
        self.generated_score = generated_score
        self.manual_score = manual_score
        self.score_config_hash = score_config_hash
        self.indicator_created_at = indicator_created_at
        self.indicator_updated_at = indicator_updated_at

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat_dict())


class Event:
    def __init__(
        self,
        raw_data,
        event_title=None,
        event_type_id=None,
        event_happened_at=None,
        event_hash=None,
        event_updated_at=None,
        event_created_at=None,
        event_touched_at=None,
        event_id=None,
        event_type=None,
        event_description=None,
    ):
        self.raw_data = raw_data
        self.event_title = event_title
        self.event_type_id = event_type_id
        self.event_happened_at = event_happened_at
        self.event_hash = event_hash
        self.event_updated_at = event_updated_at
        self.event_created_at = event_created_at
        self.event_touched_at = event_touched_at
        self.event_id = event_id
        self.event_type = event_type
        self.event_description = event_description

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat_dict())

    def to_dict(self):
        ret = {}
        ret["event_title"] = self.event_title
        ret["event_type_id"] = self.event_type_id
        ret["event_happened_at"] = self.event_happened_at
        ret["event_hash"] = self.event_hash
        ret["event_updated_at"] = self.event_updated_at
        ret["event_created_at"] = self.event_created_at
        ret["event_touched_at"] = self.event_touched_at
        ret["event_id"] = self.event_id
        ret["event_type"] = self.event_type
        return ret

    def to_table(self):
        table = {
            "ID": self.event_id,
            "Title": self.event_title,
            "Description": self.event_description,
            "Created At": self.event_created_at,
            "Updated At": self.event_updated_at,
        }
        return table


class Comment:
    def __init__(
        self,
        raw_data,
        comment_value=None,
        source=None,
        created_at=None,
        updated_at=None,
    ):
        self.raw_data = raw_data
        self.comment_value = comment_value
        self.source = source
        self.created_at = created_at
        self.updated_at = updated_at

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat_dict())

    def to_dict(self):
        ret = {}
        ret["Comment"] = self.comment_value
        ret["Source"] = self.source
        ret["Created at"] = self.created_at
        ret["Updated at"] = self.updated_at
        return ret


class Attribute:
    def __init__(
        self, raw_data, value=None, name=None, created_at=None, updated_at=None
    ):
        self.raw_data = raw_data
        self.value = value
        self.name = name
        self.created_at = created_at
        self.updated_at = updated_at

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat_dict())

    def to_dict(self):
        ret = {}

        ret["Value"] = self.value
        ret["Name"] = self.name
        ret["Created at"] = self.created_at
        ret["Updated at"] = self.updated_at
        return ret


class Source:
    def __init__(
        self, raw_data, name=None, source_type=None, created_at=None, updated_at=None
    ):
        self.raw_data = raw_data
        self.name = name
        self.source_type = source_type
        self.created_at = created_at
        self.updated_at = updated_at

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat_dict())

    def to_dict(self):
        ret = {}

        ret["Type"] = self.source_type
        ret["Name"] = self.name
        ret["Created at"] = self.created_at
        ret["Updated at"] = self.updated_at
        return ret


class IndicatorDetails:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_json())

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat_dict())


class LinkedObject:
    def __init__(
        self,
        raw_data,
        id,
        title,
        name,
        value,
        description,
        created_at,
        updated_at,
        related_object_type,
    ):
        self.raw_data = raw_data
        self.id = id
        self.title = title
        self.name = name
        self.value = value
        self.description = description
        self.created_at = created_at
        self.updated_at = updated_at
        self.related_object_type = related_object_type

    def to_json(self):
        return self.raw_data

    def to_table(self):
        table = {
            "ID": self.id,
            "Description": self.description,
            "Created At": self.created_at,
            "Updated At": self.updated_at,
        }

        if self.related_object_type in ["events", "attachments"]:
            table["Title"] = self.title
        elif self.related_object_type in ["adversaries", "signatures", "tasks"]:
            table["Name"] = self.name
        else:
            table["Value"] = self.value

        return table

    def to_flat_dict(self):
        return dict_to_flat(self.to_json())

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat_dict())


class Adversary:
    def __init__(self, raw_data, name, updated_at, created_at, id):
        self.raw_data = raw_data
        self.name = name
        self.updated_at = updated_at
        self.created_at = created_at
        self.id = id

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_json())

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat_dict())


class UniversalObject:
    def __init__(
        self,
        raw_data,
        attribute_id=None,
        value=None,
        object_id=None,
        name=None,
        updated_at=None,
        created_at=None,
        attribute=None,
        sources=None,
    ):
        self.raw_data = raw_data
        self.attribute_id = attribute_id
        self.value = value
        self.object_id = object_id
        self.name = name
        self.updated_at = updated_at
        self.created_at = created_at
        self.attribute = attribute
        self.sources = sources or []

    def to_json(self):
        return self.raw_data


class MalwareDetails:
    def __init__(
        self, raw_data, id, status_id, type_id, description, created_at, updated_at
    ):
        self.raw_data = raw_data
        self.id = id
        self.status_id = status_id
        self.type_id = type_id
        self.description = description
        self.created_at = created_at
        self.updated_at = updated_at

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_json())

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat_dict())

    def to_enrichment(self):
        return {
            "id": self.id,
            "status_id": self.status_id,
            "type_id": self.type_id,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class DefaultObject:
    def __init__(
        self,
        raw_data,
        value=None,
        description=None,
        item_id=None,
        object_id=None,
        object_code=None,
        object_name=None,
        object_name_plural=None,
        updated_at=None,
        created_at=None,
    ):
        self.raw_data = raw_data
        self.value = value
        self.description = description
        self.item_id = item_id
        self.object_id = object_id
        self.updated_at = updated_at
        self.created_at = created_at
        self.object_code = object_code
        self.object_name = object_name
        self.object_name_plural = object_name_plural

    def to_json(self):
        return self.raw_data


class RelatedObject:
    def __init__(
        self,
        raw_data,
        type_id,
        value,
        object_id,
        status_id,
        description,
        title,
        name,
        started_at,
        ended_at,
        updated_at,
        created_at,
        touched_at,
        deleted_at,
        related_object_type,
    ):
        self.raw_data = raw_data
        self.type_id = type_id
        self.value = value
        self.object_id = object_id
        self.status_id = status_id
        self.description = description
        self.title = title
        self.name = name
        self.started_at = started_at
        self.ended_at = ended_at
        self.updated_at = updated_at
        self.created_at = created_at
        self.touched_at = touched_at
        self.deleted_at = deleted_at
        self.related_object_type = related_object_type

    def to_json(self):
        json_dict = self.raw_data.copy()
        del json_dict["pivot"]
        return json_dict

    def to_enrichment_data(self, index=None):
        enrichment_dict = {
            f"related_{self.related_object_type}_id_{index}": self.object_id
        }

        if self.related_object_type in ["events", "attachments"]:
            enrichment_dict[f"related_{self.related_object_type}_value_{index}"] = (
                self.title
            )
        elif self.related_object_type in ["adversaries", "signatures", "tasks"]:
            enrichment_dict[f"related_{self.related_object_type}_value_{index}"] = (
                self.name
            )
        else:
            enrichment_dict[f"related_{self.related_object_type}_value_{index}"] = (
                self.value
            )

        return enrichment_dict

    def to_flat_dict(self, index=None):
        return dict_to_flat(self.to_enrichment_data(index))

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat_dict())

    def to_table(self):
        table = {
            "ID": self.object_id,
            "Created At": self.created_at,
            "Updated At": self.updated_at,
        }

        if self.related_object_type != "adversaries":
            table["Description"] = self.description

        if self.related_object_type in ["events", "attachments"]:
            table["Title"] = self.title
        elif self.related_object_type in ["adversaries", "signatures", "tasks"]:
            table["Name"] = self.name
        else:
            table["Name"] = self.value

        return table
