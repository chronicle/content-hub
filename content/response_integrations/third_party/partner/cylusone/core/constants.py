"""Constants for CylusOne integration."""

INTEGRATION_NAME = "CylusOne"
DEFAULT_TIMEOUT = 10

ERRORS = {
    "ACTION": {"FAILED": "Failed to execute action in CylusOne:"},
    "CONNECTIVITY": {
        "FAILED": "Failed to connect to the CylusOne platform",
        "INVALID_CREDENTIALS": "Invalid API credentials",
        "TIMEOUT": "Connection timeout",
    },
}

# API endpoints
ENDPOINTS = {
    "ASSETS_BY_IP": "/rest/v1/assets/by-ip?ip={ip}",
}
