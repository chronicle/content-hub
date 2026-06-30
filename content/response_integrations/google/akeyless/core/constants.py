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

"""Constants for the Akeyless integration."""

from __future__ import annotations

from typing import TypeAlias

# Integration identifier
INTEGRATION_IDENTIFIER: str = "Akeyless"
INTEGRATION_NAME: str = "Akeyless"

# Script names
PING_SCRIPT_NAME: str = "Ping"
SYNC_CREDENTIAL_JOB_SCRIPT_NAME: str = "Sync Integration Credential Job"

# Integration configuration parameter names
ACCESS_ID_PARAM: str = "Access ID"
ACCESS_KEY_PARAM: str = "Access Key"
ACCESS_TYPE_PARAM: str = "Access Type"
API_GATEWAY_URL_PARAM: str = "API Gateway URL"
VERIFY_SSL_PARAM: str = "Verify SSL"

# Akeyless API defaults
DEFAULT_SECRET_VERSION: str = "latest"  # noqa: S105
TOKEN_TTL_SECONDS: int = 50 * 60  # 50 minutes (conservative buffer under 60-min default)

# Authentication mechanisms
GCP_ACCESS_TYPE: str = "gcp"
ACCESS_KEY_TYPE: str = "access_key"

# GCP Metadata Service configuration
GCP_METADATA_URL_TEMPLATE: str = (
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience={audience}"
)
GCP_METADATA_HEADER_NAME: str = "Metadata-Flavor"
GCP_METADATA_HEADER_VALUE: str = "Google"
GCP_METADATA_TIMEOUT_SECONDS: int = 3

# Masking configurations
MIN_MASK_LENGTH: int = 6

# Job state context keys
SYNC_CREDENTIALS_STATE_KEY: str = "sync_credentials_state"

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

# Type aliases
SecretCacheKey: TypeAlias = tuple[str, str]  # (secret_id, version_id)
StateContext: TypeAlias = dict[str, str]  # state_key → state_val
NameIdentifierMap: TypeAlias = dict[str, str]  # display_name → identifier
