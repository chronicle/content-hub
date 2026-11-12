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
import json
import xmltodict
from .datamodels import *


class TrendMicroDDANParser:
    @staticmethod
    def convert_xml_to_json(xml_string):
        """
        Convert xml string to dict
        Args:
            xml_string (str): string to convert
        Returns:
            (dict) converted dict
        """
        return json.loads(json.dumps(xmltodict.parse(xml_string, xml_attribs=False)))

    def build_event_log_objects(self, raw_data):
        items = raw_data.get("Return", {}).get("EventLogs", {}).get("EventLog", [])
        return [
            self.build_event_log_object(item)
            for item in (items if isinstance(items, list) else [items])
        ]

    @staticmethod
    def build_event_log_object(raw_data):
        return EventLog(raw_data=raw_data)

    @staticmethod
    def build_report_object(raw_data):
        return Report(raw_data=raw_data)

    def build_suspicious_object_objects(self, raw_data):
        items = raw_data.get("Return", {}).get("REPORTS", {}).get("REPORT", [])
        return [
            self.build_suspicious_object_object(item)
            for item in (items if isinstance(items, list) else [items])
        ]

    @staticmethod
    def build_suspicious_object_object(raw_data):
        return SuspiciousObject(raw_data=raw_data)
