from __future__ import annotations
INTEGRATION_NAME = "MicrosoftIntune"
INTEGRATION_DISPLAY_NAME = "Microsoft Intune"

# ACTION NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
LIST_MANAGED_DEVICES_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Managed Devices"
GET_MANAGED_DEVICE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Managed Device"
SYNC_MANAGED_DEVICE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Sync Managed Device"
LOCATE_MANAGED_DEVICE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Locate Managed Device"
WIPE_MANAGED_DEVICE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Wipe Managed Device"
RESET_MANAGED_DEVICE_PASSCODE_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Reset Managed Device Passcode"
)
REMOTE_LOCK_MANAGED_DEVICE_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Remote Lock Managed Device"
)

# ACCESS CONSTANTS
AZURE_AD_ENDPOINT_DEFAULT_VALUE = "https://login.microsoftonline.com"
MICROSOFT_GRAPH_ENDPOINT_DEFAULT_VALUE = "https://graph.microsoft.com"
HEADERS = {"Content-Type": "application/json"}
GRANT_TYPE = "client_credentials"
SCOPE = "https://graph.microsoft.com/.default"
RESOURCE = "https://graph.microsoft.com"

# ENDPOINTS
ENDPOINTS = {
    "ping": "{base_url}/{azure_ad_id}/oauth2/token",
    "locate_managed_device": (
        "{base_url}/v1.0/deviceManagement/managedDevices/{host_id}/locateDevice"
    ),
    "list_managed_devices": (
        "{base_url}/v1.0/deviceManagement/managedDevices" "?$top={page_size}"
    ),
    "reset_managed_device": (
        "{base_url}/v1.0/deviceManagement/managedDevices/{host_id}" "/resetPasscode"
    ),
    "remote_lock_managed_device": (
        "{base_url}/v1.0/deviceManagement/managedDevices/{host_id}/remoteLock"
    ),
    "sync_managed_device": (
        "{base_url}/v1.0/deviceManagement/managedDevices/{host_id}/syncDevice"
    ),
    "wipe_managed_device": (
        "{base_url}/v1.0/deviceManagement/managedDevices/{host_id}/wipe"
    ),
    "get_managed_device": ("{base_url}/v1.0/deviceManagement/managedDevices/{host_id}"),
}

# API Status Codes
API_BAD_REQUEST = 400
API_SERVER_ERROR = 500
API_NOT_FOUND = 404
API_UNAUTHORIZED_ERROR = 401

# PAYLOADS
GENERATE_TOKEN_PAYLOAD_FROM_SECRET = {
    "grant_type": GRANT_TYPE,
    "client_id": "",
    "scope": SCOPE,
    "client_secret": "",
    "resource": RESOURCE,
}

# List Managed Devices Constants
FILTER_KEY_DEFAULT_VALUE = "Select One"
FILTER_LOGIC_DEFAULT_VALUE = "Not Specified"
FILTER_VALUE_DEFAULT_VALUE = ""
MAX_RECORDS_TO_RETURN_DEFAULT_VALUE = 50
LIST_DEVICE_TABLE_NAME = "Available Managed Devices"
FILTER_LOGIC_EQUAL = "Equal"
FILTER_LOGIC_CONTAINS = "Contains"
DEFAULT_CONTEXT = (
    "https://graph.microsoft.com/v1.0/$metadata#deviceManagement/managedDevices"
)
