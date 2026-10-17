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
PROVIDER_NAME = "Mandiant Digital Threat Monitoring"
INTEGRATION_NAME = "MandiantDigitalThreatMonitoring"
INTEGRATION_PREFIX = "Mandiant_DTM_"

# Action names
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"

ENDPOINTS = {
    "generate_token": "/token",
    "test_connectivity": "/v4/dtm/alerts?size=1",
    "get_alerts": "/v4/dtm/alerts",
    "update_alert": "/v4/dtm/alerts/{alert_id}",
}

GTI_ENDPOINTS = {
    "test_connectivity": "/api/v3/dtm/alerts?size=1",
    "get_alerts": "/api/v3/dtm/alerts",
    "update_alert": "/api/v3/dtm/alerts/{alert_id}",
}

# alerts connector
ALERTS_CONNECTOR = "Mandiant Digital Threat Monitoring - Alerts Connector"
MAX_LIMIT = 25
SEVERITIES = ["low", "medium", "high"]
STORED_IDS_LIMIT = 10_000
DEFAULT_DEVICE_VENDOR = "MandiantDigitalThreatMonitoring"
DEFAULT_DEVICE_PRODUCT = "Alerts"
SEVERITY_MAPPING = {"low": 40, "medium": 60, "high": 80}
MAIN_ALERT_EVENT_TYPE = "Main Alert"
ALERT_STATUSES = ["escalated", "in_progress", "new", "read"]
EVENTS_LIMIT = 400
UPDATE_ALERT_NAME = "Update Alert"

ALERT_STATUS_MAPPING = {
    "Select One": None,
    "New": "new",
    "Read": "read",
    "Closed": "closed",
    "Escalated": "escalated",
    "In Progress": "in_progress",
    "No Action Required": "no_action_required",
    "Duplicate": "duplicate",
    "Not Relevant": "not_relevant",
    "Tracked Externally": "tracked_external",
}

UNAUTHORIZED_ERROR_MESSAGE = "401 Client Error"

GTI_ROOT = "https://www.virustotal.com/api/v3/"
MANDIANT_ROOT = "https://api.intelligence.mandiant.com/v4"
