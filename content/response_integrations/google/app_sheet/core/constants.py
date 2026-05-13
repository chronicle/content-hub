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
INTEGRATION_NAME = "AppSheet"
INTEGRATION_DISPLAY_NAME = "AppSheet"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
ADD_RECORD_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Add Record"
UPDATE_RECORD_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Update Record"
DELETE_RECORD_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Delete Record"
SEARCH_RECORDS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Search Records"
LIST_TABLES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - List Tables"

ENDPOINTS = {
    "ping": "/api/v2/apps/{app_id}/tables",
    "record_management": "/api/v2/apps/{app_id}/tables/{table_name}/Action",
    "list_tables": "/api/v2/apps/{app_id}/tables/",
}

SEARCH_RECORDS_TABLE_NAME = "Records"
LIST_TABLES_TABLE_NAME = "Available Tables"
DEFAULT_LIMIT = 50

EQUAL_FILTER = "Equal"
CONTAINS_FILTER = "Contains"
