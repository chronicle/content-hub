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

from .conftest import MockEntity

# Mock data JSON payload lookup keys
CASE_METADATA_KEY = "case_metadata"
ALERTS_ALERT_SCOPE_KEY = "alerts_full_details_alert_scope"
ALERTS_CASE_SCOPE_KEY = "alerts_full_details_case_scope"
WORKFLOW_CARDS_KEY = "workflow_cards"

# Target values and entities
ORIGINAL_TITLE = "Original Title"
ALERT_SCOPE_NAME = "AlertScopeName"
CASE_SCOPE_NAME = "CaseScopeName"
TARGET_IP = "192.168.1.1"
OTHER_IP = "192.168.1.2"

INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent

MOCK_DATA_PATH = INTEGRATION_PATH / "tests" / "mock_data.json"
with open(MOCK_DATA_PATH, "r") as f:
    MOCK_DATA = json.load(f)

ALERT_1_CONTEXT = MOCK_DATA["alert_1_context"]
ALERT_2_CONTEXT = MOCK_DATA["alert_2_context"]

ADD_ALERT_SCOPE_PARAMS = MOCK_DATA["add_additional_data_alert_scope_parameters"]
ADD_ALERT_SCOPE_CONTEXT = copy.deepcopy(ALERT_1_CONTEXT)
ADD_CASE_SCOPE_PARAMS = MOCK_DATA["add_additional_data_case_scope_parameters"]
ADD_CASE_SCOPE_CONTEXT = copy.deepcopy(ALERT_1_CONTEXT)

ATTACH_PLAYBOOK_PARAMS = MOCK_DATA["attach_playbook_parameters"]
ATTACH_PLAYBOOK_ALERT_SCOPE_CONTEXT = copy.deepcopy(ALERT_1_CONTEXT)
ATTACH_PLAYBOOK_CASE_SCOPE_CONTEXT = copy.deepcopy(ALERT_1_CONTEXT)

CHANGE_CASE_ALERT_FIRST_ALERT_PARAMS = MOCK_DATA[
    "change_case_name_alert_scope_parameters"
]
CHANGE_CASE_ALERT_FIRST_ALERT_CONTEXT = copy.deepcopy(ALERT_1_CONTEXT)
CHANGE_CASE_ALERT_NOT_FIRST_ALERT_CONTEXT = copy.deepcopy(ALERT_2_CONTEXT)
CHANGE_CASE_CASE_SCOPE_PARAMS = MOCK_DATA["change_case_name_case_scope_parameters"]
CHANGE_CASE_CASE_SCOPE_CONTEXT = copy.deepcopy(ALERT_2_CONTEXT)

CHECK_ENTITIES_PARAMS = MOCK_DATA["check_entities_parameters"]
CHECK_ENTITIES_ALERT_SCOPE_CONTEXT = copy.deepcopy(ALERT_1_CONTEXT)
CHECK_ENTITIES_CASE_SCOPE_CONTEXT = copy.deepcopy(ALERT_1_CONTEXT)
CHECK_ENTITIES_ALERT_SCOPE_ENTITIES = [
    MockEntity(identifier=TARGET_IP, additional_properties={"key1": "val1"})
]

CONVERT_INTO_SIMULATED_CASE_ALERT_DETAILS_KEY = "convert_into_simulated_case_alert_details"
CONVERT_INTO_SIMULATED_CASE_CONTEXT = copy.deepcopy(ALERT_1_CONTEXT)
CONVERT_INTO_SIMULATED_CASE_EXPECTED_DATA_KEY = "convert_into_simulated_case_expected_data"

