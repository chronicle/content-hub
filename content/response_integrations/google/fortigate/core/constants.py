from __future__ import annotations
INTEGRATION_NAME = "Fortigate"
INTEGRATION_DISPLAY_NAME = "Fortigate"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
ADD_ENTITIES_TO_POLICY_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Add Entities To Policy"
)
ADD_ENTITIES_TO_ADDRESS_GROUP_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Add Entities To Address Group"
)
REMOVE_ENTITIES_FROM_POLICY_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Remove Entities From Policy"
)
REMOVE_ENTITIES_FROM_ADDRESS_GROUP_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Remove Entities From Address Group"
)
LIST_POLICIES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - List Policies"
LIST_ADDRESS_GROUPS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - List Address Groups"

ENDPOINTS = {
    "ping": "/api/v2/cmdb/firewall/addrgrp?count=1",
    "get_policy_by_name": "/api/v2/cmdb/firewall/policy/?filter=name=={policy_name}",
    "update_policy": (
        "/api/v2/cmdb/firewall/policy/{policy_id}?filter=name=={policy_name}"
    ),
    "get_policies": "api/v2/cmdb/firewall/policy/",
    "get_address": "/api/v2/cmdb/firewall/address/",
    "create_address": "/api/v2/cmdb/firewall/address/",
    "get_address_group_by_name": (
        "/api/v2/cmdb/firewall/addrgrp?filter=name=={address_group_name}"
    ),
    "update_address_group": "/api/v2/cmdb/firewall/addrgrp/{address_group_name}",
    "get_address_groups": "/api/v2/cmdb/firewall/addrgrp/",
    "get_threat_logs": "/api/v2/log/{location}/{subtype}",
}

SUBNET_DELIMITER = "/"
DEFAULT_IP_MASK = "255.255.255.255"
IP_SUBNET_CONVERSIONS = {
    "/0": "0.0.0.0",
    "/1": "128.0.0.0",
    "/2": "192.0.0.0",
    "/3": "224.0.0.0",
    "/4": "240.0.0.0",
    "/5": "248.0.0.0",
    "/6": "252.0.0.0",
    "/7": "254.0.0.0",
    "/8": "255.0.0.0",
    "/9": "255.128.0.0",
    "/10": "255.192.0.0",
    "/11": "255.224.0.0",
    "/12": "255.240.0.0",
    "/13": "255.248.0.0",
    "/14": "255.252.0.0",
    "/15": "255.254.0.0",
    "/16": "255.255.0.0",
    "/17": "255.255.128.0",
    "/18": "255.255.192.0",
    "/19": "255.255.224.0",
    "/20": "255.255.240.0",
    "/21": "255.255.248.0",
    "/22": "255.255.252.0",
    "/23": "255.255.254.0",
    "/24": "255.255.255.0",
    "/25": "255.255.255.128",
    "/26": "255.255.255.192",
    "/27": "255.255.255.224",
    "/28": "255.255.255.240",
    "/29": "255.255.255.248",
    "/30": "255.255.255.252",
    "/31": "255.255.255.254",
    "/32": "255.255.255.255",
}

UPDATE_ACTIONS = {"add": "add", "remove": "remove"}

FILTER_KEY_VALUES = {"Select One": "", "Name": "name"}

FILTER_LOGIC_OPERATORS = {"Equal": "==", "Contains": "=@"}

ENTITIES_LOCATION = {"destination": "Destination", "source": "Source"}

# Connector
CONNECTOR_NAME = f"{INTEGRATION_DISPLAY_NAME} - Threat Logs Connector"
DEFAULT_TIME_FRAME = 1
DEFAULT_LIMIT = 100
DEVICE_VENDOR = "Fortinet"
DEVICE_PRODUCT = "Fortigate"
COMPLETED_QUERY = 100
STORED_IDS_LIMIT = 1000

SEVERITY_MAP = {
    "debug": -1,
    "information": -1,
    "notice": 40,
    "warning": 60,
    "critical": 80,
    "alert": 100,
    "emergency": 100,
}

SEVERITIES = [
    "debug",
    "information",
    "notice",
    "warning",
    "critical",
    "alert",
    "emergency",
]
