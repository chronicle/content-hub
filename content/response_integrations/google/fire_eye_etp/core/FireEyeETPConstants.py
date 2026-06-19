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
PROVIDER_NAME = "FireEye ETP"

# ACTIONS
PING_SCRIPT_NAME = f"{PROVIDER_NAME} - Ping"

ENDPOINTS = {
    "test_connectivity": "/api/v2/public/alerts/search",
    "get_alerts": "/api/v2/public/alerts/search",
    "get_alert_details": "/api/v2/public/alerts/{alert_id}",
}

# AUTHENTICATION
TOKEN_URL = "https://auth.trellix.com/auth/realms/IAM/protocol/openid-connect/token"
NEW_AUTH_HEADER = "Authorization"
LEGACY_AUTH_HEADER = "x-fireeye-api-key"
ETP_SCOPES = "etp.conf.ro etp.trce.rw etp.admn.ro etp.domn.ro etp.accs.rw etp.quar.rw etp.domn.rw etp.rprt.rw etp.accs.ro etp.quar.ro etp.alrt.rw etp.rprt.ro etp.conf.rw etp.trce.ro etp.alrt.ro etp.admn.rw"


HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

ALERTS_CONNECTOR_NAME = "FireEye ETP - Email Alerts Connector"

TIMEOUT_THRESHOLD = 0.9
LIMIT_IDS_IN_IDS_FILE = 1000
TEST_OFFSET_HOURS = 24
ACCEPTABLE_TIME_INTERVAL_IN_MINUTES = 5
WHITELIST_FILTER = "whitelist"
BLACKLIST_FILTER = "blacklist"
DEFAULT_TIME_FRAME = 1
ALERT_ID_FIELD = "id"
DEFAULT_FETCH_SIZE = 200

MAP_FILE = "map.json"
IDS_FILE = "ids.json"

DEVICE_VENDOR = "FireEye"
DEVICE_PRODUCT = "FireEye ETP"
ALERT_NAME = "Malicious Email"

PRINT_TIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
API_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
