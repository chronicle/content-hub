"""
Constants for Abnormal Security Google SecOps SOAR Integration.
"""

# Integration Information
INTEGRATION_NAME = "AbnormalSecurity"
INTEGRATION_DISPLAY_NAME = "Abnormal Security"
USER_AGENT = "Abnormal-Google-SecOps-SOAR/1.0"

# API Endpoints
DEFAULT_API_URL = "https://api.abnormalplatform.com"
API_VERSION = "v1"

MESSAGES_SEARCH_ENDPOINT = f"/{API_VERSION}/messages/search"
MESSAGES_REMEDIATE_ENDPOINT = f"/{API_VERSION}/messages/remediate"
ACTIVITY_STATUS_ENDPOINT = f"/{API_VERSION}/messages/activities/{{activity_log_id}}/status"
THREATS_ENDPOINT = f"/{API_VERSION}/threats"

# HTTP Configuration
DEFAULT_TIMEOUT = 30
DEFAULT_VERIFY_SSL = True
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 1
RETRY_STATUS_CODES = [429, 500, 502, 503, 504]

# Remediation Action Types
VALID_REMEDIATION_ACTIONS = ["delete", "move_to_inbox", "submit_to_d360", "reclassify"]

# Remediation Reason Types
VALID_REMEDIATION_REASONS = ["false_negative", "false_positive", "manual_remediation"]

# Activity Terminal Statuses
TERMINAL_STATUSES = {"success", "failed", "completed"}

# HTTP Headers
HEADER_AUTHORIZATION = "Authorization"
HEADER_CONTENT_TYPE = "Content-Type"
HEADER_USER_AGENT = "User-Agent"
CONTENT_TYPE_JSON = "application/json"

# Action Script Names
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
SEARCH_MESSAGES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Search Messages"
REMEDIATE_MESSAGES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Remediate Messages"
GET_ACTIVITY_STATUS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Get Activity Status"

# Error Messages
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

# Success Messages
SUCCESS_MSG_CONNECTIVITY = "Successfully connected to Abnormal Security API."
