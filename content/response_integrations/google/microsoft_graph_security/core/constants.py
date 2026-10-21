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
INTEGRATION_NAME = "MicrosoftGraphSecurity"
VENDOR = "Microsoft Graph Security"
DEVICE_PRODUCT = "AlertV2"
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
GET_ADMINISTRATOR_CONSENT_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Get Administrator Consent"
)
GET_ALERT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Alert"
KILL_USER_SESSION = f"{INTEGRATION_NAME} - Kill User Session"
LIST_ALERTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Alerts"
LIST_INCIDENTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Incidents"
GET_INCIDENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Incident"
UPDATE_ALERT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Alert"
ADD_ALERT_COMMENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Alert Comment"
API_COMMENT_LIMITATION = 1000
DEFAULT_MAX_RECORDS = 50
DEFAULT_API_PAGINATION_LIMIT = 200
ALERT_ID_FIELD = "id"

GRANT_TYPE = "client_credentials"
CLIENT_ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"

DEFAULT_API_ROOT = "https://graph.microsoft.com"
DEFAULT_LOGIN_API_ROOT = "https://login.microsoftonline.com"

# url paths and templates
AUTH_TOKEN_PATH = "{tenant}/oauth2/v2.0/token"
ADMIN_CONSENT_PATH = (
    "{tenant}/adminconsent?client_id={client_id}&redirect_uri={redirect_uri}"
)
GET_ALERT_PATH = "v1.0/security/alerts"
GET_ALERT_V2_PATH = "v1.0/security/alerts_v2"
GET_INCIDENTS_PATH = "v1.0/security/incidents"
GET_USERS_PATH = "v1.0/users"
KILL_USER_PATH = "v1.0/users/{}/revokeSignInSessions"
ADD_ALERT_COMMENT_PATH = "v1.0/security/alerts_v2/{}/comments"
GET_INCIDENT_PATH = "v1.0/security/incidents/{incident_id}"

TOKEN_PAYLOAD = {
    "client_id": None,
    "scope": None,
    "client_secret": None,
    "grant_type": "client_credentials",
}
UPDATE_ALERT_HEADER = {"Prefer": "return=representation"}
FEEDBACK_VALUES = ["unknown", "truePositive", "falsePositive", "benignPositive"]
CLASSIFICATION_VALUES = [
    "unknown",
    "falsePositive",
    "truePositive",
    "informationalExpectedActivity",
    "unknownFutureValue",
]
STATUS_VALUES = ["unknown", "newAlert", "inProgress", "resolved"]
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

SEVERITY_MAP = {"high": 80, "medium": 60, "low": 40, "informational": -1, "unknown": -1}
VALID_ALERT_STATUSES = ["unknown", "newAlert", "inProgress", "resolved"]
VALID_ALERT_FEEDBACKS = ["unknown", "truePositive", "falsePositive", "benignPositive"]
VALID_ALERT_COMMENTS = ["Closed in IPC", "Closed in MCAS"]
EVENT_STATES = [
    "fileStates",
    "hostStates",
    "malwareStates",
    "networkConnections",
    "registryKeyStates",
    "triggers",
    "userStates",
    "vulnerabilityStates",
    "cloudAppStates",
    "processes",
    "alertDetections",
    "historyStates",
    "investigationSecurityStates",
    "messageSecurityStates",
    "securityResources",
    "uriClickSecurityStates",
]
CONTAINS_FILTER_NOT_SUPPORTED_ERROR = (
    "no function signature for the function with name 'contains' "
    "matches the specified arguments."
)
