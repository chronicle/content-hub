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
INTEGRATION_DISPLAY_NAME = "AWS CloudWatch"

# actions:
PING = "Ping"
LIST_LOG_GROUPS = "List Log Groups"
LIST_LOG_STREAMS = "List Log Streams"
CREATE_LOG_GROUP = "Create Log Group"
CREATE_LOG_STREAM = "Create Log Stream"
DELETE_LOG_GROUP = "Delete Log Group"
DELETE_LOG_STREAM = "Delete Log Stream"
SEARCH_LOG_EVENTS = "Search Log Events"
REMOVE_RETENTION_POLICY = "Remove Retention Policy"
SET_RETENTION_POLICY = "Set Retention Policy"


DEFAULT_MAX_RESULTS = 50
DEFAULT_MIN_RESULTS = 1
DEFAULT_MIN_GROUPS = 1
PAGE_SIZE = 50

LOG_GROUPS_TABLE_NAME = "Log Groups"

SORTING_MAPPING = {"Ascending": False, "Descending": True}

ORDER_BY_MAPPING = {
    "Log Stream Name": "LogStreamName",
    "Last Event Time": "LastEventTime",
}

TIME_FRAME_MAPPING = {
    "Last Hour": 3600000,
    "Last 6 Hours": 21600000,
    "Last 24 Hours": 86400000,
    "Last Week": 604800000,
    "Last Month": 2592000000,
}
