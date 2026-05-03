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
INTEGRATION_NAME = "CBLiveResponse"
PROVIDER_NAME = "VMware Carbon Black Endpoint Standard Live Response"
SHORT_PROVIDER_NAME = "CB Live Response"
VENDOR_NAME = "VMware Carbon Black Cloud"
SHORT_VENDOR_NAME = "VMware CB Cloud"

API_VERSION_V3 = 3
API_VERSION_V6 = 6

# ACTIONS NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
LIST_FILES_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Files"
LIST_PROCESSES_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Processes"
PUT_FILE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Put File"
DELETE_FILE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Delete File"
KILL_PROCESS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Kill Process"
DOWNLOAD_FILE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Download File"
LIST_FILES_IN_CLOUD_STORAGE_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - List Files in Cloud Storage"
)
CREATE_MEMDUMP_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create Memdump"
DELETE_FILE_FROM_CLOUD_STORAGE = f"{INTEGRATION_NAME} - Delete File from Cloud Storage"
EXECUTE_FILE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Execute File"

DEFAULT_PAGE_SIZE = 50
SLEEP_TIME = 2
DEFAULT_RESULTS_LIMIT = 25
DEFAULT_TIMEOUT = 300

# CASE WALL TABLE NAMES
FILES_CASE_WALL = "{} Directory List on {}"
PROCESSES_CASE_WALL = "{} Process List"
STORAGE_FILES_CASE_WALL = "{} file storage for session {}"

ERROR_JSON = {"step": "Not available", "reason": "Not available"}
