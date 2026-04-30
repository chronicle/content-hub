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

from .action_param_mappers import non_empty, parse_bool, required

INTEGRATION_NAME = "CloudIdentity"
INTEGRATION_DISPLAY_NAME = "Cloud Identity"
INTEGRATION_PARAM_MAPPERS = {
    "Service Account JSON File Content": [],
    "Verify SSL": [parse_bool()],
    "Workload Identity Email": [],
    "Delegated Email": [required(), non_empty()],
}

DEFAULT_API_ROOT = "https://cloudidentity.googleapis.com"
ADMIN_SDK_API_ROOT = "https://admin.googleapis.com"
DEFAULT_V1_VERSION = "v1"
BETA_V1_VERSION = "v1beta1"

OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/cloud-identity.policies",
    "https://www.googleapis.com/auth/admin.directory.orgunit",
]

MY_CUSTOMER = "my_customer"
