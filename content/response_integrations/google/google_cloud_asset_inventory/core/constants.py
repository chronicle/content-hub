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
PROVIDER_NAME = "GoogleCloudAssetInventory"
INTEGRATION_NAME = "GoogleCloudAssetInventory"
INTEGRATION_DISPLAY_NAME = "Google Cloud Asset Inventory"
# ACTION NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
ENRICH_RESOURCE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich Resource"
LIST_SERVICE_ACCOUNT_ROLES_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - List Service Account Roles"
)
GET_RESOURCE_SNAPSHOT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Resource Snapshot"

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

# ENDPOINTS
ENDPOINTS = {
    "ping": "v1/{type}/{id}:searchAllResources?pageSize=1",
    "get_resource_details": (
        "v1/{type}/{id}:searchAllResources?pageSize={page_size}"
        "&readMask={read_mask}&query={query}"
    ),
    "analyze_iam_policy": "v1/{type}/{id}:analyzeIamPolicy",
    "get_resource_snapshots": (
        "v1/{type}/{id}:batchGetAssetsHistory?assetNames={asset_names}"
        "&fields={read_mask}&contentType=RESOURCE"
    ),
}

FORBIDDEN_STATUS = 403
NOT_FOUND_STATUS = 404
RATE_LIMIT_STATUS = 429
RESOURCE_NAME_KEY = "name"
RESOURCE_SNAPSHOT_NAME_KEY = "assets.asset.name"
DEFAULT_FIELDS_TO_RETURN = "*"
QUERY_CHARACTER_LIMIT = 2104
NOT_FOUND_RESOURCES_PATTERN = (
    r"The following \d+ resources don\'t exist in "
    r"(projects|organizations)\/(\w|-)+\s+: (.+)\n"
)
MAX_ASSETS_TO_QUERY = 100
RESOURCE_ALLOWED_CHARACTERS = r"(\w|-|\.|\/)+"
