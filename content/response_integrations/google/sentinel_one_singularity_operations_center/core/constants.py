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

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

# Integration Identifiers
INTEGRATION_IDENTIFIER: str = "SentinelOneSingularityOperationsCenter"
INTEGRATION_DISPLAY_NAME: str = "SentinelOne Singularity Operations Center"

# Script Identifiers
PING_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Ping"

# Default Configuration Parameter Values
DEFAULT_VERIFY_SSL: bool = True

# API Constants
ENDPOINTS: Mapping[str, str] = {
    "graphql": "/web/api/v2.1/unifiedalerts/graphql",
    "users": "/web/api/v2.1/users",
}


# Timeouts
REQUEST_TIMEOUT: int = 30

# Severity Name Constants
SEVERITY_INFO: str = "INFO"
SEVERITY_LOW: str = "LOW"
SEVERITY_MEDIUM: str = "MEDIUM"
SEVERITY_HIGH: str = "HIGH"
SEVERITY_CRITICAL: str = "CRITICAL"

# Severity/Priority mapping for Siemplify AlertInfo
SEVERITY_MAP: Mapping[str, int] = {
    SEVERITY_CRITICAL: 100,
    SEVERITY_HIGH: 80,
    SEVERITY_MEDIUM: 60,
    SEVERITY_LOW: 40,
    SEVERITY_INFO: -1,
}

SEVERITIES: list[str] = [
    SEVERITY_INFO,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_HIGH,
    SEVERITY_CRITICAL,
]

# Event Type Fields and Values
EVENT_TYPE_FIELD: str = "event_type"


class EventType(StrEnum):
    ALERT = "Alert"
    OBSERVABLE = "Observable"
    INDICATOR = "Indicator"
    ASSET = "Asset"


# Mapping from UI Dropdowns to SentinelOne API Enum Values
STATUS_MAP: Mapping[str, str] = {
    "New": "NEW",
    "In Progress": "IN_PROGRESS",
    "Resolved": "RESOLVED",
}

VERDICT_MAP: Mapping[str, str] = {
    "True positive/Malware": "TRUE_POSITIVE_MALWARE",
    "True positive/Unauthorized access": "TRUE_POSITIVE_UNAUTHORIZED_ACCESS",
    "True positive/Data exfiltration": "TRUE_POSITIVE_DATA_EXFILTRATION",
    "True positive/Insider threat": "TRUE_POSITIVE_INSIDER_THREAT",
    "True positive/Phishing attack": "TRUE_POSITIVE_PHISHING_ATTACK",
    "True positive/Advanced persistent threat": "TRUE_POSITIVE_ADVANCED_PERSISTENT_THREAT",
    "True positive/Denial of service": "TRUE_POSITIVE_DENIAL_OF_SERVICE",
    "True positive/Ransomware": "TRUE_POSITIVE_RANSOMWARE",
    "True positive/Policy violation": "TRUE_POSITIVE_POLICY_VIOLATION",
    "True positive/Benign but suspicious": "TRUE_POSITIVE_BENIGN_BUT_SUSPICIOUS",
    "True positive/Benign": "TRUE_POSITIVE_BENIGN",
    "True positive/Undefined": "TRUE_POSITIVE_UNDEFINED",
    "True positive/Exploitation tools": "TRUE_POSITIVE_EXPLOITATION_TOOLS",
    "True positive/PUA Adware": "TRUE_POSITIVE_PUA_ADWARE",
    "False positive/Benign": "FALSE_POSITIVE_BENIGN",
    "False positive/Benign but suspicious": "FALSE_POSITIVE_BENIGN_BUT_SUSPICIOUS",
    "False positive/System error": "FALSE_POSITIVE_SYSTEM_ERROR",
    "False positive/User error": "FALSE_POSITIVE_USER_ERROR",
    "False positive/Undefined": "FALSE_POSITIVE_UNDEFINED",
}
