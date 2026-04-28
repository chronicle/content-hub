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
PROVIDER_NAME = "ObserveIT"
DEVICE_VENDOR = "ObserveIT"
DEVICE_PRODUCT = "ObserveIT"
ALERTS_LIMIT = 100
# Do not change the order, It's used in Manager._get_severities_from
SEVERITIES = ["Low", "Medium", "High", "Critical"]


# REQUEST METHODS
GET = "GET"
POST = "POST"

# CONNECTORS
ALERTS_CONNECTOR_NAME = f"{PROVIDER_NAME} - Alerts Connector"
IDS_FILE = "ids.json"
MAP_FILE = "map.json"
ALERT_ID_FIELD = "id"
LIMIT_IDS_IN_IDS_FILE = 1000
TIMEOUT_THRESHOLD = 0.9
ACCEPTABLE_TIME_INTERVAL_IN_MINUTES = 5
WHITELIST_FILTER = "whitelist"
BLACKLIST_FILTER = "blacklist"

# ACTIONS
PING_SCRIPT_NAME = f"{PROVIDER_NAME} - Ping"

# SIEM
OBSERVE_IT_TO_SIEM_SEVERITY = {"Low": 40, "Medium": 60, "High": 80, "Critical": 100}
