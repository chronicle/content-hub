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

import pathlib
import abc
from typing import MutableMapping, Any
from TIPCommon.types import SingleJson
from TIPCommon.data_models import CaseDetails

from ...core.datamodels import (
    Incident,
    IncidentInfo,
    IncidentExtraData,
)
from ...tests.common import IncidentIdNotFoundError


class PaloAltoCortexXDR(abc.ABC):
    def __init__(self) -> None:
        self._incidents: MutableMapping[str, SingleJson] = {}
        self._endpoints: MutableMapping[str, SingleJson] = {}
        self._scan_statuses: MutableMapping[str, Any] = {}
        self._connector_incidents: list[IncidentInfo] | None = None
        self._connector_incident_extra_data: IncidentExtraData | None = None

    def add_incident(self, incident: Incident) -> None:
        self._incidents[incident.incident_id] = incident

    def get_incident(self, incident_id: int) -> SingleJson:
        """Get incident by ID.

        Args:
            incident_id (int): Incident ID.
        Raises:
            IncidentIdNotFoundError: If incident ID is not found.
        Returns:
            SingleJson: Incident data.
        """
        if incident_id not in self._incidents:
            raise IncidentIdNotFoundError(
                f"Mock Error: Invalid incident ID {incident_id}"
            )

        return self._incidents[incident_id]

    def cleanup_incidents(self) -> MutableMapping[str, SingleJson]:
        self._incidents = {}

    def add_endpoint(self, endpoint_data: SingleJson) -> None:
        self._endpoints[endpoint_data["agent_id"]] = endpoint_data

    def get_endpoint_by_ip(self, ip: str) -> SingleJson | None:
        """
        Get endpoint by IP address.

        Args:
            ip (str): The IP address of the endpoint.

        Returns:
            SingleJson | None: The endpoint data if found, otherwise None.
        """
        for endpoint in self._endpoints.values():
            if ip in endpoint.get("ip", []):
                return endpoint

        return None

    def get_endpoint_by_hostname(self, hostname: str) -> SingleJson | None:
        """
        Get endpoint by hostname.

        Args:
            hostname (str): The hostname of the endpoint.

        Returns:
            SingleJson | None: The endpoint data if found, otherwise None.
        """
        for endpoint in self._endpoints.values():
            if endpoint.get("host_name") == hostname:
                return endpoint

        return None

    def add_scan(self, endpoint_ids: list[str]) -> str:
        """
        Simulates starting a scan on a list of endpoints.

        Args:
            endpoint_ids: A list of endpoint IDs to scan.

        Returns:
            The action ID of the scan.
        """
        action_id = "123456789"
        scan_status_data = {"data": {}}
        for endpoint_id in endpoint_ids:
            scan_status_data["data"][endpoint_id] = "PENDING"

        self._scan_statuses[action_id] = scan_status_data
        return action_id

    def add_case_overview_details(self, case_details: list[CaseDetails]) -> None:
        """
        Adds a list of case overview details to the mock product.
        Args:
            case_details: A list of case detail objects.
        """
        self._case_overview_details = case_details

    def get_case_overview_details(self, case_id: str) -> CaseDetails | None:
        """
        Gets case overview details for a given case ID by searching the stored list.

        Args:
            case_id: The ID of the case to retrieve.

        Returns:
            The case detail object if found, otherwise None.
        """
        if not self._case_overview_details:
            return None

        for detail in self._case_overview_details:
            if str(detail.identifier) == case_id:
                return detail
        return None

    def get_scan_status(self, action_id: str) -> Any:
        return self._scan_statuses.get(action_id)

    def add_incidents(self, incidents: list[IncidentInfo]) -> None:
        self._connector_incidents = incidents

    def get_incidents(self) -> list[IncidentInfo]:
        return self._connector_incidents

    def add_incident_extra_data(self, incident_extra_data: IncidentExtraData) -> None:
        self._connector_incident_extra_data = incident_extra_data

    def get_incident_extra_data(self) -> IncidentExtraData:
        return self._connector_incident_extra_data
