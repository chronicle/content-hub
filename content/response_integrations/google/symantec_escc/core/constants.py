from __future__ import annotations
INTEGRATION_NAME = "Symantec Endpoint Security Complete Cloud"
INTEGRATION_IDENTIFIER = "SymantecESCC"
PING_ACTION = f"{INTEGRATION_NAME} - Ping"
ENRICH_ENTITIES_ACTION = f"{INTEGRATION_NAME} - Enrich Entities"
LIST_DEVICE_GROUPS_ACTION = f"{INTEGRATION_NAME} - List Device Groups"
GET_RELATED_IOCS_ACTION = f"{INTEGRATION_NAME} - Get Related IOCs"

ENDPOINTS = {
    "access_token": "/v1/oauth2/tokens",
    "test_connectivity": "/v1/incidents",
    "get_device_groups": "/v1/device-groups",
    "get_devices_in_group": "/v1/device-groups/{group_id}/devices",
    "get_device_by_id": "/v1/devices/{device_id}",
    "get_entity_details": "/v1/threat-intel/insight/{ioc_type}/{identifier}",
    "get_hash_processes": "/v1/threat-intel/processchain/file/{filehash}",
    "get_antivirus_info": "/v1/threat-intel/protection/{ioc_type}/{identifier}",
    "get_related_iocs": "/v1/threat-intel/related/{ioc_type}/{identifier}",
}

BAD_REPUTATION = "BAD"
GOOD_REPUTATION = "GOOD"
BLOCKED_STATE = "blocked"
UNKNOWN_STATE = "unknown"
ENDPOINT_LINK_FORMAT = "https://sep.securitycloud.symantec.com/v1/#/asset/{id}/details"
BLOCKED_DESC = "This entity was blocked in AntiVirus, IPS or BASH"
UNKNOWN_DESC = "This entity was not seen in AntiVirus, IPS or BASH"
NETWORK_KEY = "network"
FILE_KEY = "file"
SECURE_STATUS = "SECURE"
AT_RISK_STATUS = "AT RISK"
EQUAL_FILTER = "Equal"
CONTAINS_FILTER = "Contains"
DEFAULT_DEVICE_GROUPS_LIMIT = 50

FILE_IOC = "File"
DOMAIN_IOC = "Domain"
IP_IOC = "IP"
