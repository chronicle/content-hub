from __future__ import annotations
INTEGRATION_NAME = "Sophos"
INTEGRATION_DISPLAY_NAME = "Sophos"

FILTER_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
GET_SERVICE_STATUS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Service Status"
SCAN_ENDPOINTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Scan Endpoints"
GET_EVENTS_LOG_SCRIPT_NAME = f"{INTEGRATION_NAME} - GetEventsLog"
ISOLATE_ENDPOINT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Isolate Endpoint"
UNISOLATE_ENDPOINT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Unisolate Endpoint"
LIST_ALERT_ACTIONS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Alert Actions"
EXECUTE_ALERT_ACTIONS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Execute Alert Actions"
ENRICH_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich Entities"
ADD_ENTITIES_TO_BLOCKLIST_ACTIONS_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Add Entities To Blocklist"
)
ADD_ENTITIES_TO_ALLOWLIST_ACTIONS_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Add Entities To Allowlist"
)

# Connector
CONNECTOR_NAME = f"{INTEGRATION_DISPLAY_NAME} - Alerts Connector"
DEFAULT_TIME_FRAME = 1
DEFAULT_LIMIT = 10
MAX_LIMIT = 1000
MAX_FETCH_HOURS = 24
LIMIT_PER_REQUEST = 100
LIMIT_PER_REQUEST_LATEST: int = 200
DEVICE_VENDOR = "Sophos"
DEVICE_PRODUCT = "Sophos Central"

SEVERITY_MAP = {"low": 40, "medium": 60, "high": 100}

SEVERITIES = ["low", "medium", "high"]
ISOLATION_IN_PROGRESS = "In Progress"
ISOLATED = "Isolated"
UNISOLATED = "Unisolated"
DEFAULT_TIMEOUT = 300
HEALTH_COLOR_MAP = {"Good": "#339966", "Suspicious": "#ff9900", "Bad": "#ff0000"}

ACTION_TYPES_MAPPING = {
    "Acknowledge": "acknowledge",
    "Clean PUA": "cleanPua",
    "Clean Virus": "cleanVirus",
    "Auth PUA": "authPua",
    "Clear Threat": "clearThreat",
    "Clear HMPA": "clearHmpa",
    "Send Message PUA": "sendMsgPua",
    "Send Message Threats": "sendMsgThreat",
}

SHA256_LENGTH = 64
