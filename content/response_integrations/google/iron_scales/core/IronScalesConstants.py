from __future__ import annotations
PROVIDER_NAME = "Iron Scales"

# ACTIONS
PING_SCRIPT_NAME = f"{PROVIDER_NAME} - Ping"
CLASSIFY_INCIDENT_NAME = f"{PROVIDER_NAME} - Classify Incident"
GET_INCIDENT_DETAILS_NAME = f"{PROVIDER_NAME} - Get Incident Details"
GET_MITIGATION_IMPERSONATION_DETAILS_NAME = (
    f"{PROVIDER_NAME} - Get Mitigation Impersonation Details"
)
GET_INCIDENT_MITIGATION_DETAILS_NAME = (
    f"{PROVIDER_NAME} - Get Incident Mitigation Details"
)
GET_MITIGATIONS_PER_MAILBOX_NAME = f"{PROVIDER_NAME} - Get Mitigations Per Mailbox"

ENDPOINTS = {
    "get_jwt_token": "appapi/get-token/",
    "test_connectivity": "appapi/company/{company_id}",
    "get_incident_details": "appapi/incident/{company_id}/details/{incident_id}",
    "classify_incident": "appapi/incident/{company_id}/classify/{incident_id}",
    "get_impersonation_details": "appapi/mitigation/{company_id}/impersonation/details/",
    "get_mitigation_details": "appapi/mitigation/{company_id}/incidents/details/",
    "get_mitigations_per_mailbox": "appapi/mitigation/{company_id}/details/",
}

HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

SCOPES_LIST_COMPANY = ["company.view", "company.all", "company.classify"]
SCOPES_LIST_PARTNER = [
    "partner.company.view",
    "partner.company.create",
    "partner.company.edit",
    "partner.all",
    "partner.company.classify",
]
DEFAULT_CLASSIFICATION_VALUE = "Attack"
DEFAULT_TIME_PERIOD = "Last 24 hours"
API_NOT_FOUND_ERROR = 404
DEFAULT_PAGE_QTY = 1

TIME_PERIOD_MAPPING = {
    "Last 24 hours": 0,
    "Last 7 days": 1,
    "Last 90 days": 2,
    "Last 180 days": 3,
    "Last 360 days": 4,
    "Current year to date": 5,
    "All time": 6,
}
