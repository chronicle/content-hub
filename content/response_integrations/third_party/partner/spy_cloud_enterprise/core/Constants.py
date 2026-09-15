from __future__ import annotations

INTEGRATION_NAME = "SpyCloud Enterprise"
INTEGRATION_DISPLAY_NAME = "SpyCloud Enterprise"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
GET_WATCHLIST_EXPOSURES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Get Watchlist Exposures"
FILTER_PASSWORDS_BY_POLICY_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Filter Passwords By Policy"
)
CHECK_PASSWORD_ROTATION_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Check Password Rotation"
)

ENDPOINT_PING = "/enterprise-v2/breach/catalog/1"
ENDPOINT_BREACH_CATALOG = "/enterprise-v2/breach/catalog"
ENDPOINT_BREACH_DATA_WATCHLIST = "/enterprise-v2/breach/data/watchlist"

# Compass
ENDPOINT_COMPASS_DATA = "/enterprise-v2/compass/data"
ENDPOINT_COMPASS_DEVICES = "/enterprise-v2/compass/devices"
ENDPOINT_COMPASS_DEVICE_DETAILS = "/enterprise-v2/compass/data/devices/{infected_machine_id}"
ENDPOINT_COMPASS_APPLICATIONS = "/enterprise-v2/compass/applications"
ENDPOINT_COMPASS_APPLICATION_DETAILS = "/enterprise-v2/compass/data/applications/{target_application}"