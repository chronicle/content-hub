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
from microsoft_graph_security.core.datamodels import Alert, Incident
from TIPCommon.types import SingleJson


class MicrosoftGraphSecurityParser:
    """
    Microsoft Graph Security Transformation Layer.
    """

    @staticmethod
    def build_siemplify_alert_obj(alert_data):
        return Alert(
            raw_data=alert_data,
            vendor=alert_data.get("vendorInformation", {}).get("vendor"),
            provider=alert_data.get("vendorInformation", {}).get("provider"),
            **alert_data
        )

    @staticmethod
    def build_siemplify_incident_obj(incident_data: SingleJson) -> Incident:
        """Build incident object.

        Args:
            incident_data (SingleJson): Incident data from MsGraph Security API.

        Returns:
            Incident: Incident object.
        """
        return Incident.from_json(incident_data=incident_data)
