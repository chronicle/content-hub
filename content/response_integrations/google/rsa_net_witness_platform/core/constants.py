from __future__ import annotations
INTEGRATION_NAME = "RSANetWitnessPlatform"

PROVIDER_NAME = "RSA NetWitness Platform"
DEVICE_PRODUCT = PROVIDER_NAME
DEVICE_VENDOR = "RSA"

PING_ACTION = f"{INTEGRATION_NAME} - Ping"
QUERY_NET_HOST_ACTION = f"{INTEGRATION_NAME} - Query NetWitness For Events Around Host"
QUERY_NET_IP_ACTION = f"{INTEGRATION_NAME} - Query NetWitness For Events Around IP"
QUERY_NET_USER_ACTION = f"{INTEGRATION_NAME} - Query NetWitness For Events Around User"
RUN_GENERAL_QUERY_ACTION = f"{INTEGRATION_NAME} - Run General Query"
ENRICH_ENDPOINT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich Endpoint"
ENRICH_FILE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich File"
ISOLATE_ENDPOINT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Isolate Endpoint"
UNISOLATE_ENDPOINT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Unisolate Endpoint"
UPDATE_INCIDENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Incident"
ADD_NOTE_TO_INCIDENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Note To Incident"

ATTACHMENT_NAME = "{}_pcap_file.pcap"
ENRICHMENT_PREFIX = "RSA_NTW"
SHA256_LENGTH = 64
MD5_LENGTH = 32

# Default Values
DEFAULT_RISK_SCORE_THRESHOLD = 50
DEFAULT_SIZE_OF_QUERY = "50"
DEFAULT_BROKER_ROOT = "http://x.x.x.x:50103"
DEFAULT_CONCENTRATOR_ROOT = "http://x.x.x.x:50105"
DEFAULT_UI_ROOT = "https://{ip}/rest/api/"
DEFAULT_HOURS_BACKWARDS = 1
DEFAULT_EVENTS_LIMIT = 50

# Payloads.
QUERY_REQUEST_PARAMETERS = {
    "msg": "query",
    "query": "select sessionid where ip.src=10.0.0.138",
    "size": 50,
}
GET_PCAP_FOR_SESSION_ID_PARAMETERS = {
    "render": "pcap",
    "sessions": "12335,35135,351355",
}
GET_METADATA_FOR_SESSION_ID_IN_RANGE_PARAMETERS = {
    "id1": "123",
    "id2": "123",
    "msg": "query",
    "query": "select *",
    "size": 50,
}
GET_METADATA_FOR_SESSION_ID_PARAMETERS = {
    "id1": "123",
    "id2": "123",
    "msg": "session",
    "size": 50,
}
PING_QUERY = "sdk?msg=query&query=select sessionid&size=1"

# Headers.
REQUEST_HEADERS = {"Accept": "application/json"}
UI_SESSION_HEADERS = {
    "NetWitness-Token": "",
    "Content-Type": "application/x-www-form-urlencoded",
}

# Queries Formats.
# Get session id.
GET_SESSION_ID_QUERY_FORMAT = "select sessionid where time >= {} AND {} GROUP BY sessionid ORDER BY sessionid desc"
GET_SESSION_ID_BASIC_QUERY = "select sessionid"

# RSA fields.
SOURCE_IP_FIELD = "ip.src"
DESTINATION_IP_FIELD = "ip.dst"
SOURCE_USER_FIELD = "user.src"
DESTINATION_USER_FIELD = "user.dst"
SOURCE_DOMAIN_FIELD = "domain.src"
DESTINATION_DOMAIN_FIELD = "domain.dst"

# Endpoints
OBTAIN_TOKEN_URL = "auth/userpass"
QUERY_URL = "/sdk"
PCAP_URL = "sdk/packets"
REQUIRED_SERVICE_ID_URL = "services?name=endpoint-server"
GET_HOSTS_URL = "hosts"
GET_FILES_URL = "files"
ISOLATE_ENDPOINT_URL = "host/{agent_id}/isolation"
UPDATE_INCIDENT_URL = "incidents/{incident_id}"
ADD_NOTE_URL = "incidents/{incident_id}/journal"
GET_INCIDENTS = "incidents"
GET_INCIDENT_ALERTS = "incidents/{incident_id}/alerts"

# Status Mapping
STATUS_MAPPING = {
    "New": "New",
    "Assigned": "Assigned",
    "In Progress": "InProgress",
    "Task Requested": "RemediationRequested",
    "Task Complete": "RemediationComplete",
    "Closed": "Closed",
    "Closed - False Positive": "ClosedFalsePositive",
}

# Connector
CONNECTOR_NAME = "RSA Netwitness Platform - Incidents Connector"
DEFAULT_FETCH_MAX_HOURS_BACKWARDS = 1
DEFAULT_FETCH_MAX_REPORTS = 10
DEFAULT_LOWEST_RISK_SCORE = 0
MIN_HOURS_BACKWARDS = 1

MIN_RISK_SCORE = 0
MAX_RISK_SCORE = 100
MIN_REPORTS_TO_FETCH = 0
MAX_REPORTS_TO_FETCH = 100

CONNECTOR_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
MAX_EVENTS_PER_ALERT = 99

DEFAULT_RULE_GENERATOR = "Netwitness Platform Alert"
INCIDENT_TIME_THRESHOLD_MINUTES = 5

SEVERITY_MAP = {
    "Informational": -1,
    "Low": 40,
    "Medium": 60,
    "High": 80,
    "Critical": 100,
}

DEFAULT_USERNAME_STRING = "default_username"
DEFAULT_PASSWORD_STRING = "default_password"

UNPROCESSED_INCIDENT_DB_KEY = "unprocessed_incident"
UNPROCESSED_INCIDENT_FILE_NAME = "unprocessed_incident.json"
