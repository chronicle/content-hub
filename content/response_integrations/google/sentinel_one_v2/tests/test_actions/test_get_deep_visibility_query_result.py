from __future__ import annotations

import pathlib

from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_first_run

from sentinel_one_v2.actions import GetDeepVisibilityQueryResult
from sentinel_one_v2.tests.common import MOCK_AGENT
from sentinel_one_v2.tests.core.product import SentinelOneV2
from sentinel_one_v2.tests.core.session import SentinelOneV2Session
from integration_testing.common import get_def_file_content, set_is_first_run_to_true, set_is_first_run_to_false
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

CONFIG_FILE_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent / "config.json"
INTEGRATION_CONFIG: SingleJson = get_def_file_content(CONFIG_FILE_PATH)

TEST_UUID: str = "1"
ACTION_PARAMETERS: dict[str, str | int] = {
    "Query ID": TEST_UUID,
    "Limit": 50,
}


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_get_deep_visibility_query_result_running(
    _script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    """First poll: query returns RUNNING state => action stays IN_PROGRESS."""
    set_is_first_run_to_true()
    sentinel_one_v2.add_agent("windows-server", MOCK_AGENT)
    GetDeepVisibilityQueryResult.main(is_first_run)
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_get_deep_visibility_query_result_finished(
    _script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    """Second poll: query returns FINISHED state => action completes."""
    set_is_first_run_to_false()
    sentinel_one_v2.add_agent("windows-server", MOCK_AGENT)
    # Force the mock to immediately return FINISHED by incrementing past the first call
    sentinel_one_v2.increment_query_status_calls()
    GetDeepVisibilityQueryResult.main(is_first_run)
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_get_deep_visibility_query_result_api_error(
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    set_is_first_run_to_true()
    sentinel_one_v2.simulate_api_error = True
    GetDeepVisibilityQueryResult.main(is_first_run)
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
