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
REMOTE_PLATFORM_BACKSTORY_REDIRECT_HEADER: str = "REMOTE-PLATFORM-BACKSTORY-REDIRECT"
CLIENT_ADDRESS_ENV_VAR: str = "CLIENT_ADDRESS"

SUCCESS_STATUS_CODE: int = 200

LAST_EXECUTION_DATA_KEY: str = "lastExecutionData"
HAS_FAILED_KEY: str = "hasFailed"
TARGET_PLATFORM_NOT_PROVIDED_ERROR_MESSAGE: str = "Target Platform must be provided"
