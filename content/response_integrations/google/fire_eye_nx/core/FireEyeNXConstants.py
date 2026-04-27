from __future__ import annotations
PROVIDER_NAME = "FireEye NX"
DEVICE_VENDOR = "FireEye"
DEVICE_PRODUCT = "FireEye NX"

# CONNECTORS
ALERTS_CONNECTOR_NAME = f"{PROVIDER_NAME} - Alerts Connector"
IDS_FILE = "ids.json"
MAP_FILE = "map.json"
ALERT_ID_FIELD = "uuid"
LIMIT_IDS_IN_IDS_FILE = 1000
TIMEOUT_THRESHOLD = 0.9
ACCEPTABLE_TIME_INTERVAL_IN_MINUTES = 5
WHITELIST_FILTER = "whitelist"
BLACKLIST_FILTER = "blacklist"
DEFAULT_TIME_FRAME = 1
DURATION = "48_hours"
API_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f-00:00"

# ACTIONS
PING_SCRIPT_NAME = f"{PROVIDER_NAME} - Ping"
DOWNLOAD_ALERT_ARTIFACTS_SCRIPT_NAME = f"{PROVIDER_NAME} - Download Alert Artifacts"
ADD_IPS_POLICY_EXCEPTION_SCRIPT_NAME = f"{PROVIDER_NAME} - Add IPS Policy Exception"

# SIEM
FIREEYE_NX_TO_SIEM_SEVERITY = {"MINR": 60, "MAJR": 80, "CRIT": 100}

ENDPOINTS = {
    "authorize": "wsapis/v2.0.0/auth/login",
    "test_connectivity": "wsapis/v2.0.0/health/system",
    "download_artifacts": "wsapis/v2.0.0/artifacts/{alert_uuid}",
    "get_alerts": "wsapis/v2.0.0/alerts",
    "add_ip_policy_exception": "wsapis/v2.0.0/ips/policy_exceptions",
}

HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

DEFAULT_IP_POLICY_EXCEPTION_MODE = "Block"
DEFAULT_IP_POLICY_EXCEPTION_INTERFACE = "ALL"
DEFAULT_IP_POLICY_EXCEPTION_NAME = "Siemplify_{}_{}"

IPV4_MASK = "/32"

MAPPED_IP_POLICY_EXCEPTION_MODE = {
    "Block": "block",
    "Unblock": "unblock",
    "Suppress": "suppress",
    "Suppress-unblock": "suppress-unblock",
}
