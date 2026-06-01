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
INTEGRATION_NAME = "Google Alert Center"
INTEGRATION_DISPLAY_NAME = "Google Alert Center"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
DELETE_ALERT_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Delete Alert"

ENDPOINTS = {
    "ping": "alerts?pageSize={limit}",
    "alerts": 'alerts?pageSize={limit}&orderBy=createTime asc&filter=createTime >= "{timestamp}"',
    "delete_alert": "alerts/{alert_id}",
}

GOOGLE_APIS_ALERTS_ROOT = "https://alertcenter.googleapis.com/v1beta1/"
SCOPES = ["https://www.googleapis.com/auth/apps.alerts"]

SUCCESS_STATUSES = ["200"]


# Connector
CONNECTOR_NAME = "Google Alert Center - Alerts Connector"
DEFAULT_TIME_FRAME = 1
DEFAULT_LIMIT = 100
DEFAULT_MAX_LIMIT = 100
DEVICE_VENDOR = "Google"
DEVICE_PRODUCT = "Google Alert Center"
CONNECTOR_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

DEFAULT_SEVERITY = -1
SEVERITY_MAP = {"informational": -1, "low": 40, "medium": 60, "high": 80}
