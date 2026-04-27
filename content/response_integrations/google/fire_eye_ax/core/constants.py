from __future__ import annotations
INTEGRATION_NAME = "FireEyeAX"
INTEGRATION_DISPLAY_NAME = "FireEye AX"

# ACTIONS
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
GET_APPLIANCE_DETAILS_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Get Appliance Details"
)
SUBMIT_URL_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Submit URL"
SUBMIT_FILE_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Submit File"

ENDPOINTS = {
    "authorize": "wsapis/v2.0.0/auth/login",
    "ping": "wsapis/v2.0.0/config",
    "get_appliance_details": "wsapis/v2.0.0/config",
    "get_data": "wsapis/v2.0.0/submissions/url",
    "get_submission_status": "wsapis/v2.0.0/submissions/status/{submission_id}",
    "get_submission_details": "wsapis/v2.0.0/submissions/results/{result_id}?info_level=extended",
    "submit_file": "wsapis/v2.0.0/submissions",
}

HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

PRIORITY_MAPPING = {"Normal": 0, "Urgent": 1}

ANALYSIS_TYPE_MAPPING = {"Live": 1, "Sandbox": 2}

SUBMISSION_DONE = "Submission Done"
DEFAULT_TIMEOUT = 300
