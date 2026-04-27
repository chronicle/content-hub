from __future__ import annotations
PROVIDER_NAME = "FireEye ETP"

# ACTIONS
PING_SCRIPT_NAME = f"{PROVIDER_NAME} - Ping"

ENDPOINTS = {
    "test_connectivity": "/api/v1/alerts",
    "get_alerts": "/api/v1/alerts",
    "get_alert_details": "/api/v1/alerts/{alert_id}",
}

HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

ALERTS_CONNECTOR_NAME = "FireEye ETP - Email Alerts Connector"

TIMEOUT_THRESHOLD = 0.9
LIMIT_IDS_IN_IDS_FILE = 1000
TEST_OFFSET_HOURS = 24
ACCEPTABLE_TIME_INTERVAL_IN_MINUTES = 5
WHITELIST_FILTER = "whitelist"
BLACKLIST_FILTER = "blacklist"
DEFAULT_TIME_FRAME = 1
ALERT_ID_FIELD = "id"
DEFAULT_FETCH_SIZE = 200

MAP_FILE = "map.json"
IDS_FILE = "ids.json"

DEVICE_VENDOR = "FireEye"
DEVICE_PRODUCT = "FireEye ETP"
ALERT_NAME = "Malicious Email"

PRINT_TIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
API_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
