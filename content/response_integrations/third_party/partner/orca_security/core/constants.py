from __future__ import annotations

INTEGRATION_NAME = "Orca Security"
INTEGRATION_DISPLAY_NAME = "Orca Security"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
UPDATE_ALERT_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Update Alert"
ADD_COMMENT_TO_ALERT_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Add Comment To Alert"
GET_COMPLIANCE_INFO_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Get Compliance Info"
SCAN_ASSETS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Scan Assets"
GET_VULNERABILITY_DETAILS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Get Vulnerability Details"
GET_ASSET_DETAILS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Get Asset Details"

SERVING_QUERY: str = "/api/serving-layer/query"
ENDPOINTS = {
    "login": "/api/user/session",
    "ping": "/api/default_user_preference",
    "get_alerts": SERVING_QUERY,
    "verify_alert": "/api/alerts/{alert_id}/verify",
    "snooze_alert": "/api/alerts/{alert_id}/snooze",
    "update_alert_status": "/api/alerts/{alert_id}/status/{status}",
    "add_alert_comment": "/api/alerts/{alert_id}/comment",
    "get_frameworks": "/api/serving-layer/compliance/frameworks/overview",
    "start_scan": "/api/scan/asset/{asset_id}",
    "get_scan_status": "/api/scan/status/{scan_id}",
    "vulnerability_details": SERVING_QUERY,
    "asset_details": SERVING_QUERY,
}

# Connector
CONNECTOR_NAME = f"{INTEGRATION_DISPLAY_NAME} - Alerts Connector"
DEFAULT_TIME_FRAME = 1
DEFAULT_LIMIT = 100
DEFAULT_ASSET_LIMIT: int = 20
DEFAULT_RESULTS_LIMIT: int = 1000
DEFAULT_OFFSET: int = 0
DEFAULT_MAX_LIMIT = 100
DEVICE_VENDOR = "Orca Security"
DEVICE_PRODUCT = "Orca Security"
WHITELIST_FILTER = 1
BLACKLIST_FILTER = 2
KEY_PREFIX = "Orca_Security"
FALLBACK_ALERT_NAME = "Orca Security Alert"
POSSIBLE_SEVERITIES = [
    "critical",
    "high",
    "medium",
    "low",
    "unknown",
]
SEVERITY_MAPPING = {
    "critical": 100,
    "high": 80,
    "medium": 60,
    "low": -1,
    "unknown": -1,
}

HIGHEST_POSSIBLE_SCORE = 10.0


DEFAULT_SNOOZE_DAYS = 1
SNOOZE_STATE_MAPPING = {"Select One": "", "Snooze": "Snooze", "Unsnooze": "Unsnooze"}

STATUS_MAPPING = {
    "Select One": "",
    "Open": "open",
    "In Progress": "in_progress",
    "Close": "close",
    "Dismiss": "dismiss",
}

SCORE_MAPPING = {"info": 50, "low": 75, "medium": 90, "high": 100}

SCORE_COLORS = {
    "info": "#ff0000",
    "low": "#ff9900",
    "medium": "#33cccc",
    "high": "#00ff00",
}

COMPLETED_STATUS = "done"
DEFAULT_TIMEOUT = 300

VULNERABILITIES_MAX_LIMIT = 10000
OUTPUT_TYPE_JSON = "JSON"
VULNERABILITIES_TABLE_NAME = "Vulnerability Details"
ASSETS_TABLE_NAME = "Asset Details"
SEVERITY_COLOR_MAPPER = {
    "critical": "style='color: #ff0000;'",
    "high": "style='color: #ff9900;'",
    "medium": "style='color: #ffff00;'",
    "low": "",
    "unknown": "",
}
