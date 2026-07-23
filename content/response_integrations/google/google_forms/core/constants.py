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


INTEGRATION_NAME: str = "Google Forms"

PING_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Ping"
RESPONSE_CONNECTOR_NAME: str = f"{INTEGRATION_NAME} - Responses Connector"

API_ROOT: str = "https://www.googleapis.com"
CONNECTOR_API_ROOT: str = "https://forms.googleapis.com"

ENDPOINTS: dict[str, str] = {"list-users": "/admin/directory/v1/users"}
CONNECTOR_ENDPOINTS: dict[str, str] = {
    "get_form": "/v1/forms/{form_Id}/responses",
    "get_form_details": "/v1/forms/{form_Id}",
}

OAUTH_SCOPES: list[str] = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/admin.directory.user",
    "https://www.googleapis.com/auth/admin.directory.group.member",
    "https://www.googleapis.com/auth/admin.directory.customer.readonly",
    "https://www.googleapis.com/auth/admin.directory.domain.readonly",
    "https://www.googleapis.com/auth/admin.directory.group",
    "https://www.googleapis.com/auth/admin.directory.orgunit",
    "https://www.googleapis.com/auth/admin.directory.user.alias",
    "https://www.googleapis.com/auth/admin.directory.rolemanagement.readonly",
    "https://www.googleapis.com/auth/apps.groups.settings",
    "https://www.googleapis.com/auth/forms.responses.readonly",
    "https://www.googleapis.com/auth/forms.body.readonly",
]
API_BAD_REQUEST_STATUS_CODE: int = 400
ALLOWED_SEVERITIES: list[str] = ["Informational", "Low", "Medium", "High", "Critical"]
PAGESIZE: int = 100
SEC_IN_MS: int = 1000
HOUR_IN_SEC: int = 3600
DEVICE_VENDOR: str = "Google Forms"
DEVICE_PRODUCT: str = "Google Forms"
