from __future__ import annotations
INTEGRATION_NAME = "LogPoint"
DEFAULT_DEVICE_VENDOR = "LogPoint"
USER_PREFERENCE = "user_preference"
REPOS = "logpoint_repos"

# Actions:
PING = "Ping"
LIST_REPOS = "List Repos"
EXECUTE_QUERY = "Execute Query"
EXECUTE_ENTITY_QUERY_SCRIPT_NAME = "Execute Entity Query"
UPDATE_INCIDENT_STATUS_SCRIPT_NAME = f'{INTEGRATION_NAME} - {"Update Incident Status"}'

# Connectors
INCIDENTS_CONNECTOR_SCRIPT_NAME = f"{INTEGRATION_NAME} - Incidents Connector"

# Status Codes
VALID_RESPONSE = 200
NOT_FOUND = 404

DEFAULT_TIME_FRAME = "Last 24 Hours"
DEFAULT_MAX_REPOS = 100
MIN_REPOS = 1

NOT_FOUND_IN_SERVER_MESSAGE = "was not found on this server."

TIMEOUT_RESPONSE_MESSAGE = "timeout"

SEARCH_ID = "search_id"

RESULTS = "Results"
REPOS_TABLE = "Available Repos"
CONNECTOR_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

DEFAULT_QUERY_TIME_FRAME = "Last 24 Hours"
CUSTOM_QUERY_TIME_FRAME = "Custom"
DEFAULT_CROSS_ENTITY_OPERATOR = "OR"
DEFAULT_MAX_QUERY_RESULTS = 100


TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
VALID_EMAIL_REGEXP = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

URL_ENTITY_KEY = "URL"
ENTITY_TYPE_EMAIL = "EmailAddress"

CHART_STRING = "| chart"
FOLLOWED_BY_STRING = "followed by"

EVENTS_LIMIT_PER_ALERT = 200
EVENTS_TOTAL_COUNT = 200
SLEEP_TIME = 1

# Mappings
TIME_FRAME_MAPPING = {
    "Last 24 Hours": "Last 24 hours",
    "Last Hour": "Last hour",
    "Last 12 Hours": "Last 12 hours",
    "Last 30 Days": "Last 30 days",
    "Last 365 Days": "Last 365 days",
}

CRITICAL_RISK = "critical"
HIGH_RISK = "high"
MEDIUM_RISK = "medium"
LOW_RISK = "low"

INCIDENT_RISK_LEVEL_MAPPING = {
    LOW_RISK: 1,
    MEDIUM_RISK: 2,
    HIGH_RISK: 3,
    CRITICAL_RISK: 4,
}

LOG_POINT_TO_SIEM_PRIORITIES = {
    LOW_RISK: 40,
    MEDIUM_RISK: 60,
    HIGH_RISK: 80,
    CRITICAL_RISK: 100,
}

INCIDENT_SEARCH_TYPE = "Search"

OR = "or"
AND = "and"

MAPPED_OPERATOR = {"OR": "or", "AND": "and"}

CLOSE = "Close"
RESOLVE = "Resolve"

ACTION_MAPPING = {CLOSE: "Closed", RESOLVE: "Resolved"}
STORED_IDS_LIMIT = 3000
