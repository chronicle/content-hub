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

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


INTEGRATION_IDENTIFIER: str = "ProofpointCloudThreatResponse"
INTEGRATION_NAME: str = "Proofpoint Cloud Threat Response"

PING_SCRIPT_NAME: str = f"{INTEGRATION_NAME}- Ping"
CONNECTOR_SCRIPT_NAME = "Proofpoint Cloud Threat Response - Incidents Connector"

DEFAULT_API_ROOT: str = "https://threatprotection-api.proofpoint.com"
AUTH_URL: str = "https://auth.proofpoint.com/v1/token"
DEFAULT_VERIFY_SSL: bool = True

ENDPOINTS: Mapping[str, str] = {
    "ping": "api/v1/tric/incidents",
    "list_incidents": "api/v1/tric/incidents",
    "get_incident_messages": "api/v1/tric/incidents/{incident_id}/messages",
}

MAX_INCIDENTS_LIMIT: int = 9
MIN_INT_PARAM_LIMIT: int = 1

SEVERITY_MAP: Mapping[str, list[str]] = {
    "Low": ["low", "medium", "high"],
    "Medium": ["medium", "high"],
    "High": ["high"],
}
CONFIDENCE_MAP: Mapping[str, list[str]] = {
    "Low": ["confidence_low", "confidence_medium", "confidence_high"],
    "Medium": ["confidence_medium", "confidence_high"],
    "High": ["confidence_high"],
}
STATUS_MAP: Mapping[str, str] = {"Open": "open", "Closed": "closed"}
VERDICT_MAP: Mapping[str, str] = {
    "Failed": "verdict_failed",
    "Low Risk": "verdict_low_risk",
    "Manual Review": "verdict_manual_review",
    "Threat": "verdict_threat",
}
DISPOSITION_MAP: Mapping[str, str] = {
    "Bulk": "bulk",
    "Clean": "clean",
    "Impostor": "impostor",
    "In Progress": "in_progress",
    "Internal": "internal",
    "Low Risk": "low_risk",
    "Malware": "malware",
    "Manual Review": "manual_review",
    "Not Set": "not_set",
    "Phish": "phish",
    "Scam": "scam",
    "Simulated Phish": "simulated_phish",
    "Spam": "spam",
    "Suspicious": "suspicious",
    "Tap False Positive": "tap_false_positive",
    "Toad": "toad",
    "Vendor": "vendor",
}

DEFAULT_VENDOR: str = "Proofpoint Cloud Threat Response"
DEFAULT_PRODUCT: str = "Incident"
DEFAULT_PRIORITY: str = "low"
SOURCE_GROUPING_IDENTIFIER_FORMAT: str = "ProofpointCTR_{incident_id}"


class AlertSeverityEnum(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def priority(self) -> int:
        return SECOPS_SEVERITY_MAP[self]

    @property
    def severity(self) -> int:
        return self.value.title()

    @property
    def risk_score(self) -> int:
        return SECOPS_SEVERITY_MAP[self]


SECOPS_SEVERITY_MAP: Mapping[str, int] = {
    AlertSeverityEnum.LOW: 40,
    AlertSeverityEnum.MEDIUM: 60,
    AlertSeverityEnum.HIGH: 80,
}
