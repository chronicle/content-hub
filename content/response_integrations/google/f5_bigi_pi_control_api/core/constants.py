from __future__ import annotations
INTEGRATION_NAME = "F5BIGIPiControlAPI"
INTEGRATION_DISPLAY_NAME = "F5 BIG-IP"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
LIST_DATA_GROUPS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - List Data Groups"
ADD_IP_TO_DATA_GROUP_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Add IP To Data Group"
LIST_PORT_LISTS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - List Port Lists"
ADD_PORT_TO_PORT_LIST_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Add Port To Port List"
)
CREATE_PORT_LIST_NAME = f"{INTEGRATION_DISPLAY_NAME} - Create Port List"
REMOVE_PORT_FROM_PORT_LIST_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Remove Port From Port List"
)
LIST_ADDRESS_LISTS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - List Address Lists"
LIST_IRULES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - List iRules"
CREATE_DATA_GROUP_NAME = f"{INTEGRATION_DISPLAY_NAME} - Create Data Group"
DELETE_DATA_GROUP_NAME = f"{INTEGRATION_DISPLAY_NAME} - Delete Data Group"
CREATE_IRULE_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Create iRule"
DELETE_IRULE_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Delete iRule"
UPDATE_IRULE_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Update iRule"
CREATE_ADDRESS_LIST_NAME = f"{INTEGRATION_DISPLAY_NAME} - Create Address List"
DELETE_ADDRESS_LIST_NAME = f"{INTEGRATION_DISPLAY_NAME} - Delete Address List"
CREATE_PORT_LIST_NAME = f"{INTEGRATION_DISPLAY_NAME} - Create Port List"
DELETE_PORT_LIST_NAME = f"{INTEGRATION_DISPLAY_NAME} - Delete Port List"
ADD_IP_TO_ADDRESS_LIST_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Add IP To Address List"
)
REMOVE_IP_FROM_ADDRESS_LIST_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Remove IP From Address List"
)
REMOVE_IP_FROM_DATA_GROUP_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Remove IP From Data Group"
)

ENDPOINTS = {
    "ping": "/mgmt/tm/security/firewall/port-list",
    "list_data_groups": "/mgmt/tm/ltm/data-group/internal",
    "data_group": "/mgmt/tm/ltm/data-group/internal/{group_name}",
    "list_port_lists": "/mgmt/tm/security/firewall/port-list",
    "port_list": "/mgmt/tm/security/firewall/port-list/{port_list_name}",
    "list_address_lists": "/mgmt/tm/security/firewall/address-list/",
    "address_list": "/mgmt/tm/security/firewall/address-list/{list_name}",
    "list_irules": "/mgmt/tm/ltm/rule/",
    "create_data_group": "/mgmt/tm/ltm/data-group/internal",
    "delete_data_group": "/mgmt/tm/ltm/data-group/internal/{group_name}",
    "create_irule": "/mgmt/tm/ltm/rule",
    "delete_irule": "/mgmt/tm/ltm/rule/{name}",
    "update_irule": "/mgmt/tm/ltm/rule/{name}",
    "create_address_list": "/mgmt/tm/security/firewall/address-list/",
    "delete_address_list": "/mgmt/tm/security/firewall/address-list/{list_name}",
    "create_port_list": "/mgmt/tm/security/firewall/port-list",
}

GROUP_TYPES = {"IP Address": "ip", "String": "string", "Integer": "integer"}

DEFAULT_LIMIT = 50
EQUAL_FILTER = "Equal"
CONTAINS_FILTER = "Contains"
IP_GROUP_TYPE = "ip"
IPV4_MASK = "/32"
IPV6_MASK = "/128"
ALL_IPV6 = "::"
