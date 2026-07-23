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
OS_INDEX = "*"
OS_QUERY = "*"
DISPLAYFIELD = "*"
SEARCHFIELD = "*"
DSL_INDEX = "_all"
OLDESTDATE = "1970-01-01T00:00:00"
EARLIESTDATE = "now"
TIMESTAMPFIELD = "@timestamp"
RESULT_LIMIT = 10
CA_CERTIFICATE_FILE_PATH = "cacert.pem"
DEFAULT_TIMEOUT = 600
DEFAULT_MAX_LIMIT = 10_000
INTEGRATION_NAME = "OpenSearch"
PING_SCRIPT_NAME = "Ping"
SIMPLE_OS_SEARCH_SCRIPT_NAME = "Simple Search"
DSL_SEARCH_SCRIPT_NAME = "DSL Search"
ADVANCED_OS_SEARCH_SCRIPT_NAME = "Advanced Search"
OPENSEARCH_QUERY_JSON = {
    "from": 0,
    "query": {  # type: ignore
        "bool": {
            "must": [
                {"query_string": {"query": "*"}},
                {"range": {"@timestamp": {"gt": "now-1d", "lt": "now"}}},
            ],
            "must_not": [],
            "should": [],
        }
    },
}

CUSTOM_CONFIGURATION_FILE_NAME = "severity_map_config.json"
SEVERITY_CUSTOM_KEY_NAME = "severity"
DEFAULT_SEVERITY_VALUE = 50
CUSTOM_MAPPING_CONFIGURATION = {}
CONFIGURATION_DATA = {}
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
ALERTS_LIMIT = 20
DEFAULT_DAYS_BACKWARDS = 3
TIMEZONE = "UTC"
NON_SOURCE_FIELDS = ["_id", "_index", "_score", "_type"]
STORED_ALERT_IDS_LIMIT = 2000
DLS_CONNECTOR_NAME = "OpenSearch DSL Connector"
OS_CONNECTOR_NAME = "OpenSearch Connector"
TIMESTAMP_FILE = "timestamp.stmp"
ALERT_LOW_SEVERITY = "LOW"
SEVERITY_MAP = {"INFO": -1, "LOW": 40, "MEDIUM": 60, "HIGH": 80, "CRITICAL": 100}
MAP_FILE = "map.json"
