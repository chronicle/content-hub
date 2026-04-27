from __future__ import annotations
INTEGRATION_NAME = "GoogleGRR"
INTEGRATION_DISPLAY_NAME = "Google GRR"

# Error Codes:
API_UNAUTHORIZED_ERROR = 401
API_NOT_FOUND_ERROR = 404
API_BAD_REQUEST = 400

# Error Messages
INVALID_HUNT_ID = "invalid literal for int() with base 16"

WEEK_IN_SECONDS = 604800


UTC = "UTC"

HUNT_URL_PART = "/#/hunts/"

# Actions Names:
PING = "Ping"
LIST_CLIENTS = "List Clients"
GET_CLIENT_DETAILS = "Get Client Details"
LIST_LAUNCHED_FLOWS = "List Launched Flows"
GET_HUNT_DETAILS = "Get Hunt Details"
LIST_HUNTS = "List Hunts"
STOP_A_HUNT = "Stop a Hunt"
START_A_HUNT = "Start a Hunt"

STOP_STATE = "STOPPED"
START_STATE = "STARTED"
PAUSE_STATE = "PAUSED"
