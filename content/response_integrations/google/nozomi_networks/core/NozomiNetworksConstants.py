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
PROVIDER_NAME = "Nozomi Networks"

# ACTIONS
PING_SCRIPT_NAME = f"{PROVIDER_NAME} - Ping"
LIST_VULNERABILITIES_SCRIPT_NAME = f"{PROVIDER_NAME} - List Vulnerabilities"
RUN_QUERY_SCRIPT_NAME = f"{PROVIDER_NAME} - Run a Query"
RUN_CLI_COMMAND_SCRIPT_NAME = f"{PROVIDER_NAME} - Run a CLI Command"
ENRICH_ENTITIES_SCRIPT_NAME = f"{PROVIDER_NAME} - Enrich Entities"

ENDPOINTS = {
    "test_connectivity": "/api/open/query/do?query=node_cpes | head 5",
    "get_vulnerabilities": "/api/open/query/do?query=node_cves{query}",
    "run_query": "/api/open/query/do?query={query}",
    "run_cli_command": "/api/open/cli",
    "get_alerts": "/api/open/query/do?query=alerts{query}",
    "get_entity": "/api/open/query/do?query=nodes{query}",
}

HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

CA_CERTIFICATE_FILE_PATH = "cacert.pem"
DEFAULT_RECORD_LIMIT = 25
ENRICHMENT_PREFIX = "Nozomi"

# CONNECTORS
DEVICE_VENDOR = "Nozomi"
DEVICE_PRODUCT = "Nozomi Networks Guardian"
ALERTS_CONNECTOR_SCRIPT_NAME = f"{PROVIDER_NAME} - Alerts Connector"
IDS_FILE = "ids.json"
MAP_FILE = "map.json"
ALERT_ID_FIELD = "id"
LIMIT_IDS_IN_IDS_FILE = 1000
TIMEOUT_THRESHOLD = 0.9
ACCEPTABLE_TIME_INTERVAL_IN_MINUTES = 5
WHITELIST_FILTER = "whitelist"
BLACKLIST_FILTER = "blacklist"
DEFAULT_TIME_FRAME = 8
DEFAULT_FETCH_INTERVAL = 60
