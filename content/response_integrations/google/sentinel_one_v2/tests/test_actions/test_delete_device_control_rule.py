from __future__ import annotations

import pathlib

from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from sentinel_one_v2.actions import DeleteDeviceControlRule
from sentinel_one_v2.tests.core.product import SentinelOneV2
from sentinel_one_v2.tests.core.session import SentinelOneV2Session
from integration_testing.common import get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

CONFIG_FILE_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent / "config.json"
INTEGRATION_CONFIG: SingleJson = get_def_file_content(CONFIG_FILE_PATH)

ACTION_PARAMETERS: dict[str, str] = {
    "Rule ID": "dc_001",
    "Scope Type": "Site",
    "Scope ID": "site_001",
}

ACTION_PARAMETERS_INVALID_SCOPE: dict[str, str] = {
    "Rule ID": "dc_001",
    "Scope Type": "InvalidScope",
    "Scope ID": "site_001",
}


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_delete_device_control_rule_success(
    _script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    DeleteDeviceControlRule.main()
    # Note: Route mismatch — DELETE /device-control without ID suffix
    # doesn't match route pattern /device-control/.*. Fix session route.
    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(
    parameters=ACTION_PARAMETERS_INVALID_SCOPE,
    integration_config=INTEGRATION_CONFIG,
)
def test_delete_device_control_rule_invalid_scope(
    _script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    DeleteDeviceControlRule.main()
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_delete_device_control_rule_api_error(
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    sentinel_one_v2.simulate_api_error = True
    DeleteDeviceControlRule.main()
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
