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
PROVIDER_NAME = "GoogleCloudPolicyIntelligence"
INTEGRATION_NAME = "GoogleCloudPolicyIntelligence"
INTEGRATION_DISPLAY_NAME = "Google Cloud Policy Intelligence"
# ACTION NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
SEARCH_SERVICE_ACCOUNT_ACTIVITY_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Search Service Account Activity"
)

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

# ENDPOINTS
ENDPOINTS = {
    "ping": (
        "v1/projects/{project_id}/locations/{location_id}/activityTypes/"
        "serviceAccountLastAuthentication/activities:query"
        '?filter=activities.full_resource_name="test-connectivity"'
    ),
    "search_activity": (
        "v1/projects/{project_id}/locations/{location_id}/activityTypes/"
        "serviceAccountLastAuthentication/activities:query"
        "?filter={filter}&pageSize={page_size}"
    ),
}

FORBIDDEN_STATUS = 403
NOT_FOUND_STATUS = 404
RATE_LIMIT_STATUS = 429

MAX_ACTIVITIES_LIMIT = 1000
MIN_ACTIVITIES_LIMIT = 1
DEFAULT_LOCATION_ID = "global"
