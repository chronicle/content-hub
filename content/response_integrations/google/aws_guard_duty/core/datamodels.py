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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from TIPCommon.transformation import dict_to_flat

if TYPE_CHECKING:
    from EnvironmentCommon import EnvironmentHandle

from . import consts

LOW_SEVERITY_THRESHOLD = 4.0
MEDIUM_SEVERITY_THRESHOLD = 7.0
HIGH_SEVERITY_THRESHOLD = 9.0
CRITICAL_SEVERITY_THRESHOLD = 10.0

FILE_FORMATS = {
    "Plaintext": "TXT",
    "Structured Threat Information Expression (STIX)": "STIX",
    "Open Threat Exchange (OTX)™ CSV": "OTX_CSV",
    "FireEye™ iSIGHT Threat Intelligence CSV": "FIRE_EYE",
    "Proofpoint™ ET Intelligence Feed CSV": "PROOF_POINT",
    "AlienVault™ Reputation Feed": "ALIEN_VAULT",
}


SEVERITIES = {
    "INFORMATIONAL": -1,
    "LOW": 40,
    "MEDIUM": 60,
    "HIGH": 80,
    "CRITICAL": 100,
}


class Finding:
    """Finding data model."""

    def __init__(self, raw_data: dict[str, Any], detector_id: str) -> None:
        """Initialize finding data model.

        Args:
            raw_data: Raw JSON response of finding.
            detector_id: Detector ID.

        """
        self.raw_data = raw_data
        self.detector_id = detector_id
        self.id = raw_data.get("Id")
        self.created_time = raw_data.get("CreatedAt")
        self.updated_time = raw_data.get("UpdatedAt")
        self.description = raw_data.get("Description")
        self.type = raw_data.get("Type")
        self.account_id = raw_data.get("AccountId")
        self.resource_id = raw_data.get("Resource", {}).get("InstanceDetails", {}).get("InstanceId")
        self.arn = raw_data.get("Arn")
        self.title = raw_data.get("Title")
        self.severity = raw_data.get("Severity")
        self.confidence = raw_data.get("Confidence")
        self.count = raw_data.get("Service", {}).get("Count")

        try:
            self.created_time_ms = convert_string_to_unix_time(self.created_time)
        except (ValueError, TypeError):
            self.created_time_ms = 1

        try:
            self.updated_time_ms = convert_string_to_unix_time(self.updated_time)
        except (ValueError, TypeError):
            self.updated_time_ms = 1

    def as_json(self) -> dict[str, Any]:
        """Convert finding to JSON dictionary.

        Returns:
            The raw JSON data.

        """
        return self.raw_data

    def as_event(self) -> dict[str, Any]:
        """Convert finding to event dictionary.

        Returns:
            The flattened event data.

        """
        event_data = self.raw_data.copy()
        event_data["detector_id_configured_in_connector_settings"] = self.detector_id
        return dict_to_flat(event_data)

    def as_csv(self) -> dict[str, Any]:
        """Convert finding to CSV representation.

        Returns:
            The CSV dictionary.

        """
        return {
            "Finding ID": self.id,
            "Title": self.title,
            "Description": self.description,
            "Type": self.type,
            "Severity": self.severity,
            "Count": self.count,
            "Resource ID": self.resource_id,
            "Created at": self.created_time,
            "Updated at": self.updated_time,
            "Account ID": self.account_id,
        }

    @property
    def siemplify_severity(self) -> int:
        """Map AWS severity value to Siemplify severity priority.

        Returns:
            Siemplify severity level.

        """
        if self.severity is None:
            return SEVERITIES["INFORMATIONAL"]

        if self.severity < LOW_SEVERITY_THRESHOLD:
            return SEVERITIES["LOW"]

        if self.severity < MEDIUM_SEVERITY_THRESHOLD:
            return SEVERITIES["MEDIUM"]

        if self.severity < HIGH_SEVERITY_THRESHOLD:
            return SEVERITIES["HIGH"]

        if self.severity <= CRITICAL_SEVERITY_THRESHOLD:
            return SEVERITIES["CRITICAL"]

        return SEVERITIES["INFORMATIONAL"]

    def as_alert_info(self, environment_common: EnvironmentHandle) -> AlertInfo:
        """Create an AlertInfo out of the current finding.

        Args:
            environment_common: The environment common object for fetching the
                environment.

        Returns:
            The created AlertInfo object.

        """
        alert_info = AlertInfo()
        alert_info.environment = environment_common.get_environment(self.as_event())
        alert_info.ticket_id = self.id
        alert_info.display_id = str(uuid.uuid4())
        alert_info.name = self.title
        alert_info.description = self.description
        alert_info.device_vendor = consts.VENDOR
        alert_info.device_product = consts.PRODUCT
        alert_info.priority = self.siemplify_severity
        alert_info.rule_generator = self.type
        alert_info.start_time = self.created_time_ms
        alert_info.end_time = self.updated_time_ms
        alert_info.events = [self.as_event()]
        return alert_info


class IpSet:
    """IP Set data model."""

    def __init__(self, raw_data: dict[str, Any], ip_set_id: str | None = None) -> None:
        """Initialize IP set.

        Args:
            raw_data: Raw JSON response.
            ip_set_id: IP Set ID.

        """
        self.raw_data = raw_data
        self.id = ip_set_id
        self.name = raw_data.get("Name")
        self.format = raw_data.get("Format")
        self.location = raw_data.get("Location")
        self.status = raw_data.get("Status")
        self.tags = raw_data.get("Tags", [])

    def as_json(self) -> dict[str, Any]:
        """Convert IP Set to JSON.

        Returns:
            The JSON representation.

        """
        return {
            "Format": self.format,
            "Name": self.name,
            "Location": self.location,
            "Status": self.status,
        }

    def as_csv(self) -> dict[str, Any]:
        """Convert IP Set to CSV.

        Returns:
            The CSV representation.

        """
        return {
            "Name": self.name,
            "Trusted IP List ID": self.id,
            "Location": self.location,
            "Status": self.status,
        }


class TISet:
    """Threat Intelligence Set data model."""

    def __init__(self, raw_data: dict[str, Any], ti_set_id: str | None = None) -> None:
        """Initialize Threat Intel Set.

        Args:
            raw_data: Raw JSON response.
            ti_set_id: Threat Intel Set ID.

        """
        self.raw_data = raw_data
        self.id = ti_set_id
        self.name = raw_data.get("Name")
        self.format = raw_data.get("Format")
        self.location = raw_data.get("Location")
        self.status = raw_data.get("Status")
        self.tags = raw_data.get("Tags", [])

    def as_json(self) -> dict[str, Any]:
        """Convert Threat Intel Set to JSON.

        Returns:
            The JSON representation.

        """
        return {
            "Format": self.format,
            "Name": self.name,
            "Location": self.location,
            "Status": self.status,
        }

    def as_csv(self) -> dict[str, Any]:
        """Convert Threat Intel Set to CSV.

        Returns:
            The CSV representation.

        """
        return {
            "Name": self.name,
            "ID": self.id,
            "Location": self.location,
            "Status": self.status,
        }


class Detector:
    """Detector data model."""

    def __init__(self, raw_data: dict[str, Any], detector_id: str | None = None) -> None:
        """Initialize Detector.

        Args:
            raw_data: Raw JSON response.
            detector_id: Detector ID.

        """
        self.raw_data = raw_data
        self.id = detector_id
        self.created_at = raw_data.get("CreatedAt")
        self.updated_at = raw_data.get("UpdatedAt")
        self.service_role = raw_data.get("ServiceRole")
        self.status = raw_data.get("Status")
        self.finding_publishing_frequency = raw_data.get("FindingPublishingFrequency")
        self.tags = raw_data.get("Tags", [])

    def to_csv(self) -> dict[str, Any]:
        """Convert detector details to CSV format.

        Returns:
            The CSV dictionary.

        """
        return {
            "Detector ID": self.id,
            "Status": self.status,
            "Service Role": self.service_role,
            "Created at": self.created_at,
            "Updated at": self.updated_at,
        }

    def to_json(self) -> dict[str, Any]:
        """Convert detector details to JSON format.

        Returns:
            The JSON representation.

        """
        return {
            "DetectorId": self.id,
            "CreatedAt": self.created_at,
            "ServiceRole": self.service_role,
            "Status": self.status,
            "UpdatedAt": self.updated_at,
        }

    def to_table(self) -> list[dict[str, Any]]:
        """Prepare the detector's data to be used on the table.

        Returns:
            List containing dict of detector's data.

        """
        return [self.to_csv()]


@dataclass
class FindingsQuery:
    """AWS GuardDuty findings query parameters dataclass.

    Attributes:
        detector_id: The unique ID of the detector.
        min_severity: Lowest severity that will be used to fetch findings.
        updated_at: Search for findings updated after this time (epoch ms).
        page_size: Page size to return.
        search_after_token: Token from where to start fetching next page.
        asc: If True, findings are returned in ascending order.
        sort_by: Field name to sort the results by.

    """

    detector_id: str
    min_severity: float | None = None
    updated_at: int | None = None
    page_size: int = consts.PAGE_SIZE
    search_after_token: str | None = None
    asc: bool = True
    sort_by: str = "updatedAt"
