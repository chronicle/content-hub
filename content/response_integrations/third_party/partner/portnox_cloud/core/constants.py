from __future__ import annotations

INTEGRATION_IDENTIFIER = "PortnoxCloud"
INTEGRATION_DISPLAY_NAME = "Portnox Cloud"

DEFAULT_API_ROOT = "https://clear.portnox.com:8081/CloudPortalBackEnd/"
DEFAULT_BLOCK_REASON = "Blocked by Google SecOps SOAR"
DEFAULT_MAX_PAGES = 10
REQUEST_TIMEOUT_SECONDS = 60
MAX_RETRIES = 2

# Portnox Cloud enforces 10 requests per 10 seconds per tenant.
RATE_LIMIT_CALLS = 10
RATE_LIMIT_WINDOW_SECONDS = 10.0

# /api/device/list only accepts PageSize between 5 and 30.
MIN_PAGE_SIZE = 5
MAX_PAGE_SIZE = 30

RETRYABLE_STATUS_CODES = (429, 502, 503, 504)
ERROR_BODY_MAX_LENGTH = 500

ENRICHMENT_PREFIX = "Portnox"

ENDPOINTS = {
    "device_list": "api/device/list",
    "device_block": "api/device/block",
    "account_block": "api/account/block",
    "account_move_group": "api/account/move-to-group",
}

# Keys under which /api/device/list returns its list of account/device entries.
DEVICE_LIST_RESULT_KEYS = ("Entities", "AccountDevices", "Items", "Result", "Data")
