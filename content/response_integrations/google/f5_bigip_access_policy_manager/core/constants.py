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
INTEGRATION_NAME = "F5BIGIPAccessPolicyManager"
INTEGRATION_DISPLAY_NAME = "F5 BIG-IP Access Policy Manager"

PING_ACTION = f"{INTEGRATION_DISPLAY_NAME} - Ping"
LIST_ACTIVE_SESSIONS_ACTION = f"{INTEGRATION_DISPLAY_NAME} - List Active Sessions"
DISCONNECT_SESSIONS_ACTION = f"{INTEGRATION_DISPLAY_NAME} - Disconnect Sessions"

TOKEN_FILE_PATH = "token.txt"
DEFAULT_ENCODING = "utf-8"

# ENDPOINTS
LOGIN_QUERY = "{}/mgmt/shared/authn/login"
UPDATE_TIMEOUT_QUERY = "{}/mgmt/shared/authz/tokens/{}"
PING_QUERY = "{}/mgmt/shared/authz/tokens"
LIST_ACTIVE_SESSIONS_QUERY = "{}/mgmt/tm/apm/access-info?$top={}"
DISCONNECT_SESSIONS_GET_QUERY = "{}/mgmt/tm/apm/access-info"
DISCONNECT_SESSIONS_DELETE_QUERY = "{}/mgmt/tm/apm/session/{}"
