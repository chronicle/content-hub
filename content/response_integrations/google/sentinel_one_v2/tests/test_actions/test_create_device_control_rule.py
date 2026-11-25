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

import json
import pathlib

from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from sentinel_one_v2.actions import CreateDeviceControlRule
from sentinel_one_v2.tests.core.product import SentinelOneV2
from sentinel_one_v2.tests.core.session import SentinelOneV2Session
from integration_testing.common import get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

CONFIG_FILE_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent / "config.json"
INTEGRATION_CONFIG: SingleJson = get_def_file_content(CONFIG_FILE_PATH)

RULE_JSON: str = json.dumps(
    {
        "action": "Allow",
        "deviceClass": "USB Mass Storage",
        "order": 1,
        "ruleName": "TestRule",
        "status": "Enabled",
    }
)

SCOPE_JSON: str = json.dumps(
    {
        "siteIds": ["site_001"],
    }
)

ACTION_PARAMETERS: dict[str, str] = {
    "Rule JSON": RULE_JSON,
    "Scope JSON": SCOPE_JSON,
}

ACTION_PARAMETERS_INVALID_JSON: dict[str, str] = {
    "Rule JSON": "not valid json {",
    "Scope JSON": SCOPE_JSON,
}


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_create_device_control_rule_success(
    _script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    CreateDeviceControlRule.main()
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert "Successfully created" in action_output.results.output_message


@set_metadata(
    parameters=ACTION_PARAMETERS_INVALID_JSON,
    integration_config=INTEGRATION_CONFIG,
)
def test_create_device_control_rule_invalid_json(
    _script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    CreateDeviceControlRule.main()
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_create_device_control_rule_api_error(
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    sentinel_one_v2.simulate_api_error = True
    CreateDeviceControlRule.main()
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
