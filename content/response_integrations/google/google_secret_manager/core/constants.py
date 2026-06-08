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

"""Constants for the Google Secret Manager integration."""

# Integration identifier
INTEGRATION_IDENTIFIER: str = "GoogleSecretManager"
INTEGRATION_NAME: str = "Google Secret Manager"

# Script names
PING_SCRIPT_NAME: str = "Ping"
SYNC_CREDENTIAL_JOB_SCRIPT_NAME: str = "Sync Integration Credential Job"

# Integration configuration parameter names
SERVICE_ACCOUNT_JSON_PARAM: str = "Service Account JSON"
PROJECT_ID_PARAM: str = "Project ID"
WORKLOAD_IDENTITY_EMAIL_PARAM: str = "Workload Identity Email"
VERIFY_SSL_PARAM: str = "Verify SSL"

# Secret Manager API defaults
DEFAULT_SECRET_VERSION: str = "latest"  # noqa: S105
SECRET_MANAGER_API_BASE: str = "https://secretmanager.googleapis.com/v1"  # noqa: S105
SECRET_MANAGER_SCOPE: str = "https://www.googleapis.com/auth/cloud-platform"  # noqa: S105

# Job parameter names
ENVIRONMENT_NAME_PARAM: str = "Environment Name"
CREDENTIAL_MAPPING_PARAM: str = "Credential Mapping"

# Credential mapping JSON keys
INTEGRATION_INSTANCES_KEY: str = "integration_instances"
CONNECTORS_KEY: str = "connectors"
JOBS_KEY: str = "jobs"

# API Filter Values
ANY_INTEGRATION_FILTER_VALUE: str = "-"

# Async concurrency control
ASYNC_SEMAPHORE_LIMIT: int = 10
TIMEOUT_THRESHOLD_MS: int = 1000 * 540

# Masking configurations
MIN_MASK_LENGTH: int = 6
