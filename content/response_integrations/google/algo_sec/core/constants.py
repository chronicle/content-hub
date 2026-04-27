from __future__ import annotations
INTEGRATION_NAME = "AlgoSec"
INTEGRATION_DISPLAY_NAME = "AlgoSec"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
BLOCK_IP_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Block IP"
ALLOW_IP_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Allow IP"
WAIT_FOR_CHANGE_REQUEST_STATUS_UPDATE_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Wait for Change Request Status Update"
)
LIST_TEMPLATES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - List Templates"

ENDPOINTS = {
    "authentication": "/FireFlow/api/authentication/authenticate",
    "ping": "/FireFlow/api/templates",
    "create_request": "/FireFlow/api/change-requests/traffic",
    "get_request_details": "/FireFlow/api/change-requests/traffic/{request_id}",
    "list_templates": "/FireFlow/api/templates",
}

BLOCK_ACTION = "Drop"
ALLOW_ACTION = "Allow"
ALL_ITEMS_STRING = "all"
DATETIME_ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DATETIME_API_FORMAT = "%Y-%m-%d %H:%M:%S"
ALLOW_DEAULT_SUBJECT = "Siemplify Allow IP request"
BLOCK_DEFAULT_SUBJECT = "Siemplify Block IP request"
POSSIBLE_STATUSES = [
    "resolved",
    "reconcile",
    "open",
    "check",
    "implementation plan",
    "implement",
    "validate",
]
DEFAULT_TIMEOUT = 300

DEFAULT_TEMPLATES_LIMIT = 50
EQUAL_FILTER = "Equal"
CONTAINS_FILTER = "Contains"
SLEEP_TIME = 10
