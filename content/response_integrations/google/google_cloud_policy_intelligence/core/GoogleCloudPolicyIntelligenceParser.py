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

from TIPCommon.types import SingleJson

from .datamodels import Activity


def build_activity_objects(raw_json: SingleJson) -> list[Activity]:
    """Builds multiple activity objects

    Args:
        raw_json: Raw json from the response having information
        for multiple activities

    Returns:
        A list of activity objects
    """
    activities = raw_json.get("activities", [])
    return [build_activity_object(activity) for activity in activities]


def build_activity_object(raw_data: SingleJson) -> Activity:
    """Builds a single activity object

    Args:
        raw_data: A dict object for a single activity
    Returns:
        Activity object
    """
    return Activity(raw_data=raw_data, resource_name=raw_data["fullResourceName"])
