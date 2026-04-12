from __future__ import annotations

# Integration Identifiers
INTEGRATION_IDENTIFIER = "SignalSciences"
INTEGRATION_DISPLAY_NAME = "Signal Sciences"

# API Constants
DEFAULT_API_ROOT = "https://dashboard.signalsciences.net"
API_BASE_PATH = "/api/v0"

# Endpoints
GET_CORP_ENDPOINT = "/corps/{corp_name}"
ALLOW_LIST_ENDPOINT = "/corps/{corp_name}/sites/{site_name}/whitelist"
ALLOW_LIST_ITEM_ENDPOINT = "/corps/{corp_name}/sites/{site_name}/whitelist/{item_id}"
BLOCK_LIST_ENDPOINT = "/corps/{corp_name}/sites/{site_name}/blacklist"
BLOCK_LIST_ITEM_ENDPOINT = "/corps/{corp_name}/sites/{site_name}/blacklist/{item_id}"
LIST_SITES_ENDPOINT = "/corps/{corp_name}/sites"

LIMIT_SITES_PARAM = 10
