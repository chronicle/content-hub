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
PROVIDER_NAME = "SolarWinds Orion"

# ACTIONS
PING_SCRIPT_NAME = f"{PROVIDER_NAME} - Ping"
EXECUTE_QUERY_SCRIPT_NAME = f"{PROVIDER_NAME} - Execute Query"
EXECUTE_ENTITY_QUERY_SCRIPT_NAME = f"{PROVIDER_NAME} - Execute Entity Query"
ENRICH_ENDPOINT_SCRIPT_NAME = f"{PROVIDER_NAME} - EnrichEndpoint"

ENDPOINTS = {"test_connectivity": "/SolarWinds/InformationService/v3/Json/Query"}

HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

DEFAULT_RESULTS_LIMIT = 100
BAD_REQUEST_STATUS_CODE = 400
DEFAULT_IP_KEY = "IpAddress"
DEFAULT_HOSTNAME_KEY = "Hostname"
DEFAULT_DISPLAY_NAME_KEY = "DisplayName"
ENRICHMENT_PREFIX = "SLRW_ORION"
ENRICHMENT_QUERY = (
    "SELECT IpAddress, DisplayName, NodeDescription, ObjectSubType,Description,SysName, Caption,DNS,"
    "Contact,Status,StatusDescription,IOSImage,IOSVersion,GroupStatus,LastBoot,SystemUpTime,"
    "AvgResponseTime,CPULoad,PercentMemoryUsed,MemoryAvailable,Severity,Category,EntityType, IsServer, "
    "IsOrionServer FROM Orion.Nodes "
)
