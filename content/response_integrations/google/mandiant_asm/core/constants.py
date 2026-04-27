from __future__ import annotations
from dateutil.relativedelta import relativedelta


ENDPOINTS = {
    "index_projects": {"non_gti": "/api/v1/projects", "gti": "/api/v3/asm/projects"},
    "update_issue": {
        "non_gti": "/api/v1/issues/{issue_id}/status",
        "gti": "/api/v3/asm/issues/{issue_id}/status",
    },
    "get_issues": {
        "non_gti": (
            "/api/v1/search/issues/first_seen_after:{first_seen_after} "
            "last_seen_after:last_refresh severity_lte:{severity} status_new:open"
        ),
        "gti": (
            "/api/v3/asm/search/issues/first_seen_after:{first_seen_after} "
            "last_seen_after:last_refresh severity_lte:{severity} status_new:open"
        ),
    },
    "get_issue_details": {
        "non_gti": "/api/v1/issues/{issue_id}",
        "gti": "/api/v3/asm/issues/{issue_id}",
    },
    "search_entities": {
        "non_gti": "/api/v1/search/entities/{query_string}",
        "gti": "/api/v3/asm/search/entities/{query_string}",
    },
    "search_issues": {
        "non_gti": "/api/v1/search/issues/severity_lte:{severity} {query_string}",
        "gti_search_issues": (
            "/api/v3/asm/search/issues/severity_lte:{severity} {query_string}"
        ),
    },
    "entity_full_details": {
        "non_gti": "api/v1/entities/{entity_id}/raw",
        "gti": "api/v3/asm/entities/{entity_id}/raw",
    },
}

INTEGRATION_NAME = "MandiantASM"
INTEGRATION_DISPLAY_NAME = "Mandiant ASM"

DEFAULT_DEVICE_PRODUCT = "Mandiant ASM"
DEFAULT_DEVICE_VENDOR = "Mandiant ASM"
DEFAULT_PAGE = 0
DEFAULT_PAGE_SIZE = 100

DEFAULT_SEARCH_ISSUES_LIMIT = "50"
MAX_SEARCH_ISSUES_LIMIT = 200
MAX_SEARCH_ENTITIES_LIMIT = 200
STATUS_MAPPING = {"Open": "open", "Closed": "closed"}
TIME_FRAME_MAPPING = {
    "Last Hour": relativedelta(hours=1),
    "Last 6 Hours": relativedelta(hours=6),
    "Last 24 Hours": relativedelta(hours=24),
    "Last Week": relativedelta(days=7),
    "Last Month": relativedelta(months=1),
}

PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
SEARCH_ISSUES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Search Issues"
UPDATE_ISSUE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Issue"
SEARCH_ASM_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Search ASM Entities"
GET_ASM_ENTITY_DETAILS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get ASM Entity Details"

ISSUE_STATUS_MAPPING = {
    "New": "open_new",
    "Triaged": "open_triaged",
    "In Progress": "open_in_progress",
    "Resolved": "closed_resolved",
    "Duplicate": "closed_duplicate",
    "Out Of Scope": "closed_out_of_scope",
    "Not A Security Issue (Benign)": "closed_benign",
    "Risk Accepted": "closed_risk_accepted",
    "False Positive": "closed_false_positive",
    "Unable To Reproduce": "closed_no_repro",
    "Tracked Externally": "closed_tracked_externally",
    "Mitigated": "closed",
}

SEVERITY_MAPPING = {"critical": 1, "high": 2, "medium": 3, "low": 4, "informational": 5}

PRIORITY_MAPPING = {1: 100, 2: 80, 3: 60, 4: 40, 5: -1}

POSSIBLE_SEVERITIES = ["Informational", "Low", "Medium", "High", "Critical"]
ISSUES_CONNECTOR_NAME = "Mandiant ASM - Issues Connector"

DATETIME_FORMAT_FOR_CONNECTOR = "%Y-%m-%dT%H:%M:%SZ"
DEFAULT_LIMIT_FOR_CONNECTOR = 10
DEFAULT_HOURS_BACKWARDS = 1

TIMEOUT_THRESHOLD = 0.9

WRONG_API_ERROR_MESSAGE = (
    "Invalid Credentials or Wrong API Key. Please verify the 'Client ID,' "
    "'Client Secret,' or 'GTI API Key'."
)
ERROR_CODE = {"code": "WrongCredentialsError", "message": "Wrong API key"}
