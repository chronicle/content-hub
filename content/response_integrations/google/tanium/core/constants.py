from __future__ import annotations
INTEGRATION_NAME = "Tanium"
INTEGRATION_VERSION = "20.0"

PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
CREATE_QUESTION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create Question"
GET_QUESTION_RESULTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Question Results"
ENRICH_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich Entities"
LIST_ENDPOINT_EVENTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Endpoint Events"
GET_TASK_DETAILS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Task Details"
DOWNLOAD_FILE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Download File"
DELETE_FILE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Delete File"
QUARANTINE_ENDPOINT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Quarantine Endpoint"
CREATE_CONNECTION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create Connection"
LIST_CONNECTIONS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Connections"

QUESTION_RESULT_TABLE_NAME = "Tanium Question {} Results"

BAD_REQUEST_STATUS_CODE = "400 Bad Request"
NOT_FOUND_STATUS_CODE = "404 Item Not Found"
UNAUTHORIZED_STATUS_CODE = 401
MAX_QUESTION_RESULTS_DEFAULT = 50
TIMEOUT_THRESHOLD = 0.9
DEFAULT_TIMEOUT = 300
DEFAULT_ACTION_LIMIT = 50
DEFAULT_SORT_FIELD = "create_time_raw"
GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

ENRICHMENT_PREFIX = "Tanium"
TASK_STATUS_COMPLETED = "COMPLETED"
TASK_STATUS_INCOMPLETE = "INCOMPLETE"
TASK_STATUS_ERROR = "ERROR"
QUARANTINE_TASK = "quarantine"

ASC_SORT_ORDER = "ASC"
CONNECTED_STATUS = "connected"
PROCESS_EVENT_TYPE = "process"
EVENT_TYPE_MAPPING = {
    "File": "file",
    "Network": "network",
    "Process": "process",
    "Registry": "registry",
    "Driver": "driver",
    "Combined": "combined",
    "DNS": "dns",
    "Image": "image",
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

PACKAGE_NAME_MAPPING = {
    "Linux": "Apply Linux IPTables Quarantine",
    "Mac": "Apply Mac PF Quarantine",
    "Windows": "Apply Windows IPsec Quarantine",
}

ENTITY_TYPE_MAPPING = {"HOSTNAME": "hostname", "ADDRESS": "ip"}

PACKAGE_PARAMETERS = [
    {"key": "$1", "value": None},
    {"key": "$2", "value": None},
    {"key": "$3", "value": None},
    {"key": "$4", "value": None},
    {"key": "$5", "value": None},
    {"key": "$6", "value": None},
    {"key": "$7", "value": None},
    {"key": "$8", "value": None},
    {"key": "$9", "value": None},
]
