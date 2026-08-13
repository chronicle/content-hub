"""Constants for Abnormal Security Google SecOps SOAR Integration."""

INTEGRATION_NAME = "AbnormalSecurity"
INTEGRATION_DISPLAY_NAME = "Abnormal Security"
USER_AGENT = "Abnormal-Google-SecOps-SOAR/1.0"

API_VERSION = "v1"

# Search & Respond endpoints
MESSAGES_SEARCH_ENDPOINT = f"/{API_VERSION}/search"
MESSAGES_REMEDIATE_ENDPOINT = f"/{API_VERSION}/search/remediate"
ACTIVITIES_LIST_ENDPOINT = f"/{API_VERSION}/search/activities"
ACTIVITY_STATUS_ENDPOINT = f"/{API_VERSION}/search/activities/{{activity_log_id}}/status"

# Threats endpoints
THREATS_ENDPOINT = f"/{API_VERSION}/threats"
THREAT_BY_ID_ENDPOINT = f"/{API_VERSION}/threats/{{threat_id}}"
THREAT_ATTACHMENTS_ENDPOINT = f"/{API_VERSION}/threats/{{threat_id}}/attachments"
THREAT_LINKS_ENDPOINT = f"/{API_VERSION}/threats/{{threat_id}}/links"
THREAT_ACTION_ENDPOINT = f"/{API_VERSION}/threats/{{threat_id}}/actions/{{action_id}}"

# Cases endpoints
CASES_ENDPOINT = f"/{API_VERSION}/cases"
CASE_BY_ID_ENDPOINT = f"/{API_VERSION}/cases/{{case_id}}"
CASE_ANALYSIS_ENDPOINT = f"/{API_VERSION}/cases/{{case_id}}/analysis"
CASE_ACTION_ENDPOINT = f"/{API_VERSION}/cases/{{case_id}}/actions/{{action_id}}"

# Inquiry endpoint
INQUIRY_ENDPOINT = f"/{API_VERSION}/inquiry"

# HTTP Configuration
DEFAULT_API_URL = "https://api.abnormalplatform.com"
DEFAULT_TIMEOUT = 30
DEFAULT_VERIFY_SSL = True
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 1
# 429 is excluded — handled immediately by AbnormalRateLimitError, not retried
RETRY_STATUS_CODES = [500, 502, 503, 504]

# S&R remediation values
VALID_REMEDIATION_ACTIONS = ["delete", "move_to_inbox", "submit_to_d360"]
VALID_REMEDIATION_REASONS = [
    "false_negative",
    "unsolicited",
    "other",
    "groups_remediation",
    "quarantine_release",
]
VALID_SEARCH_SOURCES = ["abnormal", "quarantine"]

# Threat actions
VALID_THREAT_ACTIONS = ["remediate", "unremediate"]

# Case actions — must match EXPECTED_OPERATION keys in soar/constants.py
VALID_CASE_ACTIONS = [
    "action_required",
    "acknowledge_resolved",
    "acknowledge_in_progress",
    "acknowledge_not_an_attack",
]

# Inquiry report types
VALID_INQUIRY_REPORT_TYPES = ["false-positive", "false-negative"]

# Activity terminal statuses — everything except "pending"
TERMINAL_STATUSES = {"success", "partial_success", "error"}

# HTTP headers
HEADER_AUTHORIZATION = "Authorization"
HEADER_CONTENT_TYPE = "Content-Type"
HEADER_USER_AGENT = "User-Agent"
# Identifies SOAR-originated API calls to the Abnormal Security backend. The
# Abnormal SOAR API reads this header to apply the Google SecOps egress subnet
# allowlist and origin metrics; without it requests default to "Rest API".
HEADER_SOAR_INTEGRATION_ORIGIN = "Soar-Integration-Origin"
SOAR_INTEGRATION_ORIGIN = "Google SecOps"
CONTENT_TYPE_JSON = "application/json"

# Connector
CONNECTOR_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Threats and Cases Connector"
DEVICE_VENDOR = INTEGRATION_DISPLAY_NAME
DEVICE_PRODUCT_THREAT = "Threat"
DEVICE_PRODUCT_CASE = "Case"
DEFAULT_MAX_DAYS_BACKWARDS = 1
DEFAULT_MAX_ALERTS_PER_CYCLE = 50
IDS_CACHE_HOURS = 72

# Action script names — existing
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
SEARCH_MESSAGES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Search Messages"
REMEDIATE_MESSAGES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Remediate Messages"
GET_ACTIVITY_STATUS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Get Activity Status"
GET_THREAT_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Get Threat"
LIST_THREATS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - List Threats"
POST_THREAT_ACTION_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Post Threat Action"
GET_CASE_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Get Case"
LIST_CASES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - List Cases"
POST_CASE_ACTION_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Post Case Action"

# Action script names — new
LIST_ACTIVITIES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - List Activities"
GET_THREAT_ATTACHMENTS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Get Threat Attachments"
GET_THREAT_LINKS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Get Threat Links"
GET_CASE_ANALYSIS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Get Case Analysis"
SUBMIT_INQUIRY_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Submit Inquiry"

# Action script names — specific verb actions (replacements for generic Post X Action)
REMEDIATE_THREAT_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Remediate Threat"
UNREMEDIATE_THREAT_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Unremediate Threat"
MARK_CASE_ACTION_REQUIRED_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Mark Case Action Required"
RESOLVE_CASE_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Resolve Case"
MARK_CASE_IN_PROGRESS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Mark Case In Progress"
MARK_CASE_NOT_AN_ATTACK_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Mark Case Not An Attack"
DELETE_MESSAGES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Delete Messages"
MOVE_MESSAGES_TO_INBOX_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Move Messages To Inbox"
SUBMIT_MESSAGES_TO_D360_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Submit Messages To D360"

# Error messages
ERROR_MSG_AUTH_FAILED = "Authentication failed. Please verify your API key."
ERROR_MSG_CONNECTION_ERROR = "Connection error. Please verify network connectivity and API URL."
ERROR_MSG_TIMEOUT = "Request timed out. Please try again."
ERROR_MSG_INVALID_RESPONSE = "Invalid response from API. Please contact support."
ERROR_MSG_RATE_LIMIT = "Rate limit exceeded. Please retry after some time."
ERROR_MSG_SERVER_ERROR = "Server error occurred. Please try again later."
ERROR_MSG_INVALID_ACTION = "Invalid remediation action specified."
ERROR_MSG_INVALID_REASON = "Invalid remediation reason specified."
ERROR_MSG_NO_MESSAGES = "No messages provided for remediation."
ERROR_MSG_MISSING_ACTIVITY_ID = "Activity log ID is required."
ERROR_MSG_MISSING_TENANT_IDS = "Tenant IDs are required."
ERROR_MSG_MISSING_THREAT_ID = "Threat ID is required."
ERROR_MSG_MISSING_CASE_ID = "Case ID is required."
ERROR_MSG_INVALID_THREAT_ACTION = "Invalid threat action specified."
ERROR_MSG_INVALID_CASE_ACTION = "Invalid case action specified."
ERROR_MSG_INVALID_INQUIRY_REPORT_TYPE = "Invalid inquiry report_type specified."
ERROR_MSG_MISSING_INQUIRY_REPORTER = "Inquiry reporter is required."
