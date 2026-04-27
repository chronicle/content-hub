from __future__ import annotations
INTEGRATION_NAME = "Intsights"
VENDOR = "Intsights"

PING_ACTION = f"{INTEGRATION_NAME} - Ping"
CLOSE_ALERT_ACTION = f"{INTEGRATION_NAME} - Close Alert"
ASSIGN_ALERT_ACTION = f"{INTEGRATION_NAME} - Assign Alert"
ASK_AN_ANALYST_ACTION = f"{INTEGRATION_NAME} - Ask An Analyst"
TAKEDOWN_REQUEST_ACTION = f"{INTEGRATION_NAME} - Takedown Request"
REOPEN_ALERT_ACTION = f"{INTEGRATION_NAME} - Reopen Alert"
GET_ALERT_IMAGE_ACTION = f"{INTEGRATION_NAME} - Get Alert Image"
SUBMIT_REMEDIATION_EVIDENCE_ACTION = f"{INTEGRATION_NAME} - Submit Remediation Evidence"
DOWNLOAD_ALERT_CSV_ACTION = f"{INTEGRATION_NAME} - Download Alert CSV"
SEARCH_IOCS_ACTION = f"{INTEGRATION_NAME} - SearchIOCs"
ADD_NOTE_ACTION = f"{INTEGRATION_NAME} - Add Note"


CONNECTOR_SCRIPT_NAME = f"{INTEGRATION_NAME} - Connector"
ALERT_FIELD_ID = "alert_id"

MAX_RATE = 5
MIN_RATE = 1

SUPPORTED_REMEDIATION_FILES_FORMATS = ["pdf", "jpeg", "txt", "png", "jpg"]

PRIORITIES = {"High": 80, "Medium": 60, "Low": 40}

ACTION_TYPE_ALERT = "ALERT"
ACTION_TYPE_USER = "USER"

# Requests
ASSIGN_ALERT_URL = "{}/public/v1/data/alerts/assign-alert/{}"
TAKEDOWN_REQUEST_URL = "{}/public/v1/data/alerts/takedown-request/{}"
SUBMIT_REMEDIATION_EVIDENCE_URL = (
    "{}/public/v1/data/alerts/upload-remediation-evidence/{}/{}/false"
)

REASON_MAPPING = {
    "Problem Solved": "ProblemSolved",
    "Informational Only": "InformationalOnly",
    "Problem We Are Aware Of": "ProblemWeAreAlreadyAwareOf",
    "Company Owned Domain": "CompanyOwnedDomain",
    "Legitimate Application/Profile": "LegitimateApplication/Profile",
    "Not Related To My Company": "NotRelatedToMyCompany",
    "False Positive": "FalsePositive",
    "Other": "Other",
}

SEVERITY_VALUES = ["Medium", "High"]
