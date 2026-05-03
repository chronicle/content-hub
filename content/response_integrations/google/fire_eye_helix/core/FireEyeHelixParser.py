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
from .datamodels import *


class FireEyeHelixParser:
    def build_first_alert(self, raw_data):
        alerts = raw_data.get("alerts", [])
        if alerts:
            raw_json = alerts[0]
            return self.build_alert_object(raw_json)

    def build_alert_object(self, alert_json, timezone_offset=None):
        return Alert(
            raw_data=alert_json,
            message=alert_json.get("message"),
            risk=alert_json.get("risk"),
            description=alert_json.get("description"),
            type_name=(
                alert_json.get("alert_type", {}).get("name")
                if alert_json.get("alert_type")
                else alert_json.get("message")
            ),
            created_at=alert_json.get("created_at"),
            first_event_at=alert_json.get("first_event_at"),
            last_event_at=alert_json.get("last_event_at"),
            source_url=alert_json.get("source_url"),
            id=alert_json.get("id"),
            timezone_offset=timezone_offset,
            notes=[
                self.build_note_object(note_json=note_json)
                for note_json in alert_json.get("notes", [])
            ],
        )

    def build_note_object(self, note_json):
        return Note(
            raw_data=note_json,
            note=note_json.get("note"),
            author=note_json.get("_author", {}).get("name"),
            created_at=note_json.get("createDate"),
        )

    def build_event_object(self, event_json, timezone_offset):
        return Event(raw_data=event_json, timezone_offset=timezone_offset)

    def get_lists(self, raw_json):
        results = raw_json.get("results", [])

        return [
            List(
                raw_data=result,
                id=result.get("id"),
                name=result.get("name"),
                short_name=result.get("short_name"),
                created_at=result.get("created_at"),
                item_count=result.get("item_count"),
                is_internal=result.get("is_internal"),
                is_active=result.get("is_active"),
                is_protected=result.get("is_protected"),
            )
            for result in results
        ]

    def get_items(self, raw_json):
        return [self.get_item(result) for result in raw_json.get("results", [])]

    def get_item(self, raw_json):
        return Item(
            raw_data=raw_json,
            id=raw_json.get("id"),
            value=raw_json.get("value"),
            type=raw_json.get("type"),
            risk=raw_json.get("risk"),
            notes=raw_json.get("notes"),
            list=raw_json.get("list"),
        )

    def get_index_search_result(self, raw_json):
        return IndexSearchResult(raw_data=raw_json.get("results", {}))

    def get_job_id(self, raw_json):
        data = raw_json.get("data", [])

        if len(data):
            return data[0].get("id")

    def get_job_state(self, raw_json):
        data = raw_json.get("data", [])

        if len(data):
            return data[0].get("state")

    def get_archive_search_result(self, raw_json):
        return ArchiveSearchResult(raw_data=raw_json.get("results", {}))

    def build_asset_object(self, raw_data):
        results = raw_data.get("results", [])
        if results:
            raw_json = results[0]
            return Asset(
                raw_data=raw_json,
                risk_score=raw_json.get("risk_score"),
                last_event_at=raw_json.get("last_event_at"),
                severity=raw_json.get("severity"),
                asset_status=raw_json.get("asset_status"),
                source=raw_json.get("source"),
                events_count=raw_json.get("events_count"),
                is_vip_asset=raw_json.get("is_vip_asset"),
                asset_type=raw_json.get("asset_type"),
                asset_name=raw_json.get("asset_name"),
                detections=raw_json.get("detections"),
                asset_uuid=raw_json.get("asset_uuid"),
                asset_department=raw_json.get("asset_department"),
                id=raw_json.get("id"),
                os=raw_json.get("properties", {}).get("os"),
            )
