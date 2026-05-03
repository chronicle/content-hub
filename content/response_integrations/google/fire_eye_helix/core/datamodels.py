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
import uuid
from TIPCommon import dict_to_flat, add_prefix_to_dict, flat_dict_to_csv
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from .UtilsManager import naive_time_converted_to_aware

from .FireEyeHelixConstants import (
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    FIREEYE_HELIX_TO_SIEM_SEVERITY,
)


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class List(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        name,
        short_name,
        created_at,
        item_count,
        is_internal,
        is_active,
        is_protected,
    ):
        super(List, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.short_name = short_name
        self.created_at = created_at
        self.item_count = item_count
        self.is_internal = is_internal
        self.is_active = is_active
        self.is_protected = is_protected

    def to_csv(self):
        return {
            "Name": self.name,
            "Short Name": self.short_name,
            "Created At": self.created_at,
            "Item Count": self.item_count,
            "Internal ": self.is_internal,
            "Active": self.is_active,
            "Protected": self.is_protected,
        }


class Item(BaseModel):
    def __init__(self, raw_data, id, value, type, risk, notes, list):
        super(Item, self).__init__(raw_data)
        self.id = id
        self.value = value
        self.type = type
        self.risk = risk
        self.notes = notes
        self.list = list

    def to_csv(self):
        return {
            "Value": self.value,
            "Type": self.type,
            "Risk": self.risk,
            "Notes": self.notes,
            "List ": self.list,
        }


class Alert(BaseModel):
    def __init__(
        self,
        raw_data,
        message,
        risk,
        description,
        type_name,
        created_at,
        first_event_at,
        last_event_at,
        source_url,
        id,
        timezone_offset,
        notes,
    ):
        super(Alert, self).__init__(raw_data)
        self.message = message
        self.risk = risk
        self.description = description
        self.type_name = type_name
        self.created_at = created_at
        self.first_event_at = first_event_at
        self.last_event_at = last_event_at
        self.source_url = source_url
        self.id = id
        self.timezone_offset = timezone_offset
        self.notes = notes

    @property
    def priority(self):
        """
        Converts API severity format to SIEM priority
        @return: SIEM priority
        """
        return FIREEYE_HELIX_TO_SIEM_SEVERITY.get(self.risk, -1)

    def to_alert_info(self, environment, alert_events):
        # type: (EnvironmentHandle) -> AlertInfo
        """
        Creates Siemplify Alert Info based on Indicator information
        @param environment: EnvironmentHandle object
        @param alert_events: Alert events
        @return: Alert Info object
        """
        alert_info = AlertInfo()
        alert_info.ticket_id = self.id
        alert_info.display_id = str(uuid.uuid4())
        alert_info.name = self.message
        alert_info.description = self.description
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = DEVICE_PRODUCT
        alert_info.priority = self.priority
        alert_info.rule_generator = self.type_name
        alert_info.start_time = convert_datetime_to_unix_time(
            naive_time_converted_to_aware(self.first_event_at, self.timezone_offset)
        )
        alert_info.end_time = convert_datetime_to_unix_time(
            naive_time_converted_to_aware(self.last_event_at, self.timezone_offset)
        )
        alert_info.events = (
            [dict_to_flat(event.raw_data) for event in self.create_events(alert_events)]
            if alert_events
            else [self.to_event()]
        )
        alert_info.environment = self.get_environment(environment, alert_info.events)
        alert_info.extensions = dict_to_flat({"source_url": self.source_url})

        return alert_info

    def create_events(self, alert_events):
        cleaned_events = []
        for event in alert_events:
            unique_keys = []
            duplicate_keys = []
            for k in event.raw_data.keys():
                if k.lower() in unique_keys:
                    duplicate_keys.append(k)
                else:
                    unique_keys.append(k.lower())
            for duplicate in duplicate_keys:
                event.raw_data.pop(duplicate, None)
            cleaned_events.append(event)
        return cleaned_events

    def to_event(self):
        return dict_to_flat(self.raw_data)

    def get_environment(self, environment, events):
        environment_from_alert = environment.get_environment(self.raw_data)

        if environment_from_alert != environment.default_environment:
            return environment_from_alert

        for event in events:
            environment_from_event = environment.get_environment(event)

            if environment_from_event != environment.default_environment:
                return environment_from_event

        return environment.default_environment


class Event(BaseModel):
    def __init__(self, raw_data, timezone_offset):
        super(Event, self).__init__(raw_data)
        self.timezone_offset = timezone_offset


class IndexSearchResult(BaseModel):
    def __init__(self, raw_data):
        super(IndexSearchResult, self).__init__(raw_data)

    def contains_results(self):
        return self.raw_data.get("hits", {}).get("total")


class ArchiveSearchResult(BaseModel):
    def __init__(self, raw_data):
        super(ArchiveSearchResult, self).__init__(raw_data)

    def contains_results(self):
        return self.raw_data.get("results", {}).get("hits", {}).get("total")


class Note(BaseModel):
    def __init__(self, raw_data, note, author, created_at):
        super(Note, self).__init__(raw_data)
        self.note = note
        self.author = author
        self.created_at = created_at

    def to_csv(self):
        return {"Note": self.note, "Author": self.author, "Created At": self.created_at}


class Asset(BaseModel):
    def __init__(
        self,
        raw_data,
        risk_score,
        last_event_at,
        severity,
        asset_status,
        source,
        events_count,
        is_vip_asset,
        asset_type,
        asset_name,
        detections,
        asset_uuid,
        asset_department,
        id,
        os,
    ):
        super(Asset, self).__init__(raw_data)
        self.risk_score = risk_score
        self.last_event_at = last_event_at
        self.severity = severity
        self.asset_status = asset_status
        self.source = source
        self.events_count = events_count
        self.is_vip_asset = is_vip_asset
        self.asset_type = asset_type
        self.asset_name = asset_name
        self.detections = detections
        self.asset_uuid = asset_uuid
        self.asset_department = asset_department
        self.id = id
        self.os = os

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.create_enrichment_dict())
        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_csv(self):
        return flat_dict_to_csv(self.create_enrichment_dict())

    def create_enrichment_dict(self):
        return {
            "risk_score": self.risk_score,
            "last_event_at": self.last_event_at,
            "severity": self.severity,
            "asset_status": self.asset_status,
            "source": self.source,
            "events_count": self.events_count,
            "is_vip_asset": self.is_vip_asset,
            "asset_type": self.asset_type,
            "asset_name": self.asset_name,
            "detections": self.detections,
            "asset_uuid": self.asset_uuid,
            "asset_department": self.asset_department,
            "id": self.id,
            "os": self.os,
        }
