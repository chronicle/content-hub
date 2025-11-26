INTEGRATION_NAME = "Darktrace"
INTEGRATION_DISPLAY_NAME = "Darktrace"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
ENRICH_ENTITIES_NAME = f"{INTEGRATION_DISPLAY_NAME} - Enrich Entities"
UPDATE_MODEL_BREACH_STATUS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Update Model Breach Status"
LIST_ENDPOINT_EVENTS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - List Endpoint Events"
EXECUTE_CUSTOM_SEARCH_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Execute Custom Search"
LIST_SIMILAR_DEVICES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - List Similar Devices"
ADD_COMMENT_TO_MODEL_BREACH_NAME = f"{INTEGRATION_DISPLAY_NAME} - Add Comment To Model Breach"

ENDPOINTS = {
    "status": "/status",
    "model_breaches": "/modelbreaches",
    "model_breach_details": "/details",
    "device_search": "/devicesearch",
    "devices": "/devices",
    "endpoint_details": "/endpointdetails",
    "acknowledge": "/modelbreaches/{model_breach_id}/acknowledge",
    "unacknowledge": "/modelbreaches/{model_breach_id}/unacknowledge",
    "model_breach": "/modelbreaches/{model_breach_id}",
    "ai_analyst_incident_events": "/aianalyst/incidentevents",
    "details": "/details",
    "connection_data": "/deviceinfo",
    "advanced_search": "/advancedsearch/api/search/{base64_query}",
    "similar_devices": "/similardevices",
    "add_comment": "/modelbreaches/{model_breach_id}/comments",
}


# Connector
DARKTRACE_AI_EVENT = "Darktrace AI Event"
AI_CONNECTOR_NAME = "Darktrace - AI Incident Events Connector"
AI_DEFAULT_TIME_FRAME = 1
AI_DEFAULT_LIMIT = 10
AI_DEFAULT_FETCH_INTERVAL = 4
AI_DEFAULT_MAX_LIMIT = 100
AI_MAX_LIMIT = 1000
AI_DEFAULT_MIN_SCORE = 0
AI_SCORE_MIN_VALUE = 0
AI_SCORE_MAX_VALUE = 100
AI_INCIDENTS_MIN_VALUE = 1
AI_INCIDENTS_MAX_VALUE = 100
AI_DEVICE_VENDOR = "Darktrace"
AI_DEVICE_PRODUCT = "AI Incident"
DARKTRACE_AI_FILE_NAME = "darktrace_ai_repeat_time.timestamp"
REPEAT_TIME_DEFAULT_VALUE = -1
REPEAT_TIME_DB_KEY = "repeat_time"
MILI_SECOND = 1000
SPLIT_INTERVAL = 4
PADDING_INTERVAL = 1
CONNECTOR_NAME = "Darktrace - Model Breaches Connector"
DEFAULT_TIME_FRAME = 1
DEFAULT_LIMIT = 10
DEFAULT_MAX_LIMIT = 100
MAX_LIMIT = 1000
DEFAULT_MIN_SCORE = 0
MIN_PRIORITY: int = 1
MAX_PRIORITY: int = 5
DEVICE_VENDOR = "Darktrace"
DEVICE_PRODUCT = "Darktrace"
BEHAVIOUR_VISIBILITY_FILTER_VALUES = {
    "critical",
    "suspicious",
    "compliance",
    "informational",
}

SEVERITY_MAP = {"INFO": -1, "LOW": 40, "MEDIUM": 60, "HIGH": 80, "CRITICAL": 100}


ENRICHMENT_PREFIX = "Dark"
DEVICE_KEYS = {"ip": "ip", "mac": "mac", "hostname": "hostname"}

MODEL_BREACH_STATUSES = {
    "acknowledged": "Acknowledged",
    "unacknowledged": "Unacknowledged",
}

ERROR_TEXT = "ERROR"

PARAMETERS_DEFAULT_DELIMITER = ","
EVENT_TYPES = [
    "connection",
    "unusualconnection",
    "newconnection",
    "notice",
    "devicehistory",
    "modelbreach",
]
EVENT_TYPES_NAMES = {
    "connection": "Connection Events",
    "unusualconnection": "Unusual Connection Events",
    "newconnection": "New Connection Events",
    "notice": "Notice Events",
    "devicehistory": "Device History Events",
    "modelbreach": "Model Breach Events",
}

TIMEFRAME_MAPPING = {
    "Last Hour": {"hours": 1},
    "Last 6 Hours": {"hours": 6},
    "Last 24 Hours": {"hours": 24},
    "Last Week": "last_week",
    "Last Month": "last_month",
    "Custom": "custom",
    "Alert Time Till Now": "Alert Time Till Now",
    "5 Minutes Around Alert Time": "5 Minutes Around Alert Time",
    "30 Minutes Around Alert Time": "30 Minutes Around Alert Time",
    "1 Hour Around Alert Time": "1 Hour Around Alert Time",
}

DEFAULT_MAX_HOURS_BACKWARDS = 24
DEFAULT_RESULTS_LIMIT = 50
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
MILLISECONDS_IN_HOUR = 3600 * 1000
MAX_PADDING_TIME = 100
