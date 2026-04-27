from __future__ import annotations
INTEGRATION_NAME = "InternetStormCenter"
INTEGRATION_DISPLAY_NAME = "Internet Storm Center"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
ENRICH_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich Entities"

API_ROOT = "http://isc.sans.edu"
ENDPOINTS = {
    "ping": "/api/handler?json=null",
    "get_device": "/api/ip/{address}?json=null",
}

DEFAULT_TIMEOUT = 300
