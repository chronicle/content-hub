"""Constants for the GOQR integration."""

# INTEGRATION IDENTIFIER
INTEGRATION_IDENTIFIER = "GOQR"

# ACTIONS NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER}- Ping"
GENERATE_QR_CODE_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Generate QR Code"
SCAN_QR_CODE_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Scan QR Code"

# API
ENDPOINTS = {
    "ping": "v1/create-qr-code/?data=PingCheck&size=100x100",
    "create_qr_code": "v1/create-qr-code/",
    "read_qr_code": "v1/read-qr-code/",
}


# DEFAULT VALUES
DEFAULT_IMAGE_FORMAT = "png"
DEFAULT_QR_SIZE = "200x200"
DEFAULT_ERROR_CORRECTION = "Low"
DEFAULT_MARGIN = 1
DEFAULT_FOREGROUND_COLOR = "0-0-0"
DEFAULT_BACKGROUND_COLOR = "255-255-255"

ERROR_CORRECTION_MAPPING = {
    "Low": "L",
    "Medium": "M",
    "Quartile": "Q",
    "High": "H",
}
