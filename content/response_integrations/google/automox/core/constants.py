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
