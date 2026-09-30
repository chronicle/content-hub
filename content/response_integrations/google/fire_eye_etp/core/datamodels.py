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
from typing import TYPE_CHECKING, Any

from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time

from .fire_eye_etp_constants import ALERT_NAME
from .utils_manager import naive_time_converted_to_aware

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class BaseModel:
    """Base model for inheritance."""

    def __init__(self, raw_data: SingleJson) -> None:
        """Initialize the BaseModel.

        Args:
            raw_data: The raw JSON data.

        """
        self.raw_data = raw_data

    def to_json(self) -> SingleJson:
        """Convert the model to JSON.

        Returns:
            The raw JSON data.

        """
        return self.raw_data


class Alert(BaseModel):
    """Represent a FireEye ETP Alert."""

    def __init__(
        self,
        raw_data: SingleJson,
        timezone_offset: str | None = None,
    ) -> None:
        """Initialize the Alert.

        Args:
            raw_data: The raw JSON data.
            timezone_offset: The timezone offset.

        """
        super().__init__(raw_data)
        alert_sub: SingleJson = (
            raw_data.get("alert", {}) if isinstance(raw_data.get("alert"), dict) else {}
        )
        email_header: SingleJson = (
            alert_sub.get("email-header")
            or raw_data.get("email-header", {})
            or raw_data.get("attributes", {}).get("email", {}).get("headers", {})
        )
        smtp_message: SingleJson = (
            alert_sub.get("smtp-message")
            or raw_data.get("smtp-message", {})
            or raw_data.get("attributes", {}).get("email", {}).get("smtp", {})
        )
        explanation: SingleJson = (
            alert_sub.get("explanation", {})
            or raw_data.get("attributes", {}).get("alert", {}).get("explanation", {})
        )
        malware_detected: SingleJson = (
            explanation.get("malware-detected", {})
            or explanation.get("malware_detected", {})
        )

        self.id: str | None = (
            raw_data.get("id")
            or alert_sub.get("uuid")
            or raw_data.get("report_id")
            or raw_data.get("attributes", {}).get("alert", {}).get("uuid")
        )
        self.timestamp: str | None = (
            alert_sub.get("occurred")
            or alert_sub.get("attack-time")
            or raw_data.get("alert_date")
            or raw_data.get("accepted_time")
            or raw_data.get("attributes", {}).get("email", {}).get("timestamp", {}).get("accepted")
            or raw_data.get("attributes", {}).get("alert", {}).get("occurred")
        )

        mitre_mappings: list[Any] = raw_data.get("mitre_mapping", [])
        mitre_severity: str | None = None
        if isinstance(mitre_mappings, list):
            for mapping in mitre_mappings:
                if isinstance(mapping, dict) and mapping.get("severity"):
                    mitre_severity = str(mapping.get("severity"))
                    break

        self.severity: str | None = (
            mitre_severity
            or alert_sub.get("severity")
            or raw_data.get("severity")
            or raw_data.get("attributes", {}).get("alert", {}).get("severity")
        )
        self.etp_message_id: str = (
            email_header.get("message-id")
            or smtp_message.get("queue-id")
            or raw_data.get("mta_msg_id")
            or raw_data.get("attributes", {}).get("email", {}).get("etp_message_id")
            or (self.id or "")
        )
        legacy_malwares = (
            raw_data.get("attributes", {})
            .get("alert", {})
            .get("explanation", {})
            .get("malware_detected", {})
            .get("malware", [])
        )
        self.malwares: list[SingleJson] = (
            malware_detected.get("malware", [])
            or raw_data.get("malware", [])
            or legacy_malwares
        )

        smtp_to: Any = smtp_message.get("to") or smtp_message.get("rcpt_to")
        if isinstance(smtp_to, list):
            smtp_recipients: list[str] = [str(r) for r in smtp_to if r]
        elif isinstance(smtp_to, str):
            smtp_recipients = smtp_to.split()
        else:
            smtp_recipients = []

        if not smtp_recipients and alert_sub.get("dst", {}).get("smtp-to"):
            smtp_recipients = [str(alert_sub["dst"]["smtp-to"])]

        legacy_recipients: list[str] = (
            raw_data.get("attributes", {}).get("email", {}).get("smtp", {}).get("rcpt_to", "").split()
        )
        self.recipients: list[str] = smtp_recipients or legacy_recipients
        self.name: str = ALERT_NAME
        self.timezone_offset: str | None = timezone_offset

    @property
    def priority(self) -> int:
        """The priority of the alert.

        Returns:
            The priority value (60, 80, or 100).

        """
        if self.severity in {"majr", "high"}:
            return 80
        if self.severity in {"crit", "critical"}:
            return 100
        if self.severity in {"minr", "medium"}:
            return 60
        if self.severity in {"info", "low"}:
            return 40

        return 60

    @property
    def events(self) -> list[SingleJson]:
        """The events from the alert.

        Returns:
            The list of events.

        """
        events: list[SingleJson] = []

        if self.malwares:
            for malware in self.malwares:
                malware_copy = copy.deepcopy(malware)
                alert_copy = copy.deepcopy(self.raw_data)
                if isinstance(alert_copy, dict):
                    if isinstance(alert_copy.get("alert"), dict):
                        alert_copy["alert"].get("explanation", {}).get("malware-detected", {}).pop("malware", None)
                        alert_copy["alert"].get("explanation", {}).get("malware_detected", {}).pop("malware", None)
                    if isinstance(alert_copy.get("attributes"), dict):
                        alert_copy["attributes"].get("alert", {}).get("explanation", {}).pop("os_changes", None)
                        explanation_node = alert_copy["attributes"].get("alert", {}).get("explanation", {})
                        explanation_node.get("malware_detected", {}).pop("malware", None)
                if isinstance(malware_copy, dict):
                    malware_copy["alert"] = alert_copy
                    events.append(malware_copy)
                else:
                    events.append({"name": str(malware_copy), "alert": alert_copy})
        else:
            events.append(copy.deepcopy(self.raw_data))

        return events

    @property
    def recipient_events(self) -> list[SingleJson]:
        """The recipient events from the alert.

        Returns:
            The list of recipient events.

        """
        events: list[SingleJson] = []

        for recipient in self.recipients:
            event = {
                "event_name": "FireEye ETP Recipient",
                "description": "This is a custom Siemplify Event created for mapping of the recipients",
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
        if not self.timestamp:
            return 0
        try:
            return convert_datetime_to_unix_time(naive_time_converted_to_aware(self.timestamp, self.timezone_offset))
        except (ValueError, TypeError, AttributeError):
            return 0
