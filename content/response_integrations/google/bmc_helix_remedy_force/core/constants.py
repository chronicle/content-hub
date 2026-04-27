from __future__ import annotations
INTEGRATION_NAME = "BMC Helix Remedyforce"
INTEGRATION_IDENTIFIER = "BMCHelixRemedyForce"
PING_ACTION = f"{INTEGRATION_NAME} - Ping"
CREATE_RECORD_ACTION = f"{INTEGRATION_NAME} - Create Record"
DELETE_RECORD_ACTION = f"{INTEGRATION_NAME} - Delete Record"
UPDATE_RECORD_ACTION = f"{INTEGRATION_NAME} - Update Record"
GET_RECORD_DETAILS_ACTION = f"{INTEGRATION_NAME} - Get Record Details"
EXECUTE_CUSTOM_QUERY_ACTION = f"{INTEGRATION_NAME} - Execute Custom Query"
LIST_RECORD_TYPES_ACTION = f"{INTEGRATION_NAME} - List Record Types"
WAIT_FOR_FIELD_UPDATE_ACTION = f"{INTEGRATION_NAME} - Wait For Field Update"
EXECUTE_SIMPLE_ACTION = f"{INTEGRATION_NAME} - Execute Simple Query"
GET_AUTHORIZATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get OAuth Authorization Code"
GENERATE_TOKEN_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get OAuth Refresh Token"

ENDPOINTS = {
    "test_connectivity": "/services/data/v51.0/query/?q=SELECT FIELDS(ALL) from Account LIMIT 1",
    "get_session_id": "/services/Soap/u/35.0",
    "create_record": "/services/data/v51.0/sobjects/{record_type}",
    "manage_record": "/services/data/v51.0/sobjects/{record_type}/{record_id}",
    "execute_query": "/services/data/v51.0/query/",
    "get_objects": "/services/data/v51.0/sobjects/",
    "get_incidents": "/services/data/v51.0/query/",
    "login": "/services/oauth2/token",
}

OAUTH_URL = "https://login.salesforce.com/services/oauth2/token"

EQUAL_FILTER = "Equal"
CONTAINS_FILTER = "Contains"

# Connector
CONNECTOR_NAME = f"{INTEGRATION_NAME} - Incidents Connector"
DEFAULT_PRIORITY = 5
DEFAULT_TIME_FRAME = 1
DEFAULT_LIMIT = 10
MAX_LIMIT = 200
LIMIT_PER_REQUEST = 100
DEVICE_VENDOR = "BMC Helix Remedyforce"
DEVICE_PRODUCT = "BMC Helix Remedyforce"
API_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

SEVERITY_MAP = {"5": -1, "4": 40, "3": 60, "2": 80, "1": 100}
ASYNC_ACTION_TIMEOUT_THRESHOLD_MS = 30 * 1000

TIME_FRAME_LAST_HOUR = "Last Hour"
TIME_FRAME_LAST_6HOURS = "Last 6 Hours"
TIME_FRAME_LAST_24HOURS = "Last 24 Hours"
TIME_FRAME_LAST_WEEK = "Last Week"
TIME_FRAME_LAST_MONTH = "Last Month"
TIME_FRAME_CUSTOM = "Custom"

SORT_ORDER_ASC = "ASC"
SORT_ORDER_DESC = "DESC"

LIMIT_MAX = 200
