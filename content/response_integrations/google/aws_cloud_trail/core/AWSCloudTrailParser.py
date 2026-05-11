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

from .datamodels import InsightEvent


class AWSCloudTrailParser:
    """
    AWS Cloud Trail Transformation Layer.
    """

    @staticmethod
    def build_insight_event_obj(raw_data):
        try:
            cloud_trail_event = json.loads(raw_data.get("CloudTrailEvent"))
        except:
            cloud_trail_event = raw_data.get("CloudTrailEvent")

        return InsightEvent(
            raw_data=raw_data,
            event_id=raw_data.get("EventId"),
            event_name=raw_data.get("EventName"),
            event_time=raw_data.get("EventTime"),
            event_source=raw_data.get("EventSource"),
            username=raw_data.get("Username"),
            cloud_trail_event=cloud_trail_event,
        )
