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
from typing import List, Any

from .datamodels import Incident, UpdateIncidentData, MarkIncidentData


class PhishrodParser:
    def get_results(self, raw_json: dict, builder_method: str) -> List[Any]:
        """
        Default method for building dataclass objects from raw data

        Args:
            raw_json: JSON received from API
            builder_method: Method which will be used to building objects

        Returns:
            List of filled objects
        """
        results = raw_json.get("incidents", [])
        return [getattr(self, builder_method)(result_item) for result_item in results]

    @staticmethod
    def build_incidents(raw_data: dict) -> Incident:
        """
        Builds Incident dataclass

        Args:
            raw_data: Raw API data item

        Returns:
            Filled Incident object
        """
        return Incident(
            raw_data=raw_data,
            email_subject=raw_data.get("emailSubject"),
            incident_number=raw_data.get("incidentNumber"),
            report_datetime=raw_data.get("reportedBy", {})[0].get("reportDateTime"),
        )

    def build_update_incident_obj(self, raw_data: dict) -> UpdateIncidentData:
        """
        Builds Update Incident object

        Args:
            raw_data: Raw API data item

        Returns:
            Filled Update Incident object
        """
        return UpdateIncidentData(
            raw_data=raw_data,
            status_marked=raw_data.get("statusMarked", False),
            message=raw_data.get("message", ""),
        )

    def build_mark_incident_obj(self, raw_data: dict) -> MarkIncidentData:
        """
        Builds Mark Incident object

        Args:
            raw_data: Raw API data item

        Returns:
            Filled Mark Incident object
        """
        return MarkIncidentData(
            raw_data=raw_data,
            status=raw_data.get("status", ""),
            code=raw_data.get("code", ""),
        )
