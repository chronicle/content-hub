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
INTEGRATION_NAME = "SCCM"
PING_ACTION = f"{INTEGRATION_NAME} - Ping"
GET_LOGIN_HISTORY_ACTION = f"{INTEGRATION_NAME} - Get Login History"
GET_COMPUTER_PROPERTIES_ACTION = f"{INTEGRATION_NAME} - Get Computer Properties"
ENRICH_ENTITIES_ACTION = f"{INTEGRATION_NAME} - Enrich Entities"
RUN_WQL_QUERY_ACTION = f"{INTEGRATION_NAME} - Run WQL Query"

DOMAIN_USER = r"{domain}\{username}"
ENRICH_PREFIX = "SCCM"
