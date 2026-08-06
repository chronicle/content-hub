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
PROVIDER_NAME = "Stellar Cyber Starlight"

# ACTIONS
PING_SCRIPT_NAME = f"{PROVIDER_NAME} - Ping"
SIMPLE_SEARCH_SCRIPT_NAME = f"{PROVIDER_NAME} - Simple Search"
ADVANCED_SEARCH_SCRIPT_NAME = f"{PROVIDER_NAME} - Advanced Search"
UPDATE_SECURITY_EVENT_SCRIPT_NAME = f"{PROVIDER_NAME} - Update Security Event"

ENDPOINTS = {
    "test_connectivity": "data/*/_search",
    "simple_search": "data/{index}/_search",
    "get_alerts": "data/aella-ser-*/_search",
    "update_event": "update_ser",
    "access_token": "v1/access_token",
}

HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

ASCENDING_SORT = "Ascending"
DESCENDING_SORT = "Descending"
DEFAULT_LIMIT = 50
BAD_REQUEST_STATUS_CODE = 400

# CONNECTORS
DEVICE_VENDOR = "Stellar Cyber"
DEVICE_PRODUCT = "Starlight"
SECURITY_EVENTS_CONNECTOR_NAME = f"{PROVIDER_NAME} - Security Events Connector"
ALERT_ID_FIELD = "id"
ACCEPTABLE_TIME_INTERVAL_IN_MINUTES = 5
WHITELIST_FILTER = "whitelist"
BLACKLIST_FILTER = "blacklist"
DEFAULT_TIME_FRAME = 1
ALERTS_FETCH_SIZE = 100
ALERTS_LIMIT = 50
DEFAULT_SEVERITY = 50
DB_ID_STORAGE_LIMIT = 5000
PRE_DISPLAY_ID = "Stellar_Cyber_"
TIMESTAMP_FIELD_DEFAULT_VALUE = "timestamp"
TIMESTAMP_FIELD_VALUES = ["timestamp", "write_time"]

STATUS_SELECT_ONE = "Select One"

NOT_KEY_OR_TOKEN_ALERT = "Either “API Key” or “API Token” needs to be provided."
UNAUTHORIZED_STATUS_CODE = 401
ACCESS_TOKEN_CHECK = "access_token"
UNAUTHORISED_ERROR_MESSAGE = (
    "Invalid {value} or username provided. Please validate credentials."
)
INVALID_VALUE_MESSAGE = (
    "Invalid value provided in Max Events To Fetch, "
    "{ALERTS_LIMIT} will be used as fallback value"
)
