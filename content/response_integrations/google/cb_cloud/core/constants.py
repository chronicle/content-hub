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
INTEGRATION_NAME = "CBCloud"
PROVIDER_NAME = "VMware Carbon Black Cloud"
DEFAULT_VENDOR = "VMware Carbon Black"

# ACTIONS NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
DISMISS_ALERT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Dismiss Alert"
ENRICH_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich Entities"
UNQUARANTINE_DEVICE_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Create Unquarantine Device Task"
)
CREATE_POLICY_UPDATE_TASK_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Create Policy Update Task"
)
QUARANTINE_DEVICE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create Quarantine Device Task"
CREATE_BACKGROUND_SCAN_TASK_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Create Background Scan Task"
)
CREATE_DISABLE_BYPASS_MODE_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Create Disable Bypass Mode Task"
)
CREATE_ENABLE_BYPASS_MODE_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Create Enable Bypass Mode Task"
)
CREATE_REPUTATION_OVERRIDE_FOR_IT_TOOL_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Create a Reputation Override for IT Tool"
)
CREATE_REPUTATION_OVERRIDE_FOR_CERTIFICATE_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Create a Reputation Override for Certificate"
)
CREATE_REPUTATION_OVERRIDE_FOR_SHA256_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Create a Reputation Override for SHA-256 Hash"
)
LIST_REPUTATION_OVERRIDES_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - List Reputation Overrides"
)
DELETE_REPUTATION_OVERRIDE_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Delete a Reputation Override"
)
EXECUTE_ENTITY_PROCESSES_SEARCH_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Execute Entity Processes Search"
)
LIST_HOST_VULNERABILITIES_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - List Host Vulnerabilities"
)

# CONNECTORS NAMES
ALERTS_CONNECTOR_NAME = "VMware Carbon Black Cloud Alerts Connector"
TRACKING_CONNECTOR_NAME = f"{PROVIDER_NAME} Alerts and Events Tracking Connector"
BASELINE_CONNECTOR_NAME = "VMware Carbon Black Cloud Alerts Connector"


# TABLES NAMES
PROCESS_SEARCH_RESULTS_TABLE_NAME = f"{PROVIDER_NAME} Process Search Results"

NEW_LINE = "\n"

ALERT_TYPES_WITHOUT_ENRICHED_EVENTS_BASELINE = ["WATCHLIST"]
OFFSET_FILE = "offset.json"
MAP_FILE = "map.json"

# TRACKING CONNECTOR
DEFAULT_MAX_ALERTS_PER_CYCLE = 100
DEFAULT_ALERT_FIELD_FOR_RULE_NAME = "type"
DEFAULT_ALERT_FIELD_FOR_RULE_GENERATOR = "type"
DEFAULT_EVENTS_PADDING_PERIOD = 24
DEFAULT_EVENTS_LIMIT_TO_INGEST_PER_ALERT = 25
WHITELIST_FILTER = "whitelist"
BLACKLIST_FILTER = "blacklist"
EMPTY_LEGACY_ID = "XXXXXXXX"
OFFENSE_EVENTS_FILE = "offense_events.json"
BACKLOG_FILE = "backlog_ids.json"
TIMEOUT_THRESHOLD = 0.9
WATCHLIST_TYPE = "watchlist"
ALERT_TYPES_WITHOUT_ENRICHED_EVENTS = ["WATCHLIST", "DEVICE_CONTROL"]
SIEMPLIFY_ALERT_NAME = "CBCLOUD_Alert_{}"
SIEMPLIFY_RULE_GENERATOR = "CBCLOUD_{}"
MAX_ENRICHED_EVENTS_PER_REQUEST = 10
BACKLOG_DB_KEY = "backlog_ids"
OFFENSE_ALERTS_DB_KEY = "offense_alerts"
OFFENSE_EVENTS_DB_KEY = "offense_events"
KEY_FOR_SAVED_ALERTS = "offenses"
KEY_FOR_SAVED_EVENTS = "events"
KEY_FOR_SAVED_EVENTS_TIME = "timestamp"
ALERT_NAME_ALLOWED_VALUE = ["type", "policy_name"]
MAX_EVENTS_PER_ALERT = 100
DEFAULT_MAX_BACKLOG_ALERTS_PER_CYCLE = 10
KEY_FOR_SAVED_ALERTS_TIME = "last_seen_time"
KEY_FOR_UPDATED_ALERTS_TIME = "last_update_time"
DEFAULT_TOTAL_LIMIT_OF_EVENTS_PER_ALERT = 100
EVENTS_COUNT_TRACKING_FILE = "events_count_tracking.json"
EVENTS_COUNT_TRACKING_DB_KEY = "events_count_tracking"
EVENTS_COUNT_TRACKING_TS_KEY = "first_ingested_time"
EVENTS_COUNT_TRACKING_COUNT_KEY = "events_count"

# ACTIONS
BLACK_LIST_REPUTATION = "BLACK_LIST"
WHITE_LIST_REPUTATION = "WHITE_LIST"
NOT_SPECIFIED = "Not Specified"
SHA256_REGEX = r"^[A-Fa-f0-9]{64}$"
COMMASPACE = ", "
ASC = "ASC"
DESC = "DESC"
MAPPED_SORT_ORDER = {ASC: "asc", DESC: "desc"}

PLACEHOLDER_START = "["
PLACEHOLDER_END = "]"
CHARACTERS_LIMIT = 256


SEVERITY_FILTER_MAPPING = {
    "critical": "CRITICAL",
    "important": "IMPORTANT",
    "moderate": "MODERATE",
    "low": "LOW",
}

ALERT_CLOSE_REASON = {
    "Specify a Value": "",
    "No dismissal reason": "NO_REASON",
    "Resolved": "RESOLVED",
    "Resolved - Benign/Known good": "RESOLVED_BENIGN_KNOWN_GOOD",
    "Duplicate/Cleanup": "DUPLICATE_CLEANUP",
    "Other": "OTHER",
}

ALERT_DETERMINATION = {
    "Specify a Value": "",
    "None": "NONE",
    "True positive": "TRUE_POSITIVE",
    "False positive": "FALSE_POSITIVE",
}

HTTP_STATUS_CODE_BAD_REQUEST = 400
HTTP_STATUS_CODE_UNAUTHORIZED = 401
