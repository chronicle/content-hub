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
INTEGRATION_NAME = "Splunk"
DEFAULT_ALERTS_FETCH_LIMIT = 100
DEFAULT_ALERTS_PROCESS_LIMIT = 50
DEFAULT_TIME_FRAME = 1
MAX_EVENTS_COUNT = 200
MAX_PADDING_TIME = 100
AUTO_FINALIZE_EC_LIMIT = 10_000

DEFAULT_DEVICE_VENDOR = "Splunk"
DEFAULT_DEVICE_PRODUCT = "Splunk SE"
SPLUNK_EVENT_TYPE = "Notable Events"

EMAIL_PATTERN = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
# MAPPINGS
TIME_UNIT_MAPPER = {
    "y": "year",
    "q": "quarter",
    "mon": "months",
    "w": "weeks",
    "d": "days",
    "h": "hours",
    "m": "minutes",
    "s": "seconds",
}


SEVERITY_MAPPER = {
    -1: "informational",
    40: "low",
    60: "medium",
    80: "high",
    100: "critical",
}

SEARCH_NAME_SOURCE = "search_name"
ALERT_NAME_SOURCE_MAPPER = {
    "Search Name": SEARCH_NAME_SOURCE,
    "Rule Name": "rule_title",
}

# ACTIONS NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
UPDATE_NOTABLE_EVENTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Notable Events"
SUBMIT_EVENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - SubmitEvent"
SPLUNK_QUERY_SCRIPT_NAME = f"{INTEGRATION_NAME} - Splunk Query"
EXECUTE_ENTITY_QUERY_SCRIPT_NAME = f"{INTEGRATION_NAME} - Execute Entity Query"
GET_HOST_EVENTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - GetHostEvents"


# JOBS NAMES
SYNC_COMMENTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Sync SplunkES Comments"
SYNC_CLOSURE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Sync Splunk ES Closed Events"


# CONNECTORS NAMES
CONNECTOR_NAME = f"{INTEGRATION_NAME} - Notable Events Connector"
QUERY_CONNECTOR_SCRIPT_NAME = f"{INTEGRATION_NAME} - Query Connector"


# TABLES NAMES
QUERY_RESULTS_TABLE_NAME = "Splunk Query Results"
HOST_EVENTS_TABLE_NAME = "Events"


OPEN_CASE_STATUS_ENUM = "1"
SIEMPLIFY_COMMENT_PREFIX = "Siemplify: "
SPLUNK_COMMENT_PREFIX = "Splunk ES: "
CASE_STATUS_CLOSED = 2
CASE_STATUS_OPEN = 1
SPLUNK_CLOSED_STATUS = "5"
SPLUNK_RESOLVED_STATUS = "4"
REASON = "Maintenance"
ROOT_CAUSE = "None"
COMMENT = f"Alert was closed by {SYNC_CLOSURE_SCRIPT_NAME}"
DEFAULT_QUERY_LIMIT = 100
FROM_TIME_DEFAULT = "-24h"
TO_TIME_DEFAULT = "now"
HOST_KEY = "host"
CROSS_OPERATORS = {"OR": "OR", "AND": "AND"}

# API Status Codes
API_BAD_REQUEST = 400
API_SERVER_ERROR = 500
UNIX_FORMAT = 1
DEFAULT_ALERT_NAME = "Splunk ES Alert"

DISPOSITION_MAPPER = {
    "Undefined": 0,
    "True Positive - Suspicious Activity": 1,
    "Benign Positive - Suspicious But Expected": 2,
    "False Positive - Incorrect Analytic Logic": 3,
    "False Positive - Inaccurate Data": 4,
    "Other": 5,
}

STORED_IDS_LIMIT = 5000
MAX_ATTEMPT_FOR_JOB_RESULT = 3
