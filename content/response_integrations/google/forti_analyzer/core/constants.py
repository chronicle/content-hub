from __future__ import annotations
INTEGRATION_NAME = "FortiAnalyzer"
INTEGRATION_DISPLAY_NAME = "FortiAnalyzer"
INTEGRATION_PREFIX = "FortiAnalyzer"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
ENRICH_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich Entities"
SEARCH_LOGS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Search Logs"
UPDATE_ALERT_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Update Alert"
ADD_COMMENT_TO_ALERT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Comment To Alert"
MAX_PROGRESS_PERCENTAGE: int = 100
ENDPOINTS = {"rpc": "/jsonrpc"}

LOG_TYPES = {
    "Traffic": "traffic",
    "App Control": "app-ctrl",
    "Attack": "attack",
    "Content": "content",
    "DLP": "dlp",
    "Email Filter": "emailfilter",
    "Event": "event",
    "History": "history",
    "Virus": "virus",
    "VOIP": "voip",
    "Web Filter": "webfilter",
    "Netscan": "netscan",
    "FCT Event": "fct-event",
    "FCT Traffic": "fct-traffic",
    "WAF": "waf",
    "GTP": "gtp",
}
# Time frames
TIME_FRAME_MAPPING = {
    "Last Hour": {"hours": 1},
    "Last 6 Hours": {"hours": 6},
    "Last 12 Hours": {"hours": 12},
    "Last 24 Hours": {"hours": 24},
    "Last Week": {"weeks": 1},
    "Last Month": "last_month",
    "Custom": "custom",
}

TIME_ORDER = {"DESC": "desc", "ASC": "asc"}
CUSTOM_TIME_FRAME = "Custom"
TIME_FRAME_DEFAULT_VALUE = "Last Month"

DEFAULT_LOGS_COUNT = 20
MAX_LOGS_COUNT = 1000

ENRICHMENT_PREFIX = "FortiAn"

DONE_STATUS = "done"
SELECT_ONE = "Select One"
ACKNOWLEDGEMENT_MAPPING = {"Acknowledge": True, "Unacknowledge": False}

# Connector
CONNECTOR_NAME = f"{INTEGRATION_DISPLAY_NAME} - Alerts Connector"
DEFAULT_TIME_FRAME = 1
DEFAULT_LIMIT = 20
DEFAULT_MAX_LIMIT = 100
DEVICE_VENDOR = "FortiAnalyzer"
DEVICE_PRODUCT = "FortiAnalyzer"
WHITELIST_FILTER = 1
BLACKLIST_FILTER = 2
POSSIBLE_SEVERITIES = ["low", "medium", "high", "critical"]
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
LOGS_LIMIT = 200
SEVERITY_MAPPING = {"critical": 0, "high": 1, "medium": 2, "low": 3}

SIEMPLIFY_SEVERITY_MAPPING = {"critical": 100, "high": 80, "medium": 60, "low": 40}

TIME_INTERVAL_CHUNK = 12
