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

from copy import deepcopy
import dataclasses
from enum import Enum
from typing import Any

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from EnvironmentCommon import EnvironmentHandle
from TIPCommon.transformation import dict_to_flat
from TIPCommon.types import SingleJson
from . import constants


class PrismaCloudPriorityEnum(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MED = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class SiemplifyPriorityEnum(Enum):
    CRITICAL = 100
    HIGH = 80
    MED = 60
    LOW = 40
    INFORMATIONAL = 20


# Priorities Map.
PRIORITIES_MAP = {
    PrismaCloudPriorityEnum.CRITICAL: SiemplifyPriorityEnum.CRITICAL,
    PrismaCloudPriorityEnum.HIGH: SiemplifyPriorityEnum.HIGH,
    PrismaCloudPriorityEnum.MED: SiemplifyPriorityEnum.MED,
    PrismaCloudPriorityEnum.LOW: SiemplifyPriorityEnum.LOW,
    PrismaCloudPriorityEnum.INFORMATIONAL: SiemplifyPriorityEnum.INFORMATIONAL,
}


def calculate_priority(severity) -> int:
    """Calculate the Siemplify alarm priority based on the severity value.

    Args:
        severity (str): The severity value as received from Prisma cloud.

    Returns:
        int: The calculated Siemplify alarm priority
    """
    for priority, siemplify_priority in PRIORITIES_MAP.items():
        if severity == priority.value:
            return siemplify_priority.value

    return SiemplifyPriorityEnum.INFORMATIONAL.value


@dataclasses.dataclass(frozen=True)
class BaseModel:
    raw_data: SingleJson

    def to_json(self) -> SingleJson:
        return dataclasses.asdict(self)

    def to_flat(self) -> dict[str, Any]:
        return dict_to_flat(self.to_json()["raw_data"])


@dataclasses.dataclass(frozen=True)
class AlertResponse(BaseModel):
    """Class to create data model for Alert Response"""

    alert_id: str
    name: str
    events = []
    alert_time: str

    @classmethod
    def from_json(cls, alert_json: SingleJson) -> AlertResponse:
        """Create an AlertResponse object from a JSON representation.

        Args:
            alert_json (SingleJson): The JSON representation of the alert.

        Returns:
            AlertResponse: The created AlertResponse object.
        """
        return cls(
            raw_data=alert_json,
            alert_id=alert_json["id"],
            name=alert_json["policy"]["name"],
            alert_time=alert_json["alertTime"],
        )

    def get_alert_info(
        self, alert_info: AlertInfo, environment_common: EnvironmentHandle
    ) -> AlertInfo:
        """Get alert information.

        Args:
            alert_info (AlertInfo): The alert information.
            environment_common (EnvironmentHandle): The environment handle.

        Returns:
            AlertInfo: The updated alert information.
        """
        alert_id = self.raw_data["id"]
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.raw_data)
        )
        alert_info.ticket_id = alert_id
        alert_info.alert_id = alert_id
        alert_info.display_id = f"Palo_Alto_Prisma_Cloud_{alert_id}"
        alert_info.name = self.raw_data["policy"]["name"]
        alert_info.reason = self.raw_data["reason"]
        alert_info.description = self.raw_data["policy"]["description"]
        alert_info.device_vendor = constants.DEVICE_VENDOR
        alert_info.device_product = constants.DEVICE_PRODUCT
        alert_info.priority = calculate_priority(self.raw_data["policy"]["severity"])
        alert_info.rule_generator = self.raw_data["policy"]["name"]
        alert_info.source_grouping_identifier = (
            self.raw_data["saveSearchId"]
            if self.raw_data["policy"]["policyType"] == "attack_path"
            else self.raw_data["policy"]["name"]
        )
        alert_info.start_time = self.raw_data["alertTime"]
        alert_info.end_time = self.raw_data["alertTime"]
        alert_info.events = self.to_events(self.raw_data)

        return alert_info

    def set_events(self) -> None:
        """Set alert events

        Returns: (): None
        """
        self.events.append(deepcopy(self.raw_data))

    @staticmethod
    def to_events(alert_json: SingleJson) -> list[SingleJson]:
        """
        Convert alert events to siemplify events
        Args:
            alert_json (SingleJson): alert data in JSON format

        Returns:
           list[SingleJson]: list of flat events
        """
        if "complianceMetadata" in alert_json["policy"]:
            del alert_json["policy"]["complianceMetadata"]
        if "history" in alert_json:
            del alert_json["history"]
        if "metadata" in alert_json:
            del alert_json["metadata"]
        alert_json[alert_json["resource"]["resourceType"]] = alert_json["resource"][
            "name"
        ]
        events = [deepcopy(alert_json)]
        return [dict_to_flat(event) for event in events]


@dataclasses.dataclass(frozen=True)
class Asset(BaseModel):
    """Class for alert api response."""

    raw_data: SingleJson
    id: str
    name: str

    @classmethod
    def from_json(cls, asset_json: SingleJson) -> Asset:
        """Create an Asset object from a JSON representation.

        Args:
            asset_json (SingleJson): The JSON representation of the asset.

        Returns:
            Asset: The created Asset object.
        """
        return cls(raw_data=asset_json, id=asset_json["id"], name=asset_json["name"])


@dataclasses.dataclass(frozen=True)
class Alert(BaseModel):
    """Class for alert api response."""

    raw_data: SingleJson

    @classmethod
    def from_json(cls, alert_json: SingleJson) -> Alert:
        """Create an alert object from a JSON representation.

        Args:
            alert_json (SingleJson): The JSON representation of the alert.

        Returns:
            Alert: The created alert object.
        """
        return cls(raw_data=alert_json)
