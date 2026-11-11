from __future__ import annotations

import re
from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

INTEGRATION_NAME = "GSuite"
ENRICHMENT_PREFIX = INTEGRATION_NAME
PREFIX = "GWorkspace"

# Action Script Names
PING_SCRIPT_NAME = "Ping"
GET_AUTHORIZATION_SCRIPT_NAME = "Get Authorization"
GENERATE_TOKEN_SCRIPT_NAME = "Generate Token"
DELETE_USER_SCRIPT_NAME = "Delete User"
DELETE_OU_SCRIPT_NAME = "Delete OU"
CREATE_OU_SCRIPT_NAME = "Create OU"
CREATE_USER_SCRIPT_NAME = "Create User"
CREATE_GROUP_SCRIPT_NAME = "Create Group"
UPDATE_OU_SCRIPT_NAME = "Update OU"
UPDATE_USER_SCRIPT_NAME = "Update User"
ADD_MEMBERS_TO_GROUP_SCRIPT_NAME = "Add Members To Group"
REMOVE_MEMBERS_FROM_GROUP_SCRIPT_NAME = "Remove Members From Group"
LIST_OU_SCRIPT_NAME = "List Organization Units"
DELETE_GROUP_SCRIPT_NAME = "Delete Group"
LIST_USERS_SCRIPT_NAME = "List Users for an Account"
LIST_GROUP_MEMBERS_SCRIPT_NAME = "List Group Members"
ENRICH_ENTITIES_SCRIPT_NAME = "Enrich Entities"
LIST_USER_PRIVILEGES_SCRIPT_NAME = "List User Privileges"
GET_GROUP_DETAILS_SCRIPT_NAME = "Get Group Details"
LIST_GROUP_PRIVILEGES_SCRIPT_NAME = "List Group Privileges"
REVOKE_USER_SESSIONS_SCRIPT_NAME = "Revoke User Sessions"
SEARCH_USER_ACTIVITY_EVENTS_SCRIPT_NAME: str = "Search User Activity Events"
GET_HOST_BROWSER_DETAILS_SCRIPT_NAME: str = "Get Host Browser Details"
GET_EXTENSION_DETAILS_SCRIPT_NAME: str = "Get Extension Details"
BLOCK_EXTENSION_SCRIPT_NAME: str = "Block Extension"
DELETE_EXTENSION_SCRIPT_NAME: str = "Delete Extension"
REMOVE_EXTENSION_SCRIPT_NAME: str = "Remove Extension"

# Extension Management
EXTENSION_ID_REGEX: re.Pattern[str] = re.compile(r"^[a-p]{32}$")
BLOCKED_INSTALL_TYPE: str = "BLOCKED"
REMOVE_INSTALL_TYPE: str = "REMOVE"

SHA256_HASH_FUNCTION = "crypt"

SEARCH_USER_ACTIVITY_EVENTS_TIMEOUT_THRESHOLD_MS: int = 15000
APPLICATION_NAMES: set[str] = {
    "access_transparency", "admin", "calendar", "chat", "chrome",
    "context_aware_access", "data_studio", "drive", "gcp", "gplus", "groups",
    "groups_enterprise", "jamboard", "keep", "login", "meet", "mobile",
    "rules", "saml", "token", "user_accounts", "vault"
}
ALL_APPLICATIONS_KEY: str = "ALL"

MAX_RESULTS_ALLOWED: int = 1000
MAX_USERS_ALLOWED: int = 100
MINIMUM_POSITIVE_INTEGER: int = 1

# Time Frame options
LAST_HOUR: str = "Last Hour"
LAST_6_HOURS: str = "Last 6 Hours"
LAST_24_HOURS: str = "Last 24 Hours"
LAST_WEEK: str = "Last Week"
LAST_MONTH: str = "Last Month"
CUSTOM: str = "Custom"

# Time Frame mapping for Search User Activity Events
TIMEDELTA_MAP: dict[str, timedelta] = {
    LAST_HOUR: timedelta(hours=1),
    LAST_6_HOURS: timedelta(hours=6),
    LAST_24_HOURS: timedelta(days=1),
    LAST_WEEK: timedelta(weeks=1),
    LAST_MONTH: timedelta(days=30),
}

# Default and max values for parameters
DEFAULT_MAX_EVENTS_SEARCH: int = 200
MAX_EVENTS_LIMIT_SEARCH: int = 1000

# API status codes
API_CONFLICT_STATUS_CODE = 409
API_NOT_FOUND_STATUS_CODE = 404
API_BAD_REQUEST_STATUS_CODE = 400
API_NOT_AUTHORIZED_STATUS_CODE = 403

DEFAULT_MAX_USERS_TO_RETURN = 20

# Query operator mapping
SPACE = " "
TRUE = "true"
FALSE = "false"
AND = "AND"
OR = "OR"
EQUAL = "="
CONTAINS = ":"

CUSTOMER = "my_customer"

API_ROOT = "https://www.googleapis.com"
CHROME_API_ROOT: str = "https://chromemanagement.googleapis.com/v1/"
CHROME_POLICY_API_ROOT: str = "https://chromepolicy.googleapis.com/v1/"

ENDPOINTS = {
    "ping": "/oauth2/v4/token",
    "refresh-token": "/oauth2/v4/token",
    "obtain-access-token": "/oauth2/v4/token",
    "create-group": "/admin/directory/v1/groups",
    "create-user": "/admin/directory/v1/users",
    "update-user": "/admin/directory/v1/users/{primary_email}",
    "get-user": "/admin/directory/v1/users/{primary_email}",
    "create-ou": "/admin/directory/v1/customer/{customer_id}/orgunits",
    "update-ou": "/admin/directory/v1/customer/{customer_id}/orgunits/{path}",
    "delete-ou": "/admin/directory/v1/customer/{customer_id}/orgunits/{org_path}",
    "delete-user": "/admin/directory/v1/users/{primary_email}",
    "sign-out-user": "admin/directory/v1/users/{primary_email}/signOut",
    "delete-group": "/admin/directory/v1/groups/{group_email}",
    "add-member-to-group": "/admin/directory/v1/groups/{group_email}/members",
    "remove-member-from-group": (
        "/admin/directory/v1/groups/{group_email}/members/{email_address}"
    ),
    "list-ou": "/admin/directory/v1/customer/{customer_id}/orgunits",
    "list-group-members": "/admin/directory/v1/groups/{group_email}/members",
    "list-users": "/admin/directory/v1/users",
    "list-role-assignments": (
        "/admin/directory/v1/customer/{customer_id}/roleassignments"
    ),
    "get-role": "/admin/directory/v1/customer/{customer_id}/roles/{role_id}",
    "list-group-permissions": "/groups/v1/groups/{group_id}?alt=json",
    "get-group": "/admin/directory/v1/groups/{group_id}",
    "list_host_browsers": (
        "/admin/directory/v1.1beta1/customer/{customer_id}/devices/chromebrowsers"
    ),
    "list-user-activity": (
        "/admin/reports/v1/activity/users/{user_key}/applications/{application_name}"
    ),
    "get-extension-details": "customers/{customer_id}/apps/chrome/{extension_id}",
    "get-extension-users": "customers/{customer_id}/apps:fetchUsersRequestingExtension",
    "get-extension-devices": (
        "customers/{customer_id}/apps:fetchDevicesRequestingExtension"
    ),
    "batch-modify-policy": "customers/{customer_id}/policies/orgunits:batchModify",
    "resolve-policy": "customers/{customer_id}/policies:resolve",
    "batch-inherit-policy": "customers/{customer_id}/policies/orgunits:batchInherit",
}

OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/admin.directory.user",
    "https://www.googleapis.com/auth/admin.directory.group.member",
    "https://www.googleapis.com/auth/admin.directory.customer.readonly",
    "https://www.googleapis.com/auth/admin.directory.domain.readonly",
    "https://www.googleapis.com/auth/admin.directory.group",
    "https://www.googleapis.com/auth/admin.directory.orgunit",
    "https://www.googleapis.com/auth/admin.directory.user.alias",
    "https://www.googleapis.com/auth/admin.directory.user.security",
    "https://www.googleapis.com/auth/admin.directory.rolemanagement.readonly",
    "https://www.googleapis.com/auth/apps.groups.settings",
    "https://www.googleapis.com/auth/admin.reports.audit.readonly",
    "https://www.googleapis.com/auth/admin.directory.device.chromebrowsers.readonly",
    "https://www.googleapis.com/auth/chrome.management.appdetails.readonly",
    "https://www.googleapis.com/auth/chrome.management.policy",
]
USER_STATUS_TO_SUSPENDED = {"Not Changed": None, "Blocked": True, "Unblocked": False}

APPLICATION_NAME_MAPPING: Mapping[str, str] = {
    "ALL": "ALL",
    "Access Transparency": "access_transparency",
    "Admin": "admin",
    "Chrome Browser & OS": "chrome",
    "Context-aware Access": "context_aware_access",
    "Data Studio": "data_studio",
    "Enterprise Groups": "groups_enterprise",
    "Google Calendar": "calendar",
    "Google Chat": "chat",
    "Google Cloud": "gcp",
    "Google Drive": "drive",
    "Google Groups": "groups",
    "Google Jamboard": "jamboard",
    "Google Keep": "keep",
    "Google Meet": "meet",
    "Google Vault": "vault",
    "Google+": "gplus",
    "Login": "login",
    "Mobile Devices": "mobile",
    "Rules": "rules",
    "SAML": "saml",
    "Token": "token",
    "User Accounts": "user_accounts",
}
PARENT_ORG_UNIT_NOT_FOUND_ERR: str = "parent org unit not found"
MIN_LIMIT: int = 1
MAX_LIMIT: int = 100
DEFAULT_MAX_LIMIT: int = 50
