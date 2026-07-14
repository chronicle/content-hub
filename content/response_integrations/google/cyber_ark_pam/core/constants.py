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

INTEGRATION_NAME: str = "CyberArk PAM"

CA_CERT_PATH: str = "cacert.pem"
URLS: dict[str, str] = {
    "get_access_token": "/PasswordVault/API/Auth/CyberArk/Logon",
    "list_accounts": "PasswordVault/API/Accounts",
    "get_password": "PasswordVault/API/Accounts/{account_id}/Password/Retrieve/",
    "change_password": "PasswordVault/API/Accounts/{account_id}/Change",
}
MAX_RETRIES: int = 1
GET_TOKEN_TIMEOUT: int = 60
MIN_MASK_LENGTH: int = 6

ACCOUNTS_PATTERN: re.Pattern = re.compile(
    r"^accounts/(?P<account>[^/]+)(?:/versions/(?P<version>\d+))?$"
)

ANY_INTEGRATION_FILTER_VALUE: str = "-"
ASYNC_SEMAPHORE_LIMIT: int = 10
CONNECTORS_KEY: str = "connectors"
INTEGRATION_INSTANCES_KEY: str = "integration_instances"
JOBS_KEY: str = "jobs"
TIMEOUT_THRESHOLD_MS: int = 1000 * 540
SYNC_CREDENTIAL_JOB_SCRIPT_NAME: str = "Sync Integration Credential Job"
