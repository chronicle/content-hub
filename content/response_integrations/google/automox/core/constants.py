from __future__ import annotations
from soar_sdk.SiemplifyDataModel import EntityTypes

INTEGRATION_NAME = "Automox"
PING_SCRIPT_NAME = "Ping"
LIST_POLICIES_SCRIPT_NAME = "List Policies"
EXECUTE_POLICY_SCRIPT_NAME = "Execute Policy"
EXECUTE_DEVICE_COMMAND_SCRIPT_NAME = "Execute Device Command"
ENRICH_ENTITIES_SCRIPT_NAME = "Enrich Entities"
PAGE_LIMIT = 500
DEFAULT_MAX_RECORDS_TO_RETURN = 50
POSSIBLE_POLICY_FILTER_KEYS = {
    "ID": "id",
    "Name": "name",
    "Policy Type Name": "policy_type_name",
    "Status": "status",
}
ENRICHMENT_PREFIX = "Automox"
SUPPORTED_ENTITIES = [EntityTypes.HOSTNAME, EntityTypes.ADDRESS]
ENTITY_MAPPER = {
    EntityTypes.HOSTNAME: "display_name",
    EntityTypes.ADDRESS: "ip_addrs_private",
}
COMMANDS_MAPPER = {
    "Scan Device": "GetOS",
    "Install Specific Patches": "InstallUpdate",
    "Install All Available Patches": "InstallAllUpdates",
    "Restart Device": "Reboot",
}
