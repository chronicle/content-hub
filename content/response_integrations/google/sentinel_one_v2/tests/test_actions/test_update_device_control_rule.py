from __future__ import annotations

import json
import pathlib

from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from sentinel_one_v2.actions import UpdateDeviceControlRule
from sentinel_one_v2.tests.core.product import SentinelOneV2
from sentinel_one_v2.tests.core.session import SentinelOneV2Session
from integration_testing.common import get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

CONFIG_FILE_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent / "config.json"
INTEGRATION_CONFIG: SingleJson = get_def_file_content(CONFIG_FILE_PATH)

RULE_JSON: str = json.dumps(
    {
        "action": "Block",
        "deviceClass": "USB Mass Storage",
        "order": 2,
        "ruleName": "UpdatedRule",
        "status": "Enabled",
    }
)

ACTION_PARAMETERS: dict[str, str] = {
    "Rule ID": "rule_001",
    "Rule JSON": RULE_JSON,
}

ACTION_PARAMETERS_INVALID_JSON: dict[str, str] = {
    "Rule ID": "rule_001",
    "Rule JSON": "not valid json {",
}


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_update_device_control_rule_success(
    _script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    UpdateDeviceControlRule.main()
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert "Successfully updated" in action_output.results.output_message


@set_metadata(
    parameters=ACTION_PARAMETERS_INVALID_JSON,
    integration_config=INTEGRATION_CONFIG,
)
def test_update_device_control_rule_invalid_json(
    _script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    UpdateDeviceControlRule.main()
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_update_device_control_rule_api_error(
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    sentinel_one_v2.simulate_api_error = True
    UpdateDeviceControlRule.main()
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
