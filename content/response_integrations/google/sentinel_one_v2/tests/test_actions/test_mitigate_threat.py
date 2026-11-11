from __future__ import annotations

import pathlib

from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from sentinel_one_v2.actions import MitigateThreat
from sentinel_one_v2.tests.common import MOCK_THREAT_FULL
from sentinel_one_v2.tests.core.product import SentinelOneV2
from sentinel_one_v2.tests.core.session import SentinelOneV2Session
from integration_testing.common import get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

CONFIG_FILE_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent / "config.json"
INTEGRATION_CONFIG: SingleJson = get_def_file_content(CONFIG_FILE_PATH)

TEST_THREAT_ID: str = "123456789012345678"

ACTION_PARAMETERS: dict[str, str] = {
    "Mitigation action": "Quarantine",
    "Threat IDs": TEST_THREAT_ID,
}


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_mitigate_threat_success(
    _script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    sentinel_one_v2.add_threat(TEST_THREAT_ID, MOCK_THREAT_FULL)
    MitigateThreat.main()
    assert action_output.results.execution_state in (
        ExecutionState.COMPLETED,
        ExecutionState.FAILED,
    )


@set_metadata(
    parameters={"Mitigation action": "Quarantine", "Threat IDs": "nonexistent_id_9999"},
    integration_config=INTEGRATION_CONFIG,
)
def test_mitigate_threat_not_found(
    _script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    MitigateThreat.main()
    assert action_output.results.result_value is False


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_mitigate_threat_api_error(
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    sentinel_one_v2.simulate_api_error = True
    MitigateThreat.main()
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
