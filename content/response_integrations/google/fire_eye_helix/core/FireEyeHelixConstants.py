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
PROVIDER_NAME = "FireEye Helix"
DEVICE_VENDOR = "FireEye"
DEVICE_PRODUCT = "FireEye Helix"
ALERTS_LIMIT = 50
NOTES_LIMIT = 50
ALERTS_FETCH_SIZE = 100
NEXT_PAGE_URL_KEY = "next"
META_URL_KEY = "meta"
QUERY_TYPE = "json"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S %p"
REQUEST_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
ENRICHMENT_PREFIX = "FEHelix"

# Do not change the order, It's used in Manager._get_severities_from
SEVERITIES = ["Low", "Medium", "High", "Critical"]
LOW_SEVERITY = "Low"
DEFAULT_SEVERITY = "Medium"

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
DEFAULT_TIME_FRAME = 1

# ACTIONS
PING_SCRIPT_NAME = f"{PROVIDER_NAME} - Ping"
SUPPRESS_ALERT_SCRIPT_NAME = f"{PROVIDER_NAME} - Suppress Alert"
CLOSE_ALERT_SCRIPT_NAME = f"{PROVIDER_NAME} - Close Alert"
ADD_NOTE_TO_ALERT_SCRIPT_NAME = f"{PROVIDER_NAME} - Add Note To Alert"
GET_LISTS_SCRIPT_NAME = f"{PROVIDER_NAME} - Get Lists"
GET_LIST_ITEMS_SCRIPT_NAME = f"{PROVIDER_NAME} - Get List Items"
ADD_ENTITIES_TO_A_LIST = f"{PROVIDER_NAME} - Add Entities To a List"
INDEX_SEARCH_SCRIPT_NAME = f"{PROVIDER_NAME} - Index Search"
ARCHIVE_SEARCH_SCRIPT_NAME = f"{PROVIDER_NAME} - Archive Search"
ENRICH_ENDPOINT_SCRIPT_NAME = f"{PROVIDER_NAME} - Enrich Endpoint"
GET_ALERT_DETAILS_SCRIPT_NAME = f"{PROVIDER_NAME} - Get Alert Details"
ENRICH_USER_SCRIPT_NAME = f"{PROVIDER_NAME} - Enrich User"

# SIEM
FIREEYE_HELIX_TO_SIEM_SEVERITY = {"Low": 40, "Medium": 60, "High": 80, "Critical": 100}

ENDPOINTS = {
    "test_connectivity": "api/v3/appliances/health",
    "suppress_alert": "api/v1/alerts/{alert_id}/suppress",
    "close_alert": "api/v1/alerts/{alert_id}",
    "add_note": "api/v3/alerts/{alert_id}/notes",
    "get_lists": "api/v3/lists",
    "get_list_items": "api/v3/lists/{list_id}/items",
    "get_alerts": "api/v3/alerts/",
    "get_events": "api/v3/alerts//{id}/events",
    "search": "api/v1/search",
    "archive_search": "api/v1/search/archive",
    "archive_search_results": "api/v1/search/archive/{job_id}/results",
    "resume_archive_search": "api/v1/search/archive/{job_id}/resume",
    "get_assets": "api/v3/assets",
}

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
}

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

SORT_BY_MAPPER = {
    "Name": "name",
    "Short Name": "short_name",
    "Created At": "created_at",
}

SORT_ORDER_MAPPER = {"Ascending": "", "Descending": "-"}

ITEM_TYPE_MAPPER = {
    "ALL": "",
    "Email": "email",
    "FQDN": "fqdn",
    "IPv4": "ipv4",
    "IPv6": "ipv6",
    "MD5": "md5",
    "MISC": "misc",
    "SHA-1": "sha1",
}

ITEM_SORT_BY_MAPPER = {"Value": "value", "Type": "type", "Risk": "risk"}

ITEM_TYPES = {
    "email": "email",
    "fqdn": "fqdn",
    "ipv4": "ipv4",
    "ipv6": "ipv6",
    "md5": "md5",
    "sha1": "sha1",
    "misc": "misc",
}

ACCEPTABLE_TIME_UNITS = {"d": 24, "h": 1}

SHIFT_HOURS = 4

VALID_TIME_FRAME_PATTERN = "^(?!.*([dh]).*\1)\d+[dh](?: \d+[dh])*$"

JOB_FINISHED_STATUS = "complete"
JOB_PAUSED_STATUS = "paused"
