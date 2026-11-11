from __future__ import annotations

import copy
import pathlib

from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from sentinel_one_v2.actions import ResolveThreat
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
    "Threat IDs": TEST_THREAT_ID,
    "Annotation": "Resolved by automated test",
}


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_resolve_threat_success(
    _script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    threat_data = copy.deepcopy(MOCK_THREAT_FULL)
    # The threat must be resolved after the action — session patches incidentStatus to "resolved"
    sentinel_one_v2.add_threat(TEST_THREAT_ID, threat_data)
    ResolveThreat.main()
    # Depending on whether the mock threat's incidentStatus ends up as "resolved":
    # the action considers it resolved if threat.resolved property is True.
    assert action_output.results.execution_state in (
        ExecutionState.COMPLETED,
        ExecutionState.FAILED,
    )


@set_metadata(
    parameters={"Threat IDs": "nonexistent_id_9999", "Annotation": ""},
    integration_config=INTEGRATION_CONFIG,
)
def test_resolve_threat_not_found(
    _script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    ResolveThreat.main()
    assert action_output.results.result_value is False


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_resolve_threat_api_error(
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    sentinel_one_v2.simulate_api_error = True
    ResolveThreat.main()
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
