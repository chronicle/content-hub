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
PROVIDER_NAME = "Cisco Orbital"

ENDPOINTS = {
    "generate_token": "v0/oauth2/token",
    "test_connectivity": "v0/ok",
    "submit_query": "v0/query",
    "get_results": "v0/jobs/{job_id}/results",
}

# Actions
PING_SCRIPT_NAME = f"{PROVIDER_NAME} - Ping"
EXECUTE_QUERY_SCRIPT_NAME = f"{PROVIDER_NAME} - Execute Query"


MAX_EXPIRATION_IN_HOURS = 24
MIN_EXPIRATION_IN_MINUTES = 1
ASYNC_ACTION_TIMEOUT_THRESHOLD_MS = 40 * 1000
IPV4_TYPE = "ipv4"
IPV6_TYPE = "ipv6"
NAME_DEFAULT_STRUCTURE = "Siemplify-{}"
