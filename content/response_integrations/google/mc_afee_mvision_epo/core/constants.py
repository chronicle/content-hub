from __future__ import annotations
INTEGRATION_NAME = "McAfeeMvisionEPO"
INTEGRATION_DISPLAY_NAME = "McAfee Mvision ePO"

IAM_URL = "https://iam.mcafee-cloud.com/iam/v1.2/token"
AUTH_PAYLOAD = {
    "grant_type": "client_credentials",
    "audience": "mcafee",
    "scope": "epo.device.r epo.device.w epo.grps.r epo.grps.w epo.sftw.r epo.tags.r epo.tags.w",
}

HEADERS = {"Content-Type": "application/json"}

PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
ADD_TAG_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Tag"
REMOVE_TAG_SCRIPT_NAME = f"{INTEGRATION_NAME} - Remove Tag"
ENRICH_ENDPOINT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich Endpoint"
ENRICHMENT_PREFIX = "MMV_EPO"
LIST_GROUPS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Groups"
LIST_TAGS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Tags"
LIST_ENDPOINTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Endpoints In Group"
PER_PAGE_LIMIT = 100
DEFAULT_LIMIT_GROUPS = 100
DEFAULT_LIMIT_ENDPOINTS = 100
DEFAULT_LIMIT_TAGS = 100
