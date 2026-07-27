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
INTEGRATION_NAME = "Cloudflare"
INTEGRATION_DISPLAY_NAME = "Cloudflare"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
ADD_URL_TO_RULE_LIST_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Add URL to Rule List"
CREATE_RULE_LIST_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Create Rule List"
LIST_FIREWALL_RULES_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Firewall Rules"
ADD_IP_TO_RULE_LIST_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Add IP To Rule List"
CREATE_FIREWALL_RULE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create Firewall Rule"
UPDATE_FIREWALL_RULE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Firewall Rule"

SUITABLE_RULE_LIST_KIND = "ip"


ENDPOINTS = {
    "rule_list": "/client/v4/accounts/{account_id}/rules/lists",
    "rule_list_items": "/client/v4/accounts/{account_id}/rules/lists/{rule_id}/items",
    "ping": "/client/v4/accounts?name={account_name}",
    "get_account": "/client/v4/accounts",
    "get_zone": "/client/v4/zones",
    "get_firewall_rules": "/client/v4/zones/{zone_id}/firewall/rules",
    "create_firewall_rule": "/client/v4/zones/{zone_id}/firewall/rules",
    "manage_firewall_rule": "/client/v4/zones/{zone_id}/firewall/rules/{rule_id}",
    "update_firewall_filter": "/client/v4/zones/{zone_id}/filters/{filter_id}",
}
ADD_URL_TO_RULE_LIST_SUITABLE_RULE_LIST_KIND = "redirect"
RULE_LIST_TYPE_MAPPING = {"IP Address": "ip", "Redirect": "redirect"}
FILTER_KEY_MAPPING = {
    "Select One": "",
    "ID": "id",
    "Action": "action",
    "Name": "description",
}

FILTER_STRATEGY_MAPPING = {"Select One": "", "Equal": "Equal", "Contains": "Contains"}

DEFAULT_LIMIT = 50
EQUAL = "Equal"
CONTAINS = "Contains"

RULE_ACTION_MAPPING = {
    "Allow": "allow",
    "Block": "block",
    "Bypass": "bypass",
    "Legacy CAPTCHA": "challenge",
    "Managed Challenge": "managed_challenge",
    "JS Challenge": "js_challenge",
    "Log": "log",
}
RULE_PRODUCTS_POSSIBLE_VALUES = [
    "zoneLockdown",
    "uaBlock",
    "bic",
    "hot",
    "securityLevel",
    "rateLimit",
    "waf",
]
CHARACTERS_MAX_LIMIT = 50
