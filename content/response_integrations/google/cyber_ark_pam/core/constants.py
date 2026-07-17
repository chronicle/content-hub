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

import re

# Integration identifier
INTEGRATION_NAME: str = "CyberArk PAM"

# Manager configuration
CA_CERT_PATH: str = "cacert.pem"
URLS: dict[str, str] = {
    "logon": "/PasswordVault/API/Auth/CyberArk/Logon",
    "list_accounts": "PasswordVault/API/Accounts",
    "get_password": "PasswordVault/API/Accounts/{account_id}/Password/Retrieve/",
    "change_password": "PasswordVault/API/Accounts/{account_id}/Change",
    "get_secret_versions": "PasswordVault/API/Accounts/{account_id}/Secret/Versions",
}
MAX_RETRIES: int = 1
AUTHENTICATION_TIMEOUT: int = 60
HTTP_STATUS_BAD_REQUEST: int = 400
HTTP_STATUS_NOT_FOUND: int = 404

# Masking configurations
MIN_MASK_LENGTH: int = 6

# Sync Credential Job constants
ACCOUNTS_PATTERN: re.Pattern = re.compile(r"^accounts/(?P<account>[^/]+)(?:/versions/(?P<version>\d+))?$")
SYNC_CREDENTIAL_JOB_SCRIPT_NAME: str = "Sync Integration Credential Job"

# Credential mapping JSON keys
INTEGRATION_INSTANCES_KEY: str = "integration_instances"
CONNECTORS_KEY: str = "connectors"
JOBS_KEY: str = "jobs"

# API filter values
ANY_INTEGRATION_FILTER_VALUE: str = "-"

# Async concurrency control
ASYNC_SEMAPHORE_LIMIT: int = 10
TIMEOUT_THRESHOLD_MS: int = 1000 * 540
