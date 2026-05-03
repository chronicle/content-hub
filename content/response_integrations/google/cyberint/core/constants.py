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
INTEGRATION_NAME = "Cyberint"
INTEGRATION_DISPLAY_NAME = "Cyberint"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
UPDATE_ALERT_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Update Alert"

ENDPOINTS = {
    "ping": "/alert/api/v1/alerts",
    "get_alerts": "/alert/api/v1/alerts",
    "update_alert": "/alert/api/v1/alerts/status",
}


# Connector
CONNECTOR_NAME = f"{INTEGRATION_DISPLAY_NAME} - Outscan Findings Connector"
DEFAULT_TIME_FRAME = 1
DEFAULT_LIMIT = 100
DEVICE_VENDOR = "CyberInt"
DEVICE_PRODUCT = "CyberInt"
API_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

SEVERITY_MAP = {"low": 40, "medium": 60, "high": 80, "very_high": 100}

SEVERITIES = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "very_high": "very high",
}

STATUS_MAPPING = {
    "Select One": "",
    "Open": "open",
    "Acknowledged": "acknowledged",
    "Closed": "closed",
}

CLOSURE_REASON_MAPPING = {
    "Select One": "",
    "Resolved": "resolved",
    "Irrelevant": "irrelevant",
    "False Positive": "false_positive",
}

CLOSED_STATUS = "closed"
