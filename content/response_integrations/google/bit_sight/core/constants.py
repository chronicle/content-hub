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
INTEGRATION_NAME = "BitSight"
INTEGRATION_DISPLAY_NAME = "BitSight"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
LIST_COMPANY_VULNERABILITIES_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - List Company Vulnerabilities"
)
LIST_COMPANY_HIGHLIGHTS_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - List Company Highlights"
)
GET_COMPANY_DETAILS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Get Company Details"

ENDPOINTS = {
    "ping": "/",
    "get_alerts": "/ratings/v2/alerts",
    "get_findings": "/v1/companies/{company_id}/findings",
    "get_companies": "/v1/companies",
    "get_company_vulnerabilities": "/v1/companies/{company_id}/findings/summary",
    "get_company_highlights": "/ratings/v1/insights",
    "get_company_details": "/v1/companies/{company_id}",
}

# Connector
CONNECTOR_NAME = f"{INTEGRATION_DISPLAY_NAME} - Alerts Connector"
DEFAULT_TIME_FRAME = 1
DEFAULT_LIMIT = 20
DEFAULT_MAX_LIMIT = 100
DEVICE_VENDOR = "BitSight"
DEVICE_PRODUCT = "BitSight"
WHITELIST_FILTER = 1
BLACKLIST_FILTER = 2
POSSIBLE_SEVERITIES = ["informational", "increase", "warn", "critical"]
SEVERITY_MAPPING = {"CRITICAL": 100, "WARN": 80, "INCREASE": 40, "INFORMATIONAL": -1}

TIME_FORMAT = "%Y-%m-%d"
DEFAULT_VULNERABILITIES_LIMIT = 50
DEFAULT_HIGHLIGHTS_LIMIT = 20

TIMEFRAME_MAPPING = {
    "Last Week": "last_week",
    "Last Month": "last_month",
    "Custom": "custom",
}

NOW = "now"
