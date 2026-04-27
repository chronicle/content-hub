from __future__ import annotations
INTEGRATION_NAME = "CheckPointThreatReputation"
INTEGRATION_DISPLAY_NAME = "CheckPoint Threat Reputation"

# Actions name
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
GET_HOST_REPUTATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get HOST reputation"
GET_IP_REPUTATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get IP reputation"
GET_FILE_HASH_REPUTATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - GET File Hash reputation"

ENTITY_ENRICHMENT_PREFIX = "CPThreatRep"
ENTITY_TABLE_NAME = "CheckPoint Threat Reputation"

WHITE_LIST_CLASSIFICATION = ("Benign", "Unclassified")
