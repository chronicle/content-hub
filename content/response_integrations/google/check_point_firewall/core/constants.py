from __future__ import annotations
INTEGRATION_NAME = "CheckPointFirewall"

# ACTIONS
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
ADD_A_SAM_RULE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add a SAM Rule"
REMOVE_SAM_RULE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Remove SAM Rule"
ADD_IP_TO_GROUP_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Ip to Group"
ADD_URL_TO_GROUP_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Url to Group"
LIST_LAYERS_ON_SITE_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Layers on Site"
LIST_POLICIES_ON_SITE_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Policies on Site"
REMOVE_IP_FROM_GROUP_SCRIPT_NAME = f"{INTEGRATION_NAME} - Remove Ip From Group"
REMOVE_URL_FROM_GROUP_SCRIPT_NAME = f"{INTEGRATION_NAME} - Remove Url From Group"
RUN_SCRIPT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Remove Url From Group"
SHOW_LOGS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Show Logs"
DOWNLOAD_LOG_ATTACHMENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Download Log Attachment"

REMOVE_SAM_RULE_DEFAULT_MSG = "Siemplify-generated-script-remove-sam-rule"
# CSV FILE NAMES
ACCESS_CONTROL_LAYERS_CSV_NAME = "Access Control Layers"
THREAT_PREVENTION_CONTROL_LAYERS_CSV_NAME = "Threat Prevention Control Layers"
RESULTS_CSV_NAME = "Results"

# ATTACHMENTS SIZE LIMIT
ATTACHMENT_SIZE_LIMIT_MB = 3
# DEFAULT DELIMITER
PARAMETERS_DEFAULT_DELIMITER = ","
PARAMETERS_NEW_LINE_DELIMITER = "\n"

# SLEEP CONSTANT
SLEEP_TIME = 5

TIME_FRAME_MAPPING = {
    "Today": "today",
    "Yesterday": "yesterday",
    "Last Hour": "last-hour",
    "Last 24 Hours": "last-24-hours",
    "Last 30 Days": "last-30-days",
    "This Week": "this-week",
    "This Month": "this-month",
    "All Time": "all-time",
}

# Log type mapping
LOG_MAPPING = {"Log": "logs", "Audit": "audit"}

# ERROR_CODES
NOT_FOUND_CODE = 404
INVALID_PARAMETERS_CODE = 400
