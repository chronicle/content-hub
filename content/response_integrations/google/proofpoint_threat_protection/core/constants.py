from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


INTEGRATION_IDENTIFIER: str = "ProofpointThreatProtection"
INTEGRATION_NAME: str = "Proofpoint Threat Protection"

PING_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Ping"
GET_ALLOW_LIST_ENTRIES_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Get Allow List Entries"
GET_BLOCK_LIST_ENTRIES_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Get Block List Entries"
ADD_ENTRY_TO_ALLOW_LIST_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - Add Entry To Allow List"
)
ADD_ENTRY_TO_BLOCK_LIST_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - Add Entry To Block List"
)
ADD_IOC_TO_ALLOW_LIST_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Add IOC To Allow List"
ADD_IOC_TO_BLOCK_LIST_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Add IOC To Block List"
REMOVE_ENTRY_FROM_ALLOW_LIST_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - Remove Entry From Allow List"
)
REMOVE_ENTRY_FROM_BLOCK_LIST_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - Remove Entry From Block List"
)

AUTH_URL: str = "https://auth.proofpoint.com/v1/token"
DEFAULT_VERIFY_SSL: bool = True

ENDPOINTS: Mapping[str, str] = {
    "get_allow_list_entries": "api/v1/emailProtection/modules/spam/orgSafeList",
    "add_allow_list_entry": "api/v1/emailProtection/modules/spam/orgSafeList",
    "add_block_list_entry": "api/v1/emailProtection/modules/spam/orgBlockList",
    "get_block_list_entries": "api/v1/emailProtection/modules/spam/orgBlockList",
    "remove_allow_list_entry": "api/v1/emailProtection/modules/spam/orgSafeList",
    "remove_block_list_entry": "/api/v1/emailProtection/modules/spam/orgBlockList",
}

MIN_ENTRIES_LIMIT: int = 1
MAX_ENTRIES_LIMIT: int = 1000
INVALID_ID_STATUS_CODE: int = 403
BAD_REQUEST_STATUS_CODE: int = 400
RATE_LIMIT_STATUS_CODE: int = 429
NULL: int = 0

DEFAULT_VENDOR: str = "Proofpoint Threat Protection"

IOC_TYPE_MAPPING: Mapping[str, str] = {
    "Recipient Email Address": "$rcpt",
    "Sender Email Address": "$from",
    "Sender IP Address": "$ip",
    "Sender Hostname": "$host",
    "Sender HELO Domain Name": "$helo",
    "Message Header From (Address Only)": "$hfrom",
}
IOC_TYPE_ALL: str = "All"

EMAIL_ATTRIBUTES_TO_VALIDATE: set[str] = {
    IOC_TYPE_MAPPING["Message Header From (Address Only)"],
    IOC_TYPE_MAPPING["Recipient Email Address"],
}

DUPLICATE_ENTRY_ERROR: str = "duplicate.entry"
ADD_ACTION: str = "add"
