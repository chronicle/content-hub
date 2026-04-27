from __future__ import annotations
PROVIDER_NAME = "Rapid7 InsightIDR"

# Actions
PING_SCRIPT_NAME = f"{PROVIDER_NAME} - Ping"
LIST_INVESTIGATIONS_SCRIPT_NAME = f"{PROVIDER_NAME} - List Investigations"
SET_INVESTIGATION_STATUS_SCRIPT_NAME = f"{PROVIDER_NAME} - Set Investigation Status"
SET_INVESTIGATION_ASSIGNEE_SCRIPT_NAME = f"{PROVIDER_NAME} - Set Investigation Assignee"
LIST_SAVED_QUERIES_SCRIPT_NAME = f"{PROVIDER_NAME} - List Saved Queries"
CREATE_SAVED_QUERY_SCRIPT_NAME = f"{PROVIDER_NAME} - Create Saved Query"
DELETE_SAVED_QUERY_SCRIPT_NAME = f"{PROVIDER_NAME} - Delete Saved Query"
RUN_SAVED_QUERY_SCRIPT_NAME = f"{PROVIDER_NAME} - Run Saved Query"
UPDATE_INVESTIGATION_SCRIPT_NAME = f"{PROVIDER_NAME} - Update Investigation"

ENDPOINTS = {
    "validate": "/validate",
    "investigations": "/idr/v1/investigations",
    "update_investigation": "/idr/v2/investigations/{investigation_id}",
    "update_investigation_status": "/idr/v1/investigations/{investigation_id}/status/{status}",
    "update_investigation_assignee": "/idr/v1/investigations/{investigation_id}/assignee",
    "saved_queries": "/log_search/query/saved_queries",
    "logs": "/log_search/management/logs",
    "create_saved_queries": "/log_search/query/saved_queries",
    "delete_saved_queries": "/log_search/query/saved_queries/{saved_query_id}",
    "run_saved_query": "/log_search/query/saved_query/{saved_query_id}",
    "get_investigations": "/idr/v2/investigations",
    "get_investigation_alerts": "/idr/v2/investigations/{investigation_id}/alerts",
}

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
DEFAULT_DELIMITER = ","
ACTION_PROCESS_TIMEOUT = 5 * 60 * 1000
REQUEST_DURATION_BUFFER = 60 * 1000

STATUS_MAPPING = {"Open": "open", "Investigating": "investigating", "Closed": "closed"}

DISPOSITION_MAPPING = {
    "Benign": "benign",
    "Malicious": "malicious",
    "Not Applicable": "not_applicable",
}

# Connector
CONNECTOR_NAME = f"{PROVIDER_NAME} - Alerts Connector"
DEFAULT_TIME_FRAME = 1
DEFAULT_LIMIT = 20
DEFAULT_MAX_LIMIT = 100
MAX_INVESTIGATION_ALERTS_LIMIT = 200
DEVICE_VENDOR = "Rapid7 InsightsIDR"
DEVICE_PRODUCT = "Rapid7 InsightsIDR"
WHITELIST_FILTER = 1
BLACKLIST_FILTER = 2
POSSIBLE_SOURCES = ["user", "alert"]
DEFAULT_SOURCES = "ALERT,USER"
# Do not change the order of severities!!! It's used for filtering in the connector.
POSSIBLE_SEVERITIES = ["low", "medium", "high", "critical"]
SEVERITY_MAPPING = {
    "CRITICAL": 100,
    "HIGH": 80,
    "MEDIUM": 60,
    "UNSPECIFIED": 60,
    "LOW": 40,
    "INFORMATIONAL": -1,
}
UNSPECIFIED_SEVERITY = "UNSPECIFIED"
