from __future__ import annotations

import pathlib

from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from sentinel_one_v2.actions import GetBlackList
from sentinel_one_v2.tests.core.product import SentinelOneV2
from sentinel_one_v2.tests.core.session import SentinelOneV2Session
from integration_testing.common import get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

CONFIG_FILE_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent / "config.json"
INTEGRATION_CONFIG: SingleJson = get_def_file_content(CONFIG_FILE_PATH)

ACTION_PARAMETERS: dict[str, str | int | bool] = {
    "Hash": "",
    "Site IDs": "site_001",
    "Group IDs": "",
    "Account IDs": "",
    "Limit": 50,
    "Query": "",
    "Use Global Blacklist": False,
}


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_get_black_list_success(
    _script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    GetBlackList.main()
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters={
        "Hash": "",
        "Site IDs": "",
        "Group IDs": "",
        "Account IDs": "",
        "Limit": 50,
        "Query": "",
        "Use Global Blacklist": False,
    },
    integration_config=INTEGRATION_CONFIG,
)
def test_get_black_list_validation_error(
    _script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    """No scope specified should raise a validation error and fail the action."""
    GetBlackList.main()
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_get_black_list_api_error(
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    sentinel_one_v2.simulate_api_error = True
    GetBlackList.main()
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
