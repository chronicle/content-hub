# Copyright 2025 Google LLC
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

import copy
import json
import pathlib

CASE_METADATA_KEY = "case_metadata"
ALERTS_ALERT_SCOPE_KEY = "alerts_full_details_alert_scope"
ALERTS_CASE_SCOPE_KEY = "alerts_full_details_case_scope"
ALERTS_EMPTY_EVENTS_KEY = "alerts_full_details_empty_events"
ALERTS_EXCEPTION_KEY = "alerts_full_details_exception_handling"

EXPECTED_TITLE = "Simulated Enrichment Case"
TARGET_IP = "192.168.1.1"
OTHER_IP = "192.168.1.2"

INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
MOCK_DATA_PATH = INTEGRATION_PATH / "tests" / "mock_data.json"
with open(MOCK_DATA_PATH, "r") as f:
    MOCK_DATA = json.load(f)

ALERT_1_CONTEXT = MOCK_DATA["alert_1_context"]

ACTION_ALERT_SCOPE_PARAMS = MOCK_DATA["action_alert_scope_parameters"]
ACTION_ALERT_SCOPE_CONTEXT = copy.deepcopy(ALERT_1_CONTEXT)

ACTION_CASE_SCOPE_PARAMS = MOCK_DATA["action_case_scope_parameters"]
ACTION_CASE_SCOPE_CONTEXT = copy.deepcopy(ALERT_1_CONTEXT)

SUCCESS_OUTPUT_MESSAGE_1 = "1 entities were successfully enriched\n"
SUCCESS_OUTPUT_MESSAGE_2 = (
    "2 entities were successfully enriched for all case open alerts\n"
)
SUCCESS_OUTPUT_MESSAGE_0 = "0 entities were successfully enriched\n"
SUCCESS_OUTPUT_MESSAGE_ENRICH_SD_ALERT = "Enrichment added.\n"
SUCCESS_OUTPUT_MESSAGE_ENRICH_SD_CASE = (
    "Enrichment added for all case open alerts.\n"
)
