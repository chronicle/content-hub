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
from .datamodels import Event


class CiscoAMPParser:
    """
    Cisco AMP Transformation Layer
    """

    @staticmethod
    def get_total_events(raw_data):
        return raw_data.get("metadata", {}).get("results", {}).get("total", 0)

    @staticmethod
    def get_prev_events_link(raw_data):
        return raw_data.get("metadata", {}).get("links", {}).get("prev")

    @staticmethod
    def build_event_obj(raw_data):
        return Event(
            raw_data=raw_data,
            severity=raw_data.get("severity"),
            event_id=raw_data.get("id"),
            event_type=raw_data.get("event_type"),
            start_date=raw_data.get("date"),
            timestamp=raw_data.get("timestamp"),
            timestamp_nanoseconds=raw_data.get("timestamp_nanoseconds"),
        )

    @staticmethod
    def build_event_obj_list(raw_data):
        return [
            CiscoAMPParser.build_event_obj(raw_event)
            for raw_event in raw_data.get("data", [])
        ]
