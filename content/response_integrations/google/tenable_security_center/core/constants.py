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
PROVIDER_NAME = "TenableSecurityCenter"
HEADERS = {"Content-Type": "application/json"}
OFFSET = 50
CONNECTIVITY_ERROR_MESSAGE = "Failed to connect to Tenable Security Center"

# Actions
RUN_ASSET_SCAN_SCRIPT_NAME = f"{PROVIDER_NAME} - Run Asset Scan"
CREATE_IP_LIST_ASSET_SCRIPT_NAME = f"{PROVIDER_NAME} - Create IP List Asset"
ADD_IP_TO_LIST_ASSET_SCRIPT_NAME = f"{PROVIDER_NAME} - Add IP To IP List Asset"
SCRIPT_NAME = "TenableSecurityCenter - EnrichIP"


ENDPOINTS = {
    "get_assets": "/rest/asset",
    "scan": "/rest/scan",
    "asset_details": "/rest/asset/{asset_id}",
}


UNIX_FORMAT = 1
DATETIME_FORMAT = 2
DAY_IN_MILLISECONDS = 86400000
