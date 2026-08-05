
from __future__ import annotations

INTEGRATION_NAME = "BloodHound Enterprise"
DEVICE_PRODUCT = "BloodHound Enterprise"
DEFAULT_DEVICE_VENDOR = "BloodHound Enterprise"
PRODUCT_NAME = "BloodHound Enterprise Connector"
VENDOR_NAME = "BloodHound Enterprise"
PROVIDER_NAME = "BloodHound Enterprise"
SIEMPLIFY_PREFIX_FOR_APP = "siemplify"

ALERT_CONNECTOR_NAME = f"{INTEGRATION_NAME} - Attack Path Alert Connector"

# ACTIONS NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
DOES_PATH_EXISTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Does Path Exists"
GET_OBJECT_ID_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Object Id"
FETCH_ASSET_INFO_SCRIPT_NAME = f"{INTEGRATION_NAME} - Fetch Assets"
PROPERTY_KEY = "domain_last_created_dates"

DIRECTORY_TYPES = [
    "User",
    "Computer",
    "Group",
    "Container",
    "Domain",
    "GPO",
    "Aiaca",
    "Rootca",
    "Enterpriseca",
    "Ntauthstore",
    "Certtemplate",
    "OU"
    ]
AZURE_TYPES = ["AZApp", "AZGroup", "AZUser", "AZRole", "AZTenant", "AZServicePrincipal", "AZAutomationAccount"]
AZURE_RELATED_TYPES = {
    "AZApp": {"inbound-control": "inbound_object_control"},
    "AZGroup": {
        "group-membership": "group_membership",
        "group-members": "group_members",
        "roles": "roles",
        "inbound-control": "inbound_object_control",
        "outbound-control": "outbound_object_control",
    },
    "AZRole": {"active-assignments": "active_assignments"},
    "AZServicePrincipal": {
        "roles": "roles",
        "inbound-control": "inbound_object_control",
        "outbound-control": "outbound_object_control",
        "inbound-abusable-app-role-assignments": "inbound_abusable_app_role_assignments",
        "outbound-abusable-app-role-assignments": "outbound_abusable_app_role_assignments",
    },
    "AZUser": {
        "group-membership": "group_membership",
        "roles": "roles",
        "outbound-execution-privileges": "execution_privileges",
        "outbound-control": "outbound_object_control",
        "inbound-control": "inbound_object_control",
    },
}
AZ_TENANT_RELATED_TYPES = [
    "descendent-users",
    "descendent-groups",
    "descendent-management-groups",
    "descendent-subscriptions",
    "descendent-resource-groups",
    "descendent-virtual-machines",
    "descendent-managed-clusters",
    "descendent-vm-scale-sets",
    "descendent-container-registries",
    "descendent-web-apps",
    "descendent-automation-accounts",
    "descendent-key-vaults",
    "descendent-function-apps",
    "descendent-logic-apps",
    "descendent-applications",
    "descendent-service-principals",
    "descendent-devices",
    "inbound-control"
]

# Errors code:
BAD_REQUEST = 400
UNAUTHORIZE_REQUEST = 401
FORBIDDEN_REQUEST = 403
NOT_FOUND = 404
TOO_MANY_REQUEST = 429
SERVER_ERROR = 500

