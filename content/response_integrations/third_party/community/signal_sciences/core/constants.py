from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

INTEGRATION_IDENTIFIER: str = "SignalSciences"
INTEGRATION_DISPLAY_NAME: str = "SignalSciences"

# Script Identifiers
PING_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Ping"

# Default Configuration Parameter Values
DEFAULT_API_ROOT: str = "https://dashboard.signalsciences.net"
DEFAULT_VERIFY_SSL: bool = True

# API Constants
ENDPOINTS: Mapping[str, str] = {
    "ping": "/ping",
    "list-sites": "sites",
    "get-allowlist": "sites/{site_name}/whitelist",
    "get-blocklist": "sites/{site_name}/blacklist",
    "add-allowlist-item": "sites/{site_name}/whitelist",
    "add-blocklist-item": "sites/{site_name}/blacklist",
    "delete-allowlist-item": "sites/{site_name}/whitelist/{item_id}",
    "delete-blocklist-item": "sites/{site_name}/blacklist/{item_id}",
}

# Timeouts
REQUEST_TIMEOUT: int = 30
