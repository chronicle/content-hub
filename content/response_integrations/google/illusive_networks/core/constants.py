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

INTEGRATION_NAME = "IllusiveNetworks"
PRODUCT_NAME = "Illusive Networks"
PING_ACTION = f"{INTEGRATION_NAME} - Ping"
RUN_FORENSIC_SCAN_ACTION = f"{INTEGRATION_NAME} - Run Forensic Scan"
ENRICH_ENTITIES_ACTION = f"{INTEGRATION_NAME} - Enrich Entities"
CONNECTOR_NAME = f"{INTEGRATION_NAME} Detection Connector"
LIST_DECEPTIVE_ITEMS_ACTION = f"{INTEGRATION_NAME} - List Deceptive Items"
REMOVE_DECEPTIVE_SERVER_SCRIPT_NAME = f"{INTEGRATION_NAME} - Remove Deceptive Server"
ADD_DECEPTIVE_SERVER_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Deceptive Server"
ADD_DECEPTIVE_USER_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Deceptive User"
REMOVE_DECEPTIVE_USER_SCRIPT_NAME = f"{INTEGRATION_NAME} - Remove Deceptive User"

PING_QUERY = "{}/api/v1/incidents?limit=1"
ENRICH_ENTITIES_QUERY = "{}/api/v2/monitoring/hosts?host_names={}"
FORENSIC_SCAN_QUERY = "{}/api/v1/event/create-external-event?hostNameOrIp={}"
GET_INCIDENT_ID_QUERY = "{}/api/v1/incidents/id?event_id={}"
GET_FORENSIC_DATA_QUERY = "{}/api/v1GET_INCIDENT_ID_QUERY/forensics?event_id={}&type={}"
GET_DECEPTIVE_USERS_QUERY = "{}/api/v1/deceptive-entities/users?deceptive_user_type={}"
GET_DECEPTIVE_SERVERS_QUERY = (
    "{}/api/v1/deceptive-entities/servers?deceptive_server_type={}"
)

CA_CERTIFICATE_FILE_PATH = "cacert.pem"
DEFAULT_ITEMS = 50
TIMEOUT_THRESHOLD = 0.9

FORENSIC_DATA_TYPES = {
    "include_sys_info": "HOST_INFO",
    "include_prefetch_files_info": "PREFETCH_INFO",
    "include_add_remove": "INSTALLED_PROGRAMS_INFO",
    "include_startup_info": "STARTUP_PROCESSES",
    "include_running_info": "RUNNING_PROCESSES",
    "include_user_assist_info": "USER_ASSIST_INFO",
    "include_powershell_info": "POWER_SHELL_HISTORY",
}

ILLUSIVE_NETWORKS_PREFIX = "ILLNET"

ALL = "All"
SUGGESTED = "Only Suggested"
APPROVED = "Only Approved"
ONLY_USERS = "Only Users"
ONLY_SERVERS = "Only Servers"

DECEPTIVE_STATE_MAPPING = {ALL: "ALL", SUGGESTED: "SUGGESTED", APPROVED: "APPROVED"}

DECEPTIVE_USERS_TABLE_NAME = "Deceptive Users"
DECEPTIVE_SERVERS_TABLE_NAME = "Deceptive Servers"


DEFAULT_DEVICE_PRODUCT = "Illusive Networks"
DEFAULT_DEVICE_VENDOR = "Illusive Networks"

RATE_LIMIT_ERROR_IDENTIFIER = "Rate limit error"
