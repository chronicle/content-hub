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
INTEGRATION_NAME = "Microsoft365Defender"
INTEGRATION_DISPLAY_NAME = "Microsoft 365 Defender"

# Actions
ADD_COMMENT_TO_INCIDENT_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Add Comment To Incident"
)
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
UPDATE_INCIDENT_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Update Incident"
EXECUTE_QUERY_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Execute Query"
EXECUTE_ENTITY_QUERY_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Execute Entity Query"
EXECUTE_CUSTOM_QUERY_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Execute Custom Query"

API_ROOT = "https://api.security.microsoft.com"
LOGIN_API_ROOT_DEFAULT = "https://login.microsoftonline.com"
GRAPH_API_ROOT_DEFAULT = "https://graph.microsoft.com"
CUSTOM_ACCESS_TOKEN_URL = "{login_api_root}/{tenant_id}/oauth2/v2.0/token"
PREFER_HEADER_FOR_CONNECTOR: str = "include-unknown-enum-members"

ENDPOINTS = {
    "login": "/{tenant_id}/oauth2/v2.0/token",
    "list_incidents": "/api/incidents",
    "list_incidents_graph": "/v1.0/security/incidents",
    "update_incident": "/v1.0/security/incidents/{incident_id}",
    "add_comment_incident": "/v1.0/security/incidents/{incident_id}/comments",
    "execute_query": "/api/advancedhunting/run",
    "execute_query_graph": "/beta/security/runHuntingQuery",
    "get_alerts": "/v1.0/security/alerts_V2",
    "update_alert": "/v1.0/security/alerts_v2/{alert_id}",
    "add_comment_to_alert": "/v1.0/security/alerts_v2/{alert_id}/comments",
}

FILTER_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

# Connector
CONNECTOR_NAME = f"{INTEGRATION_DISPLAY_NAME} - Incidents Connector"
DEFAULT_TIME_FRAME = 1
DEFAULT_LIMIT = 10
DEFAULT_MAX_LIMIT = 20
DEFAULT_FETCH_INTERVAL = 6
INCIDENTS_LIMIT_PER_REQUEST = 50
ALERTS_LIMIT_PER_REQUEST = 250
DEVICE_VENDOR = "Microsoft"
DEVICE_PRODUCT = "Microsoft 365 Defender"
DEFAULT_CLASSIFICATION = "Unknown"

SEVERITY_MAP = {"Informational": -1, "Low": 40, "Medium": 60, "High": 80}

SEVERITIES = ["informational", "low", "medium", "high"]

ENTITIES_KEY = "entities"
DEVICES_KEY = "devices"

EMPTY_DROPDOWN_VALUE = "Select One"

CLASSIFICATION_MAPPING = {
    "False Positive": "falsePositive",
    "True Positive": "truePositive",
}

DETERMINATION_MAPPING = {
    "Not Available": "unknown",
    "Apt": "apt",
    "Malware": "malware",
    "Security Personnel": "securityPersonnel",
    "Security Testing": "securityTesting",
    "Unwanted Software": "unwantedSoftware",
    "Other": "other",
}

TIMEFRAME_MAPPING = {
    "Last Hour": {"hours": 1},
    "Last 6 Hours": {"hours": 6},
    "Last 24 Hours": {"hours": 24},
    "Last Week": "last_week",
    "Last Month": "last_month",
    "Custom": "custom",
}

DEFAULT_RESULTS_LIMIT = 50
OR_OPERATOR = "OR"
AND_OPERATOR = "AND"
ALERT_ID_KEY = "alert_id"
ALERT_UNIQUE_ID_KEY = "alert_unique_id"

LIMIT_OF_INCIDENTS_TO_STORE = 1000
MAX_EVIDENCES_PER_ALERT = 500
PADDING_PERIOD_IN_MINUTES = 5
DEFAULT_INCIDENT_STATUS_FILTER = "Active, In Progress"
POSSIBLE_STATUSES = {"Active", "In Progress", "Resolved", "Redirected"}
GRAPH_API_SCOPE = "https://graph.microsoft.com/.default"
TOO_MANY_REQUEST_TIMEOUT = 90 * 1000
FETCHING_TIMEOUT_TRESHOLD = 0.8

INCIDENT_NAME_FILTER = "incident name"
ALERT_NAME_FILTER = "alert name"
ALERT_KEYS_TO_IGNORE = [
    "assignedTo",
    "status",
    "comments",
    "systemTags",
    "remediationStatus",
    "remediationStatusDetails",
    "verdict",
    "tags",
    "classification",
    "description",
    "determination",
    "title",
    "severity",
    "alertWebUrl",
    "incidentWebUrl",
    "category",
    "categories",
    "investigationState",
    "recommendedActions",
]
ALERT_KEYS_DATETIME_SUFFIX = "time"
ADDITIONAL_DATA_ALLOWLIST = frozenset([
    "OriginalAlertProductName",
    "OriginalAlertProviderName",
    "OriginatingAlertSource",
    "Trigger Operator",
    "Trigger Threshold",
    "Correlation Id",
    "Search Query Results Overall Count",
    "Data Sources",
    "Analytic Rule Ids",
    "Event Grouping",
    "Analytic Rule Name",
    "ProcessedBySentinel",
    "Alert generation status",
    "SystemAlertId",
    "Query Start Time UTC",
    "Query End Time UTC",
    "Query Period",
    "AlertType",
    "WorkspaceName",
    "Query",
    "WorkspaceId",
    "AlertPolicyTitle",
    "Intent@odata.type",
    "Intent",
])

# Jobs
SYNC_ALERTS_SCRIPT_NAME: str = f"{INTEGRATION_DISPLAY_NAME} - Sync Alerts"
SYNC_ALERTS_IDENTIFIER: str = "Microsoft365Defender_SyncAlerts"
INCIDENT_IDS_FILE_NAME: str = "sync_alerts_ids.json"
INCIDENT_IDS_DB_KEY: str = "microsoft365defender_alert_sync_map"
SYNC_ALERTS_TIMEOUT_IN_MILLISECONDS: int = 600 * 1000
M365_DEFENDER_ALERT_TAG: str = "Microsoft Defender XDR Alert"
INCIDENT_STATUS_RESOLVED: str = "Resolved"
REASON_MALICIOUS: str = "Malicious"
CLASSIFICATION_TRUE_POSITIVE: str = "truePositive"
REASON_NOT_MALICIOUS: str = "NotMalicious"
CLASSIFICATION_FALSE_POSITIVE: str = "falsePositive"
CLASSIFICATION_OTHER: str = "unknownFutureValue"
REASON_RESOLVED: str = "Inconclusive"
ROOT_CAUSE_OTHER: str = "Other"
M365_COMMENT_PREFIX: str = "Microsoft Defender XDR Alert "
SECOPS_COMMENT_PREFIX: str = "Google SecOps "
COMMENTS_MODIFICATION_TIME_FILTER: int = 1
CASES_SYNC_LIMIT: int = 10
SECOPS_TAG_PREFIX: str = "Google SecOps: "
ENTITY_TYPE: int = 2
M365_INCIDENT_ID_CONTEXT_KEY: str = "Alert_ID"
DETERMINATION_MALICIOUS: str = "Malicious"
DETERMINATION_NOT_MALICIOUS: str = "NotMalicious"
DETERMINATION_INFORMATIONAL: str = "InformationalExpectedActivity"

# Sync Job Generic Constants
M365_STATUS_RESOLVED: str = "resolved"

# Retry mechanism
RETRY_SLEEP = 60  # seconds
MAX_CHARS: int = 900
DEFAULT_CASE_TIME: int = 0
HTTP_NOT_FOUND_STATUS_CODE: int = 404
REDIRECTED_TAG: str = "redirected"
DEFENDER_SCOPE_TEMPLATE = "{api_root}/.default"
GRAPH_API_SCOPE_TEMPLATE = "{graph_api_root}/.default"

DEFAULT_SYNC_DIRECTION_JSON: str = (
    '{"Status": "Bidirectional", "Comments": "Bidirectional"}'
)
DEFAULT_CLOSED_REASON_MAPPING_JSON: str = (
    '{"{reason} | {root cause}": '
    '{"classification": "unknownFutureValue", "determination": "other"}, '
    '"Malicious": '
    '{"classification": "truePositive", "determination": "maliciousUserActivity"}, '
    '"NotMalicious": '
    '{"classification": "falsePositive", "determination": "notMalicious"}, '
    '"Fallback": '
    '{"classification": "unknownFutureValue", "determination": "other"}}'
)

CLASSIFICATION_MAP: dict[str, str] = {
    "truepositive": "truePositive",
    "falsepositive": "falsePositive",
    "informationalexpectedactivity": "informationalExpectedActivity",
    "unknown": "unknownFutureValue",
    "unclassified": "unknownFutureValue",
    "unknownfuturevalue": "unknownFutureValue",
}

DETERMINATION_MAP: dict[str, str] = {
    "multistagedattack": "multiStagedAttack",
    "malware": "malware",
    "malicioususeractivity": "maliciousUserActivity",
    "unwantedsoftware": "unwantedSoftware",
    "phishing": "phishing",
    "compromisedaccount": "compromisedAccount",
    "other": "other",
    "securitytesting": "securityTesting",
    "confirmedactivity": "confirmedActivity",
    "lineofbusinessapplication": "lineOfBusinessApplication",
    "notmalicious": "notMalicious",
    "notenoughdatatovalidate": "notEnoughDataToValidate",
}
