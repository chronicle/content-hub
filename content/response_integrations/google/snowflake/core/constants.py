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
INTEGRATION_NAME = "Snowflake"
INTEGRATION_DISPLAY_NAME = "Snowflake"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
EXECUTE_CUSTOM_QUERY_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Execute Custom Query"
EXECUTE_SIMPLE_QUERY_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Execute Simple Query"

ENDPOINTS = {
    "ping": "/api/v2/statements?async=false",
    "submit_query": "/api/v2/statements?async=true",
    "get_data": "/api/v2/statements/{query_id}",
}

EXECUTION_FINISHED = 0
EXECUTION_IN_PROGRESS = 1
ALL_FIELDS_WILDCARD = "*"
ASC_SORT_ORDER = "ASC"
