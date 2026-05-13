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

INTEGRATION_NAME = "CiscoThreatGrid"

# Action script names
GET_SUBMISSIONS_SCRIPT_NAME = f"{INTEGRATION_NAME} - GetSubmissions"

WAITING_STATE = "wait"
TO_PROCESS = "to_process"
NO_RESULTS = "no_results"
FAILED = "failed"

ENTITY_TERM_MAPPER = {
    EntityTypes.HOSTNAME: "domain",
    EntityTypes.PROCESS: "process",
    EntityTypes.URL: "url",
    EntityTypes.FILENAME: "path",
}
DEFAULT_THREAT_SCORE_THRESHOLD = 50
DEFAULT_MAX_RESULTS = 10
MAX_LIMIT_VALUE = 100
MIN_LIMIT_VALUE = 1
