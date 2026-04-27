from __future__ import annotations
PROVIDER_NAME = "Digital Shadows"

RESULTS_SIZE = 50

API_URL = "https://portal-digitalshadows.com"
HEADERS = {"Content-Type": "application/json"}
API_ENDPOINTS = {
    "SEARCH_FIND": "/api/search/find",
    "get_incidents": "/api/incidents/find",
}

SEARCH_BODY = {
    "pagination": {"size": RESULTS_SIZE, "offset": 0},
    "sort": {"property": "relevance", "direction": "DESCENDING"},
    "filter": {"types": []},
    "query": "{}",
}


# CONNECTORS
DEVICE_VENDOR = "Digital Shadows"
DEVICE_PRODUCT = "Digital Shadows"
INCIDENTS_CONNECTOR_NAME = f"{PROVIDER_NAME} - Incident Connector"
IDS_FILE = "ids.json"
MAP_FILE = "map.json"
ALERT_ID_FIELD = "id"
LIMIT_IDS_IN_IDS_FILE = 1000
TIMEOUT_THRESHOLD = 0.9
ACCEPTABLE_TIME_INTERVAL_IN_MINUTES = 5
WHITELIST_FILTER = "whitelist"
BLACKLIST_FILTER = "blacklist"
DEFAULT_TIME_FRAME = 1
ALERTS_FETCH_SIZE = 100
ALERTS_LIMIT = 50
DEFAULT_SEVERITY = "NONE"
DATETIME_STR_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
API_MAX_FETCH_LIMIT = 500

# Do not change the order, It's used in Manager._get_severities_from
SEVERITIES = ["NONE", "VERY_LOW", "LOW", "MEDIUM", "HIGH", "VERY_HIGH"]

# SIEM
DIGITAL_SHADOWS_TO_SIEM_SEVERITY = {
    "NONE": -1,
    "VERY_LOW": 40,
    "LOW": 40,
    "MEDIUM": 60,
    "HIGH": 80,
    "VERY_HIGH": 100,
}
