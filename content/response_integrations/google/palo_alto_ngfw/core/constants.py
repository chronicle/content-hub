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
INTEGRATION_NAME = "PaloAltoNGFW"

PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
ADD_IPS_TO_GROUP_SCRIPT_NAME = f"{INTEGRATION_NAME} - AddIpsToGroup"
BLOCK_IPS_IN_POLICY_SCRIPT_NAME = f"{INTEGRATION_NAME} - BlockIpsInPolicy"
BLOCK_URLS_SCRIPT_NAME = f"{INTEGRATION_NAME} - BlockURLs"
COMMIT_CHANGES_SCRIPT_NAME = f"{INTEGRATION_NAME} - CommitChanges"
EDIT_BLOCKED_APPLICATIONS_SCRIPT_NAME = f"{INTEGRATION_NAME} - EditBlockedApplications"
GET_BLOCKED_APPLICATIONS_SCRIPT_NAME = f"{INTEGRATION_NAME} - GetBlockedApplications"
REMOVE_IP_FROM_GROUP_SCRIPT_NAME = f"{INTEGRATION_NAME} - RemoveIpFromGroup"
UNBLOCK_IPS_IN_POLICY_SCRIPT_NAME = f"{INTEGRATION_NAME} - UnblockIpsInPolicy"
UNBLOCK_URLS_SCRIPT_NAME = f"{INTEGRATION_NAME} - UnblockURLs"

ITEMS_PER_REQUEST = 50
