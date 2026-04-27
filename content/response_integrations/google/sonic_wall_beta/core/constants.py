from __future__ import annotations
INTEGRATION_NAME = "SonicWall-Beta"

PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
ADD_IP_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add IP to Address Group"
REMOVE_IP_SCRIPT_NAME = f"{INTEGRATION_NAME} - Remove IP from Address Group"
ADD_URL_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add URL to URI List"
LIST_ADDRESS_GROUPS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Address Groups"
ADD_URI_TO_GROUP_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add URI List to URI Group"
REMOVE_URL_SCRIPT_NAME = f"{INTEGRATION_NAME} - Remove URL from URI List"
LIST_URI_LISTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List URI Lists"
LIST_URI_GROUPS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List URI Groups"
CREATE_CFS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create CFS Profile"

ENDPOINTS = {
    "auth": "api/sonicos/auth",
    "ping": "api/sonicos/user/status/all",
    "address_groups": "/api/sonicos/address-groups/{ip_type}/name/{group_name}",
    "create_address": "/api/sonicos/address-objects/{ip_type}",
    "confirm": "/api/sonicos/config/pending",
    "all_addresses": "/api/sonicos/address-objects/{ip_type}",
    "add_url": "/api/sonicos/content-filter/uri-list-objects/name/{uri_list}",
    "get_address_groups": "/api/sonicos/address-groups/{ip_type}",
    "delete_url": "/api/sonicos/content-filter/uri-list-objects",
    "get_uri_lists": "/api/sonicos/content-filter/uri-list-objects",
    "add_uri_to_group": "/api/sonicos/content-filter/uri-list-groups",
    "list_groups": "/api/sonicos/content-filter/uri-list-groups",
    "create_cfs_profile": "/api/sonicos/content-filter/profiles",
}

HEADERS = {
    "Accept": "application/json",
    "Accept-Encoding": "*/*",
    "Content-Type": "application/json",
}

NO_MATCH_ERROR_CODE = "E_NO_MATCH"
UNAUTHORIZED_ERROR_CODE = "E_UNAUTHORIZED"
NOT_FOUND_ERROR_CODE = "E_NOT_FOUND"
GENERAL_ERROR_CODE = "E_ERROR"

IPV4_TYPE_STRING = "ipv4"
IPV6_TYPE_STRING = "ipv6"
ALL_TYPE_STRING = "all"
MAX_LIMIT = 100
ALLOWED_URI_FIRST_STRING = "Allowed URI First"
