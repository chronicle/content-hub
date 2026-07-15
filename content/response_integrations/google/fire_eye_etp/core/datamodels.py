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

"""Datamodels for FireEye ETP integration."""

from __future__ import annotations

import copy
from typing import Any

from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time

from .fire_eye_etp_constants import ALERT_NAME
from .utils_manager import naive_time_converted_to_aware


class BaseModel:
    """Base model for inheritance."""

    def __init__(self, raw_data: dict[str, Any]) -> None:
        """Initialize the BaseModel.

        Args:
            raw_data: The raw JSON data.

        """
        self.raw_data = raw_data

    def to_json(self) -> dict[str, Any]:
        """Convert the model to JSON.

        Returns:
            The raw JSON data.

        """
        return self.raw_data


class Alert(BaseModel):
    """Represent a FireEye ETP Alert."""

    def __init__(
        self,
        raw_data: dict[str, Any],
        timezone_offset: str | None = None,
    ) -> None:
        """Initialize the Alert.

        Args:
            raw_data: The raw JSON data.
            timezone_offset: The timezone offset.

        """
        super().__init__(raw_data)
        self.id: str | None = raw_data.get("id")
        self.timestamp: str | None = (
            raw_data.get("attributes", {}).get("email", {}).get("timestamp", {}).get("accepted")
        )
        self.severity: str | None = raw_data.get("attributes", {}).get("alert", {}).get("severity")
        self.etp_message_id: str | None = raw_data.get("attributes", {}).get("email", {}).get("etp_message_id")
        self.malwares: list[dict[str, Any]] = (
            raw_data
            .get("attributes", {})
            .get("alert", {})
            .get("explanation", {})
            .get("malware_detected", {})
            .get("malware", [])
        )
        self.recipients: list[str] = (
            raw_data.get("attributes", {}).get("email", {}).get("smtp", {}).get("rcpt_to", "").split()
        )
        self.name: str = ALERT_NAME
        self.timezone_offset: str | None = timezone_offset

    @property
    def priority(self) -> int:
        """The priority of the alert.

        Returns:
            The priority value (60, 80, or 100).

        """
        if self.severity == "majr":
            return 80
        if self.severity == "crit":
            return 100

        return 60

    @property
    def events(self) -> list[dict[str, Any]]:
        """The events from the alert.

        Returns:
            The list of events.

        """
        events: list[dict[str, Any]] = []

        for malware in self.malwares:
            alert = copy.deepcopy(self.raw_data)
            alert.get("attributes", {}).get("alert", {}).get("explanation", {}).pop("os_changes", None)
            alert.get("attributes", {}).get("alert", {}).get("explanation", {}).get("malware_detected", {}).pop(
                "malware", None
            )
            malware["alert"] = alert
            events.append(malware)

        return events

    @property
    def recipient_events(self) -> list[dict[str, Any]]:
        """The recipient events from the alert.

        Returns:
            The list of recipient events.

        """
        events: list[dict[str, Any]] = []

        for recipient in self.recipients:
            event = {
                "event_name": "FireEye ETP Recipient",
                "description": ("This is a custom Siemplify Event created for mapping of the recipients"),
                "recipient": recipient,
            }
            events.append(event)

        return events

    @property
    def occurred_time_unix(self) -> int:
        """The occurred time of the alert in Unix time.

        Returns:
            The occurred time in Unix time.

        """
        return convert_datetime_to_unix_time(naive_time_converted_to_aware(self.timestamp, self.timezone_offset))
