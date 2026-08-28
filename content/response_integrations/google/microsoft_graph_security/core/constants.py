from __future__ import annotations
INTEGRATION_NAME = "MicrosoftGraphSecurity"
VENDOR = "Microsoft Graph Security"
DEVICE_PRODUCT = "AlertV2"
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
GET_ADMINISTRATOR_CONSENT_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Get Administrator Consent"
)
GET_ALERT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Alert"
KILL_USER_SESSION = f"{INTEGRATION_NAME} - Kill User Session"
LIST_ALERTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Alerts"
LIST_INCIDENTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Incidents"
GET_INCIDENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Incident"
UPDATE_ALERT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Alert"
ADD_ALERT_COMMENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Alert Comment"
API_COMMENT_LIMITATION = 1000
DEFAULT_MAX_RECORDS = 50
DEFAULT_API_PAGINATION_LIMIT = 200
ALERT_ID_FIELD = "id"

GRANT_TYPE = "client_credentials"
SCOPE = "https://graph.microsoft.com/.default"
CLIENT_ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"

# urls
URL_AUTHORIZATION = (
    "https://login.microsoftonline.com/{tenant}/"
    "adminconsent?client_id={client_id}&redirect_uri={redirect_uri}"
)
ACCESS_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
GET_ALERT_URL = "https://graph.microsoft.com/v1.0/security/alerts"
GET_ALERT_V2_URL = "https://graph.microsoft.com/v1.0/security/alerts_v2"
GET_INCIDENTS_URL = "https://graph.microsoft.com/v1.0/security/incidents"
GET_USERS_URL = "https://graph.microsoft.com/v1.0/users"
KILL_USER_URL = "https://graph.microsoft.com/v1.0/users/{}/revokeSignInSessions"
ADD_ALERT_COMMENT = "https://graph.microsoft.com/v1.0/security/alerts_v2/{}/comments"
GET_INCIDENT_URL = f"{GET_INCIDENTS_URL}/{{incident_id}}"

TOKEN_PAYLOAD = {
    "client_id": None,
    "scope": "https://graph.microsoft.com/.default",
    "client_secret": None,
    "grant_type": "client_credentials",
}
UPDATE_ALERT_HEADER = {"Prefer": "return=representation"}
FEEDBACK_VALUES = ["unknown", "truePositive", "falsePositive", "benignPositive"]
CLASSIFICATION_VALUES = [
    "unknown",
    "falsePositive",
    "truePositive",
    "informationalExpectedActivity",
    "unknownFutureValue",
]
STATUS_VALUES = ["unknown", "newAlert", "inProgress", "resolved"]
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

SEVERITY_MAP = {"high": 80, "medium": 60, "low": 40, "informational": -1, "unknown": -1}
VALID_ALERT_STATUSES = ["unknown", "newAlert", "inProgress", "resolved"]
VALID_ALERT_FEEDBACKS = ["unknown", "truePositive", "falsePositive", "benignPositive"]
VALID_ALERT_COMMENTS = ["Closed in IPC", "Closed in MCAS"]
EVENT_STATES = [
    "fileStates",
    "hostStates",
    "malwareStates",
    "networkConnections",
    "registryKeyStates",
    "triggers",
    "userStates",
    "vulnerabilityStates",
    "cloudAppStates",
    "processes",
    "alertDetections",
    "historyStates",
    "investigationSecurityStates",
    "messageSecurityStates",
    "securityResources",
    "uriClickSecurityStates",
]
CONTAINS_FILTER_NOT_SUPPORTED_ERROR = (
    "no function signature for the function with name 'contains' "
    "matches the specified arguments."
)
