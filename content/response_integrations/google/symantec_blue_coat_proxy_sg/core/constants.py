from __future__ import annotations
INTEGRATION_NAME = "Symantec Blue Coat ProxySG"
INTEGRATION_DISPLAY_NAME = "Symantec Blue Coat ProxySG"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
ENRICH_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Enrich Entities"
BLOCK_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Block Entities"

COMMANDS = {
    "help": "command help",
    "test_dns": "test dns {identifier}",
    "test_geolocation": "test geolocation {identifier}",
    "test_threat_risk": "test threat-risk {identifier}",
    "test_content_filter": "test content-filter {identifier}",
    "enable": "enable",
    "conf": "conf t",
    "attack_detection": "attack-detection",
    "client": "client",
    "block": "block {identifier}",
}

DEFAULT_PORT = 22
LINE_DELIMITERS = "\r\n"
KEY_VALUE_DELIMITER = ":"
CUSTOM_LIST_DELIMITER = ",,"
PARENT_KEY_PATTERN = "\r\n{}: \r\n  "
SKIP_ROWS_NUMBER = 2
ENRICHMENT_PREFIX = "BCProxySG"
UNAVAILABLE_COUNTRY = "Unavailable"
SHELL_COMMAND_TIMEOUT = 5
SUCCESS_TEXT = "\r\n  ok\r\n"
STATUS_SUCCESS = "success"
STATUS_FAILURE = "failure"
