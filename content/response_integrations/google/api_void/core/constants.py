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
INTEGRATION_NAME = "APIVoid"

# ACTION_NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
GET_DOMAIN_REPUTATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Domain Reputation"
GET_IP_REPUTATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Ip Reputation"
GET_SCREENSHOT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Screenshot"
GET_URL_REPUTATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Url Reputation"
VERIFY_EMAIL_SCRIPT_NAME = f"{INTEGRATION_NAME} - Verify Email"

# Constants
INSIGHT_MSG = "Country: {0}"
LIMIT_EXCEEDED = "you have 0 credits remained"
