INTEGRATION_NAME = "Jamf"
INTEGRATION_DISPLAY_NAME = "Jamf"

# Jamf Pro API ENDPOINTS
API_ENDPOINTS = {
    # Authentication
    "auth": "/api/v1/oauth/token",
    "invalidate_token": "/api/v1/auth/invalidate-token",
    # System information
    "jamf_pro_version": "/api/v1/jamf-pro-version",
    # Computer management
    "computer_groups": "/api/v1/computer-groups",
    "update_computer_group": "/JSSResource/computergroups/id/{id}",
    "computer_inventory_detail": "/api/v1/computers-inventory-detail/{id}",
    "device_group_membership": "/JSSResource/computergroups/id/{id}",
    "computers_inventory": "/api/v1/computers-inventory",
    "mdm_commands": "/api/v2/mdm/commands",
    "computer_extension_attributes": "/JSSResource/computerextensionattributes",
    # Mobile device management
    "mobile_device_inventory": "/api/v2/mobile-devices/detail",
    "mobile_device_inventory_detail": "/api/v2/mobile-devices/{id}",
}

# Jamf Protect API ENDPOINTS
PROTECT_API_ENDPOINTS = {"auth": "token", "graphQL": "graphql"}

# Mapping from UI value to Jamf Protect GraphQL enum for prevent lists
PROTECT_PREVENT_TYPE_MAP = {
    "File Hash": "FILEHASH",
    "Signing Information - Team ID": "TEAMID",
    "Signing Information - Code Directory Hash": "CDHASH",
    "Signing Information - Signing ID": "SIGNINGID",
}

# ACTION NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
LIST_COMPUTER_GROUPS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Computer Groups"
GET_DEVICE_INFORMATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Device Information"
GET_DEVICE_GROUP_MEMBERSHIP_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Device Group Membership"
GET_COMPUTER_INVENTORY_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Computer Inventory"
GET_MOBILE_DEVICE_INVENTORY_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Mobile Device Inventory"
WIPE_MANAGED_DEVICE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Wipe Managed Device"
REMOTE_LOCK_MANAGED_DEVICE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Remote Lock Managed Device"
ASSIGN_TO_GROUP_SCRIPT_NAME = f"{INTEGRATION_NAME} - Assign to Group"
UPDATE_EXTENSION_ATTRIBUTE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Extension Attribute"
REMOTE_LOCK_MOBILE_DEVICE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Remote Lock Mobile Device"
WIPE_MOBILE_DEVICE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Wipe Mobile Device"
UPDATE_PROTECT_PREVENT_LIST_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Protect Prevent List"

# CASE WALL TABLE NAMES
ENRICH_TABLE_NAME = "Jamf Report for: {}"

# HTTP HEADERS
VERSION = "2.0.0"
USER_AGENT = f"Jamf%20SOAR%20Integration/{VERSION} SecOps/Chronicle"

# ENRICHMENT PREFIX
ENRICH_PREFIX = "Jamf"

# MOBILE DEVICE SECTIONS
MOBILE_DEVICE_ALL_SECTIONS = [
    "GENERAL",
    "HARDWARE",
    "USER_AND_LOCATION",
    "PURCHASING",
    "SECURITY",
    "APPLICATIONS",
    "EBOOKS",
    "NETWORK",
    "SERVICE_SUBSCRIPTIONS",
    "CERTIFICATES",
    "PROFILES",
    "USER_PROFILES",
    "PROVISIONING_PROFILES",
    "SHARED_USERS",
    "GROUPS",
    "EXTENSION_ATTRIBUTES",
]

# COMPUTER SECTIONS
COMPUTER_ALL_SECTIONS = [
    "GENERAL",
    "DISK_ENCRYPTION",
    "PURCHASING",
    "APPLICATIONS",
    "STORAGE",
    "USER_AND_LOCATION",
    "CONFIGURATION_PROFILES",
    "PRINTERS",
    "SERVICES",
    "HARDWARE",
    "LOCAL_USER_ACCOUNTS",
    "CERTIFICATES",
    "ATTACHMENTS",
    "PLUGINS",
    "PACKAGE_RECEIPTS",
    "FONTS",
    "SECURITY",
    "OPERATING_SYSTEM",
    "LICENSED_SOFTWARE",
    "IBEACONS",
    "SOFTWARE_UPDATES",
    "EXTENSION_ATTRIBUTES",
    "CONTENT_CACHING",
    "GROUP_MEMBERSHIPS",
]
