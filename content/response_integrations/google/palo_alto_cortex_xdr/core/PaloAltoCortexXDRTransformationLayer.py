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

from typing import TYPE_CHECKING

from ..core.datamodels import (
    AgentReport,
    Alert,
    DeviceViolation,
    Endpoint,
    Incident,
    XQLSearch,
    XQLSearchResult,
    FileRetrievalAction,
    FileRetrievalDetails,
)

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class PaloAltoCortexXDRTransformationLayer:
    """
    Palo Alto Cortex XDR Transformation Layer.
    Class for object building from raw_data with static methods build_siemplify_{object}_obj.
    """

    @staticmethod
    def build_siemplify_endpoint_obj(endpoint_data):
        return Endpoint(raw_data=endpoint_data, **endpoint_data)

    @staticmethod
    def build_siemplify_device_violation_obj(device_violation_data):
        return DeviceViolation(raw_data=device_violation_data, **device_violation_data)

    @staticmethod
    def build_siemplify_agent_report_obj(agent_report_data):
        return AgentReport(raw_data=agent_report_data, **agent_report_data)

    @staticmethod
    def build_siemplify_xql_search_obj(xql_search_data: SingleJson) -> XQLSearch:
        return XQLSearch.from_json(raw_data=xql_search_data)

    @staticmethod
    def build_siemplify_xql_result_obj(
        xql_search_result_data: SingleJson,
    ) -> XQLSearchResult:
        return XQLSearchResult.from_json(raw_data=xql_search_result_data["reply"])

    @staticmethod
    def build_siemplify_incident_details_obj(
        incident_details_data: SingleJson,
    ) -> Incident:
        """Get Incident Details.


        Args:
            incident_details_data (SingleJson): Incident details data.

        Returns:
            Incident: Incident object.
        """
        incident_data: SingleJson = incident_details_data["reply"]
        if not incident_data["incident"]:
            return None

        return Incident.from_json(incident_data=incident_data)

    @staticmethod
    def build_siemplify_alert_detail_objs(
        alerts_details_data: SingleJson,
    ) -> list[Alert]:
        return [
            Alert.from_json(alert_data=alert_details_data)
            for alert_details_data in alerts_details_data["reply"]["alerts"]["data"]
        ]

    @staticmethod
    def build_siemplify_file_retrieval_action_obj(
        file_retrieval_data: SingleJson,
    ) -> FileRetrievalAction:
        return FileRetrievalAction.from_json(raw_data=file_retrieval_data['reply'])

    @staticmethod
    def build_siemplify_file_retrieval_details_obj(
        file_retrieval_details_data: SingleJson,
    ) -> FileRetrievalDetails:
        return FileRetrievalDetails.from_json(raw_data=file_retrieval_details_data['reply'])
