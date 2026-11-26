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
INTEGRATION_NAME = "RSANetWitnessEDR"
PING_ACTION = f"{INTEGRATION_NAME} - Ping"
ADDIPTOBLOCKLIST_ACTION = f"{INTEGRATION_NAME} - Add IP To Blacklist"
ADDURLTOBLOCKLIST_ACTION = f"{INTEGRATION_NAME} - Add URL To Blacklist"
ENRICHENDPOINT_ACTION = f"{INTEGRATION_NAME} - Enrich Endpoint"
GET_IOC_DETAILS_ACTION = f"{INTEGRATION_NAME} - Get IOC Details"

# Headers.
REQUEST_HEADERS = {"Accept": "application/json"}
# UI_SESSION_HEADERS = {"NetWitness-Token": "", "Content-Type": "application/x-www-form-urlencoded"}

# Endpoints
PING_QUERY = "api/v2/health"
ADD_IP_TO_BLOCKLIST = "api/v2/blacklist/ip?format=json"
ADD_URL_TO_BLOCKLIST = "api/v2/blacklist/domain?format=json"
GET_ENDPOINT_IP_GUID = "api/v2/machines?IpAddress={}&format=json"
GET_ENDPOINT_HOSTNAME_GUID = "api/v2/machines?MachineName={}&format=json"
GET_ENDPOINT_DETAILS = "api/v2/machines/{}?format=json"
GET_ENDPOINT_IOCS = "api/v2/machines/{}/instantiocs?per_page={}&format=json"
GET_IOC_DETAIL = "api/v2/instantiocs/{}?format=json"

ENRICHMENT_PREFIX = "RSA_EDR"

IOC_LEVEL_THRESHOLD = {"Low": 3, "Medium": 2, "High": 1, "Critical": 0}
