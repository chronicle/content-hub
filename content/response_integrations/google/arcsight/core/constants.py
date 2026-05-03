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
INTEGRATION_NAME = "Arcsight"


# ACTIONS
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Ping'}"
SEARCH_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'SEARCH'}"
LIST_RESOURCES_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'List Resources'}"
ADD_ENTRIES_TO_ACTIVE_LIST_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - {'Add Entries To Activelist'}"
)
GET_ACTIVE_LIST_ENTRIES_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Get Activelist Entries'}"
ADD_ENTITIES_TO_ACTIVE_LIST = f"{INTEGRATION_NAME} - {'Add Entities To Active List'}"
GET_QUERY_RESULTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Get Query Results'}"
IS_VALUE_IN_ACTIVELIST_COLUMN_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - {'Is Value In Activelist Column'}"
)
GET_REPORT_ACTION_NAME = f"{INTEGRATION_NAME} - {'Get Report'}"
CHANGE_CASE_STAGE_SCRIPT_NAME = f"{INTEGRATION_NAME} - {'Change Case Stage'}"

# LIMIT DEFAULTS
DEFAULT_LIMIT = 100

CSV = "csv"

# VALID STAGES CONSTANT
VALID_STAGES = ["INITIAL", "QUEUED", "CLOSED", "FINAL", "FOLLOW_UP"]


EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
DOMAIN_REGEX = r"[a-zA-Z\d-]{,63}(\.[a-zA-Z\d-]{,63})+"


# ADDITIONAL ENTITY TYPES
EMAIL_TYPE = 101
DOMAIN_TYPE = 102

UNSUPPORTED_REPORT_UUID_PREFIXES = ["94jAWS+"]

SECURITY_EVENTS_CONNECTOR = "ArcSight - Security Events Connector"
DEFAULT_LIMIT_FOR_CONNECTOR = 100
MAX_LIMIT_FOR_CONNECTOR = 1000
DEFAULT_DEVICE_PRODUCT = "Security Event"
DEFAULT_DEVICE_VENDOR = "ArcSight"
REPORT_FILE_NAME = "report.json"
STORED_IDS_LIMIT = 10000
MAX_EVENTS_LIMIT = 200
