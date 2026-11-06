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
INTEGRATION_NAME = "AzureADIdentityProtection"
INTEGRATION_DISPLAY_NAME = "Azure AD Identity Protection"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
ENRICH_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Enrich Entities"
UPDATE_USER_STATE_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Update User State"

ENDPOINTS = {
    "ping": "/v1.0/identityProtection/riskDetections?top=1",
    "get_alerts": "/v1.0/identityProtection/riskDetections",
    "get_users": "/v1.0/identityProtection/riskyUsers/",
    "compromise": "/v1.0/identityProtection/riskyUsers/confirmCompromised",
    "dismiss": "/v1.0/identityProtection/riskyUsers/dismiss",
}
AUTH_TOKEN_PATH = "/oauth2/v2.0/token"

PRINCIPAL_NAME = "userPrincipalName"
DISPLAY_NAME = "userDisplayName"
RISK_COLOR_MAP = {
    "No Risk": "#339966",
    "Low": "#ffff00",
    "Medium": "#ff9900",
    "High": "#ff0000",
}
COMPROMISED_STATE = "Compromised"

# Connector
CONNECTOR_NAME = f"{INTEGRATION_DISPLAY_NAME} - Risk Detections Connector"
DEFAULT_TIME_FRAME = 1
DEFAULT_LIMIT = 100
DEVICE_VENDOR = "Microsoft Azure"
DEVICE_PRODUCT = "Azure AD Identity Protection"
API_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
RISK_DETECTION_ID_FIELD = "id"

SEVERITY_MAP = {"low": 40, "medium": 60, "high": 80}

SEVERITIES = ["low", "medium", "high"]

DEFAULT_API_ROOT = "https://graph.microsoft.com"
LOGIN_API_ROOT_DEFAULT = "https://login.microsoftonline.com"
