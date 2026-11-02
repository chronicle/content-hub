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
PROVIDER_NAME = "PaloAltoPrismaCloud"
INTEGRATION_NAME = "PaloAltoPrismaCloud"
INTEGRATION_DISPLAY_NAME = "Palo Alto Prisma Cloud"
# ACTION NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
ENRICH_ASSETS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich Assets"
ALERTS_CONNECTOR_NAME = "Palo Alto Prisma Cloud - Alerts Connector"
RESPOND_TO_ALERT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Respond To Alert"

# ENDPOINTS
ENDPOINTS = {
    "login": "login",
    "ping": "v2/alert",
    "enrich_assets": "uai/v1/asset",
    "alert": "alert/",
    "Dismiss": "alert/dismiss",
    "Snooze": "alert/dismiss",
    "Remediate": "alert/remediation/",
    "Reopen": "alert/reopen",
}
RESPONSE_TYPE = ["select one", "Dismiss", "Snooze", "Reopen", "Remediate"]
HEADERS = {
    "Accept": "application/json; charset=UTF-8",
    "Content-type": "application/json; charset=UTF-8",
}

ITEM_NOT_FOUND = 404
API_BAD_REQUEST = 400
METHOD_NOT_ALLOWED = 406
PAGESIZE = 100

DEFAULT_MAX_LIMIT = 100
DEVICE_VENDOR = "Palo Alto Prisma Cloud"
DEVICE_PRODUCT = "Prisma Cloud"
SOURCE_GROUPING_IDENTIFIER = "saveSearchId"

MAX_ACTIVITIES_LIMIT = 1000
MIN_ACTIVITIES_LIMIT = 1

SEC_IN_MS = 1000
HOUR_IN_SEC = 3600

GRANT_TYPE = "client_credentials"
SCOPE = "https://api3.prismacloud.io"

TOKEN_PAYLOAD_FROM_SECRET = {"username": "", "password": ""}

ALERTS_CONNECTOR_SEVERITY_MAPPING = {
    "critical": 80,
    "high": 60,
    "medium": 40,
    "low": 20,
    "info": 0,
    "informational": 0,
}

SEVERITY_LEVELS = ["critical", "high", "medium", "low", "informational"]
DEFAULT_RESPONSE_TYPE = "Select One"
