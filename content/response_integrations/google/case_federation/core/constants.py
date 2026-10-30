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

INTEGRATION_NAME: str = "CaseFederation"

PING_SCRIPT_NAME: str = "Ping"
FEDERATION_SYNC_JOB_SCRIPT_NAME: str = "SyncJob"

BATCH_PATCH_FEDERATED_CASES_ENDPOINT_SUFFIX: str = "/legacyFederatedCases:legacyBatchPatchFederatedCases"
CHRONICLE_API_URL_PATH_REGEX: str = r"^/(?:v\d+[a-z0-9]*/)?projects/[^/]+/locations/[^/]+/instances/[^/]+/?$"
V1ALPHA_PROJECTS_PATH_SEGMENT: str = "/v1alpha/projects/"
VERSIONED_PROJECTS_PATH_REGEX: str = r"/(?:v\d+[a-z0-9]*/)?projects/"
REMOTE_PLATFORM_BACKSTORY_REDIRECT_HEADER: str = "REMOTE-PLATFORM-BACKSTORY-REDIRECT"
CLIENT_ADDRESS_ENV_VAR: str = "CLIENT_ADDRESS"
CLIENT_ADDRESS_NOT_FOUND_ERROR_MESSAGE: str = f"Environment {CLIENT_ADDRESS_ENV_VAR} not found"
GCP_PROJECT_ID_ENV_VAR: str = "GCP_PROJECT_ID"

SUCCESS_STATUS_CODE: int = 200

LAST_EXECUTION_DATA_KEY: str = "lastExecutionData"
HAS_FAILED_KEY: str = "hasFailed"
MISSING_PARAMETERS_ERROR_MESSAGE: str = "Chronicle API URL or both Target Platform and API Key must be provided"
INVALID_CHRONICLE_API_URL_ERROR_MESSAGE: str = (
    "Chronicle API URL must be the Chronicle API URL of the primary platform, for example "
    "https://<region>-chronicle.googleapis.com/projects/<project>/locations/<location>/instances/<instance>"
)
CREDENTIALS_REFRESH_ERROR_MESSAGE: str = (
    "Failed to refresh SIEM service account credentials; verify the runtime identity has permission "
    "to impersonate the SIEM service account"
)
SYNC_REQUEST_ERROR_MESSAGE: str = "Failed to send case federation sync request to target platform"
