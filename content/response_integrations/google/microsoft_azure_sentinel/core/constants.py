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
INTEGRATION_NAME = "MicrosoftAzureSentinel"
PRODUCT_NAME = "Microsoft Azure Sentinel"


# ACTIONS NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
LIST_INCIDENTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Incidents"
UPDATE_INCIDENT_DETAILS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Incident Details"
GET_ALERT_RULE_DETAILS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Alert Rule Details"
UPDATE_INCIDENT_LABELS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Incident Labels"
GET_INCIDENT_STATISTICS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Incident Statistics"
LIST_CUSTOM_HUNTING_RULES_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - List Custom Hunting Rules"
)
GET_CUSTOM_HUNTING_RULE_DETAILS_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Get Custom Hunting Rule"
)
CREATE_CUSTOM_HUNTING_RULES_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Create Custom Hunting Rule"
)
DELETE_CUSTOM_HUNTING_RULES_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Delete Custom Hunting Rule"
)
UPDATE_CUSTOM_HUNTING_RULES_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Update Custom Hunting Rule"
)
LIST_ALERT_RULES_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Alert Rules"
CREATE_ALERT_RULE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create Alert Rule"
DELETE_ALERT_RULE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Delete Alert Rule"
UPDATE_ALERT_RULE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Alert Rule"
RUN_KQL_QUERY_SCRIPT_NAME = f"{INTEGRATION_NAME} - Run KQL Query"
RUN_CUSTOM_HUNTING_RULE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Run Custom Hunting Rule"
ADD_COMMENT_TO_INCIDENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Comment to Incident"
UPDATE_INCIDENT_DETAILS_V2_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Update Incident Details v2"
)
UPDATE_INCIDENT_LABELS_V2_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Update Incident Labels v2"
)
SYNC_INCIDENTS_JOB_NAME: str = f"{INTEGRATION_NAME} - Sync Incidents"
SYNC_INCIDENTS_V2_JOB_NAME: str = f"{INTEGRATION_NAME} - Sync Incidents V2"

# TABLES NAMES
INCIDENTS_TABLE_NAME = "Incidents"
ALERT_RULE_DETAILS_TABLE = "Microsoft Azure Sentinel Alert Rule Details"
ALERT_RULES_TABLE_NAME = "Microsoft Azure Sentinel Alert Rules found"
INCIDENT_STATISTICS_BY_SEVERITY_TABLE_NAME = (
    f"{PRODUCT_NAME} Incident statistics by Severity"
)
INCIDENT_STATISTICS_BY_STATUS_TABLE_NAME = (
    f"{PRODUCT_NAME} Incident statistics by Status"
)
HUNTING_RULES_TABLE_NAME = f"{PRODUCT_NAME} hunting rules found"
CUSTOM_HUNTING_RULE_DETAILS_TABLE_NAME = f"{PRODUCT_NAME} Hunting Rule Details"
KQL_QUERY_RESULTS = "KQL Query results"
HUNTING_RULE_RESULTS_TABLE_NAME = f"{PRODUCT_NAME} hunting rule results"


SPECIAL_CHARACTERS_MAPPING = {"\r": "", "\n": "", "\u200b": ""}
SCHEDULED_ALERT_TYPE_STRING = "Scheduled Alerts"
SCHEDULED_ALERT_EVENT_KIND = "ScheduledAlert"
NRT_ALERT_TYPE_STRING = "NRT Alerts"
NRT_ALERT_EVENT_KIND = "NRT"
INCIDENT_EVENT_KIND = "Incident"
ALERT_TYPES_WITH_EVENTS = [SCHEDULED_ALERT_TYPE_STRING, NRT_ALERT_TYPE_STRING]
PLACEHOLDER_START = "["
PLACEHOLDER_END = "]"
CHARACTERS_LIMIT = 256
GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1

FETCH_INCIDENTS_EVENTS_ERROR_MESSAGE = (
    "Failed to process Azure Sentinel Scheduled Alert with id {incident_name} "
    "and incident number {incident_number}! "
    'Query field of the affected alert: "{query}"'
)

INCIDENT_CONNECTOR_V2_NAME = "Microsoft Azure Sentinel Incidents Connector v2"
SCHEDULED_ALERTS_EVENTS_DEFAULT_LIMIT = 100
DEFAULT_INCIDENTS_ALERTS_LIMIT_TO_INGEST = 10
DEFAULT_VENDOR_NAME = "MicrosoftAzureSentinel"
DEFAULT_PRODUCT_NAME = "Azure Sentinel"
DEFAULT_HTTP_REQUEST_TIMEOUT_SECONDS = 60
FETCH_TIMEOUT_THRESHOLD = 0.8
STORED_IDS_LIMIT = 3000
SAFE_ERRORS = ["ValueError", "TimeoutError"]
ALERTS_EVENTS_DEFAULT_LIMIT = 100
INCIDENTS_TRACKING_DEFAULT_HOURS = 24
IDS_FILE_NAME = "ids.json"
IDS_KEY = "ids"
INCIDENT_TRACKING_CONNECTOR_NAME = "Microsoft Sentinel Incident Tracking Connector"
COROS_LIMIT = 20
TRACKING_EVENTS_CHUNK_SIZE = 100
INCIDENTS_FETCH_LIMIT = 100
SUPPORTED_ENTITY_KINDS = ("Account", "Mailbox", "Host", "Ip")
CONTEXT_VALUE_CHUNK_LIMIT = 2_800_000
CONTEXT_VALUE_CHUNK_SIZE = 12_000
CONTEXT_VALUE_CHUNK_SIZE_REDUCTION = 10

GRAPH_API_ROOT: str = "https://graph.microsoft.com"
GRAPH_API_ENDPOINTS: list[str] = [
    "graph-incident",
    "graph-incidents",
    "graph-incident-comments",
]
INCIDENTS_JOB_IDS_FILE_NAME: str = "incident_ids.json"
INCIDENTS_JOB_IDS_DB_KEY: str = "microsoft_sentinel_incident_ids"
SECOPS_CASE_TAG: str = "Microsoft Sentinel Incident"
SECOPS_COMMENT_PREFIX: str = "Google SecOps: "
SECOPS_CASE_COMMENT_PREFIX: str = "Google SecOps Case "
SENTINEL_COMMENT_PREFIX: str = "Microsoft Sentinel: "
SENTINEL_INCIDENT_COMMENT_PREFIX: str = "Microsoft Sentinel Incident "
SENTINEL_TAG_PREFIX: str = "Microsoft Sentinel: "
SECOPS_TAG_PREFIX: str = "Google SecOps: "
CASE_STATUS: str = "BOTH"
INCIDENT_RESOLVED_STATUS: str = "resolved"
SYNC_INCIDENTS_CONTEXT_IDENTIFIER: str = "sync_incidents"
SYNC_INCIDENTS_V2_CONTEXT_IDENTIFIER: str = "sync_incidents_v2"
MIN_TAG_LEN: int = 2
MAX_TAG_LEN: int = 100
SENTINEL_COMMENTS_LIMIT: int = 100
SYNC_INCIDENTS_TIMEOUT_IN_MILLISECONDS: int = 600 * 1000
CASES_SYNC_LIMIT: int = 10
INCIDENTS_LIMIT: int = 10
BATCH_SIZE: int = 50
BATCH_INCIDENTS_LIMIT: int = 10
COMMENTS_MODIFICATION_TIME_FILTER: int = 1
INCREMENT_CASE_UPDATED_TIME_BY_MS: int = 1
ENTITY_TYPE: int = 2
INCIDENT_ID_CONTEXT_PROPERTY: str = "Incident_ID"
MISSING_APPLICATION_ROLE_ERROR: str = "Missing application roles"
TIMESTAMP_FORMAT: str = "%Y-%m-%dT%H:%M:%SZ"
INCIDENT_CLOSED_STATUS: str = "Closed"
SENTINEL_TO_SECOPS_SEVERITY_MAP: dict[str, str] = {
    "Informational": "Informative",
    "Low": "Low",
    "Medium": "Medium",
    "High": "High",
}
SENTINEL_ALERTS_CONTEXT_KEY: str = "Microsoft_Sentinel_Alerts"
MAX_CHARS: int = 29000
CASE_ALERT_CLOSED_STATUS: str = "close"
DEFAULT_COMMENT_LENGTH: int = 0
TIMEOUT: int = 60

PRE_FILTER_KQL_QUERY: str = (
    "let Incidents = \n"
    "    SecurityIncident\n"
    "    | where LastModifiedTime > {updated_filter}\n"
    "    {creation_filter_line}\n"
    "    | summarize arg_max(TimeGenerated, Title, IncidentNumber, "
    "AlertIds, AdditionalData, LastModifiedTime) "
    "by IncidentName\n"
    ";\n"
    "let AlertStats = \n"
    "    Incidents\n"
    "    | mv-expand AlertIds to typeof(string) \n"
    "    | join kind = leftouter (\n"
    "        SecurityAlert\n"
    "        | summarize arg_max(TimeGenerated, Entities, "
    "ExtendedProperties) by SystemAlertId\n"
    "        | extend EntityCount = max_of(0, "
    "array_length(parse_json(Entities)))\n"
    "        | extend AlertContentHash = hash(strcat(Entities, "
    "tostring(ExtendedProperties), tostring(TimeGenerated)))\n"
    "        )\n"
    "        on $left.AlertIds == $right.SystemAlertId\n"
    "    | summarize \n"
    "        AlertsCount = count(),\n"
    "        AlertsWithEntitiesCount = countif(EntityCount > 0),\n"
    "        AlertContentHashes = make_list_if(AlertContentHash, "
    "EntityCount > 0) \n"
    "        by IncidentName\n"
    ";\n"
    "Incidents\n"
    "| extend AlertsCount = toint(AdditionalData.alertsCount)\n"
    "| lookup AlertStats on IncidentName\n"
    "| project\n"
    "    IncidentName,\n"
    "    AlertsCount,\n"
    "    AlertsWithEntitiesCount,\n"
    "    AlertContentHashes = tostring(AlertContentHashes)"
)
RESPONSE_SIZE_ERROR: str = "Response size too large"
RETRYABLE_SERVER_ERRORS: set = {502, 503, 504}
DEFAULT_429_SLEEP: int = 5
DEFAULT_THROTTLED_SLEEP: int = 30
DEFAULT_SERVER_ERROR_SLEEP: int = 5
RETRY_BUFFER_SECONDS: int = 2
MAX_CONCURRENT_FETCHES_LIMIT: int = 5
DEFAULT_SCHEDULED_ALERTS_EVENTS_LIMIT: int = 1000
