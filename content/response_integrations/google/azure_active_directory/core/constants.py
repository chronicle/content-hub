# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
INTEGRATION_NAME = "AzureActiveDirectory"
INTEGRATION_DISPLAY_NAME = "Azure Active Directory"

# ACTIONS NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
DISABLE_ACCOUNT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Disable Account"
ENABLE_ACCOUNT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enable Account"
ADD_USER_TO_A_GROUP_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add User To Group"
IS_USER_IN_GROUP_SCRIPT_NAME = f"{INTEGRATION_NAME} - Is User In a Group"
FORCE_PASSWORD_UPDATE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Force Password Update"
RESET_USER_PASSWORD_SCRIPT_NAME = f"{INTEGRATION_NAME} - Reset User Password"
LIST_USERS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Users"
GET_MANAGER_CONTACT_DETAILS_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Get Manager Contact Details"
)
LIST_GROUPS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Groups"
ENRICH_HOST_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich Host"
ENRICH_USER_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich User"
REMOVE_USER_FROM_GROUP_SCRIPT_NAME = f"{INTEGRATION_NAME} - Remove User from a Group"
LIST_MEMBERS_IN_GROUP_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Members in the Group"
LIST_USERS_GROUPS_MEMBERSHIPS_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - List User's Groups Membership"
)
REVOKE_USER_SESSION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Revoke User Session"

# CASE WALL TABLE NAMES
LIST_USERS_TABLE_NAMES = "List Of Users"
USER_MANAGER_TABLE_NAME = "Manager Contact: {}"
LIST_GROUPS_TABLE_NAMES = "List Of Groups"
ENRICH_TABLE_NAME = "Report for: {}"

ENRICH_PREFIX = "AAD"

USERS_LIST_PRIORITY_FILDS = ["All Fields", "userPrincipalName"]

ALL_FIELDS_IDENTIFIER = "All Fields"
SELECT_ONE_FILTER_KEY = "Select One"
FILTER_LOGIC_EQUALS = "Equal"
FILTER_LOGIC_CONTAINS = "Contains"

GROUP_MEMBERS_FILTER_USER_DISPLAY_NAME = "User Display Name"
GROUP_MEMBERS_FILTER_USER_MAIL_NAME = "User Mail Name"
GROUP_MEMBERS_FILTER_USER_PRINCIPAL_NAME = "User Principal Name"

GROUP_FILTER_KEYS_MAPPING = {
    "Group Display Name": "name",
    "Group Description": "description",
}

NAME_FILTER_KEYS = ["displayName"]
EMAIL_FILTER_KEYS = ["mail", "userPrincipalName"]

DEFAULT_API_ROOT = "https://graph.microsoft.com"
DEFAULT_LOGIN_API_ROOT = "https://login.microsoftonline.com"

# HTTP STATUS CODES
NOT_FOUND_ERROR_CODE = 404
FORBIDDEN_ERROR_CODE = 403
NO_CONTENT_STATUS_CODE = 204

PERMISSION_ERROR_INDICATORS: list[str] = [
    "403", "Forbidden", "Insufficient privileges", "Authorization_RequestDenied"
]
