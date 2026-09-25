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

import re
from typing import TypeAlias

# Integration identifier
INTEGRATION_IDENTIFIER: str = "AkeylessSecurity"
INTEGRATION_NAME: str = "Akeyless Security"

# Script names
PING_SCRIPT_NAME: str = "Ping"
GET_SECRET_VALUE_SCRIPT_NAME: str = "Get Secret Value"  # ruff:ignore[hardcoded-password-string]
SYNC_CREDENTIALS_JOB_SCRIPT_NAME: str = "Sync Integration Credentials Job"
SYNC_CREDENTIAL_JOB_SCRIPT_NAME: str = SYNC_CREDENTIALS_JOB_SCRIPT_NAME
RESOURCE_NAME_PATTERN: re.Pattern = re.compile(
    r"^(?P<secret>[^:\s][^:]*)(?::(?P<version>latest|[1-9]\d*))?$"
)

# Integration configuration parameter names
ACCESS_ID_PARAM: str = "Access ID"
ACCESS_KEY_PARAM: str = "Access Key"
API_GATEWAY_URL_PARAM: str = "API Gateway URL"
VERIFY_SSL_PARAM: str = "Verify SSL"

# Action parameter names
SECRET_NAME_PARAM: str = "Secret Name"  # ruff:ignore[hardcoded-password-string]

# Akeyless API defaults
DEFAULT_API_GATEWAY_URL: str = "https://api.akeyless.io"
DEFAULT_SECRET_VERSION: str = "latest"  # ruff:ignore[hardcoded-password-string]
DEFAULT_MAX_RETRIES: int = 0

# Authentication mechanisms
ACCESS_KEY_TYPE: str = "access_key"

# Masking configurations
MIN_MASK_LENGTH: int = 6

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
NameIdentifierMap: TypeAlias = dict[str, str]  # display_name → identifier
