from __future__ import annotations

import pathlib

from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from sentinel_one_v2.actions import GetThreats
from sentinel_one_v2.tests.common import MOCK_THREAT_FULL
from sentinel_one_v2.tests.core.product import SentinelOneV2
from sentinel_one_v2.tests.core.session import SentinelOneV2Session
from integration_testing.common import get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

CONFIG_FILE_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent / "config.json"
INTEGRATION_CONFIG: SingleJson = get_def_file_content(CONFIG_FILE_PATH)

TEST_THREAT_ID: str = "123456789012345678"

ACTION_PARAMETERS: dict[str, str | int] = {
    "Mitigation Status": "",
    "Created until": "",
    "Created from": "",
    "Resolved Threats": False,
    "Threat Display Name": "",
    "Limit": 25,
    "API Version": "2.1",
}


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_get_threats_success(
    _script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    sentinel_one_v2.add_threat(TEST_THREAT_ID, MOCK_THREAT_FULL)
    GetThreats.main()
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_get_threats_no_results(
    _script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    # No threats added — session returns empty list
    GetThreats.main()
    assert action_output.results.result_value is not None
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_get_threats_api_error(
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    sentinel_one_v2.simulate_api_error = True
    GetThreats.main()
    assert action_output.results.execution_state == ExecutionState.FAILED
