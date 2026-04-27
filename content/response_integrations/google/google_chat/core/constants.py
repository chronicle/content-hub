from __future__ import annotations
INTEGRATION_NAME = "GoogleChat"
VENDOR = "Google"
PRODUCT = "Google Chat"


# Action Script Names
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
LIST_SPACES_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Spaces"
SEND_MESSAGE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Send Message"
SEND_ADVANCED_MESSAGE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Send Advanced Message"

SHA256_HASH_FUNCTION = "crypt"

DEFAULT_LIMIT = 50

FILTER_KEY_MAPPING = {
    "Select One": "",
    "Name": "name",
    "Display Name": "displayName",
    "Type": "type",
}

EQUAL = "Equal"

# API status codes
API_CONFLICT_STATUS_CODE = 409
API_NOT_FOUND_STATUS_CODE = 404
API_BAD_REQUEST_STATUS_CODE = 400
API_NOT_AUTHORIZED_STATUS_CODE = 403

AUTHORIZATION_URL = (
    "https://accounts.google.com/o/oauth2/v2/auth?access_type=offline&scope=https://"
    "www.googleapis.com/auth/admin.directory.group.member%20https://www.googleapis.com/\
        auth/"
    "admin.directory.group%20https://www.googleapis.com/auth/admin.directory.orgunit%20\
        https://"
    "www.googleapis.com/auth/admin.directory.user%20https://www.googleapis.com/auth/"
    "admin.directory.user.alias&include_granted_scopes=true&"
    "redirect_uri={redirect_uri}&response_type=code&client_id={client_id}"
)

API_ROOT = "https://chat.googleapis.com"

SCOPES = ["https://www.googleapis.com/auth/chat.bot"]

ENDPOINTS = {
    "list-spaces": "/v1/spaces",
    "get-memberships": "/v1/{space}/members",
    "create-message": "/v1/spaces/{space_name}/messages",
}
