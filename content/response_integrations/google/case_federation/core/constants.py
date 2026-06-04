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
INTEGRATION_NAME = "CaseFederation"

PING_SCRIPT_NAME = "Ping"
FEDERATION_SYNC_JOB_SCRIPT_NAME = "SyncJob"

FEDERATION_BASE_ENDPOINT_TEMPLATE: str = "{api_root}/external/v1/federation/cases"
FEDERATION_SYNC_ENDPOINT_TEMPLATE = FEDERATION_BASE_ENDPOINT_TEMPLATE + "/batch-patch"
FEDERATION_FETCH_ENDPOINT_TEMPLATE = FEDERATION_BASE_ENDPOINT_TEMPLATE

SUCCESS_STATUS_CODE = 200
