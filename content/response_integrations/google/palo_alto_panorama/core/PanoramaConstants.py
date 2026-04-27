from __future__ import annotations
PROVIDER_NAME = "Panorama"
DEVICE_VENDOR = "Palo Alto"
DEVICE_PRODUCT = "Panorama"
LOGS_LIMIT = 100

# REQUEST METHODS
GET = "GET"
POST = "POST"

# CONNECTORS
THREAT_LOG_CONNECTOR_NAME = f"{PROVIDER_NAME} - Threat Log Connector"
IDS_FILE = "ids.json"
MAP_FILE = "map.json"
THREAT_ID = "threat_id"
LIMIT_IDS_IN_IDS_FILE = 1000
TIMEOUT_THRESHOLD = 0.9
ACCEPTABLE_TIME_INTERVAL_IN_MINUTES = 5
WHITELIST_FILTER = "whitelist"
BLACKLIST_FILTER = "blacklist"
CONNECTOR_LOG_TYPE = "Threat"


ITEMS_PER_REQUEST = 50

HEADERS = {
    "Accept": "application/xml",
    "Content-Type": "application/x-www-form-urlencoded",
}
ENDPOINTS = {"main_endpoint": ""}

LOG_TYPE_MAP = {
    "Traffic": "traffic",
    "Threat": "threat",
    "URL Filtering": "url",
    "WildFire Submissions": "wildfire",
    "Data Filtering": "data",
    "HIP Match": "hipmatch",
    "IP Tag": "iptag",
    "User ID": "userid",
    "Tunnel Inspection": "tunnel",
    "Configuration": "config",
    "System": "system",
    "Authentication": "auth",
}

TIME_FORMAT = "%Y/%m/%d %H:%M:%S"
JOB_FINISHED_STATUS = "FIN"

# SIEM
PANORAMA_TO_SIEM_SEVERITY = {
    "Informational": 20,
    "Low": 40,
    "Medium": 60,
    "High": 80,
    "Critical": 100,
}

FILE_SUBTYPES = ["file", "virus", "wildfire-virus", "wildfire"]

URI_SUBTYPE = "url"

COMMIT_STATUS_FINISHED = "FIN"
COMMIT_STATUS_FAILED = "FAIL"

AMPERSAND_REPLACEMENT = "%26amp;"
AMPERSAND = "%26"
