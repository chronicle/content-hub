from __future__ import annotations
PROVIDER_NAME = "TenableSecurityCenter"
HEADERS = {"Content-Type": "application/json"}
OFFSET = 50
CONNECTIVITY_ERROR_MESSAGE = "Failed to connect to Tenable Security Center"

# Actions
RUN_ASSET_SCAN_SCRIPT_NAME = f"{PROVIDER_NAME} - Run Asset Scan"
CREATE_IP_LIST_ASSET_SCRIPT_NAME = f"{PROVIDER_NAME} - Create IP List Asset"
ADD_IP_TO_LIST_ASSET_SCRIPT_NAME = f"{PROVIDER_NAME} - Add IP To IP List Asset"
SCRIPT_NAME = "TenableSecurityCenter - EnrichIP"


ENDPOINTS = {
    "get_assets": "/rest/asset",
    "scan": "/rest/scan",
    "asset_details": "/rest/asset/{asset_id}",
}


UNIX_FORMAT = 1
DATETIME_FORMAT = 2
DAY_IN_MILLISECONDS = 86400000
