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
INTEGRATION_NAME = "CSV"
DEFAULT_PRODUCT = DEFAULT_VENDOR = INTEGRATION_NAME
# ACTIONS NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
SEARCH_BY_STRING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Search by String"
SEARCH_BY_ENTITY_SCRIPT_NAME = f"{INTEGRATION_NAME} - Search by Entity"
SAVE_JSON_TO_CSV_SCRIPT_NAME = f"{INTEGRATION_NAME} - Save JSON To CSV"


# CONNECTORS NAMES
CSV_CONNECTOR_SCRIPT_NAME = "CSV connector"

# TABLE NAMES
RECORDS_TABLE_NAME = "{} Found Records"


# PREFIXES
ENRICHMENT_PREFIX = "CSVEnrichment"


# INSIGHTS
FOUND_IN_CSV_INSIGHT_NAME = "Found in CSV: {}"

DEFAULT_PATH = "/tmp"
