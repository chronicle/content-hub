from __future__ import annotations

import pathlib

from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from sentinel_one_v2.actions import AddThreatNote
from sentinel_one_v2.tests.common import MOCK_THREAT
from sentinel_one_v2.tests.core.product import SentinelOneV2
from sentinel_one_v2.tests.core.session import SentinelOneV2Session
from integration_testing.common import get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

CONFIG_FILE_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent / "config.json"
INTEGRATION_CONFIG: SingleJson = get_def_file_content(CONFIG_FILE_PATH)

TEST_THREAT_ID: str = "123456789012345678"

ACTION_PARAMETERS: dict[str, str] = {
    "Threat ID": TEST_THREAT_ID,
    "Note": "Test note from automated test",
}


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_add_threat_note_success(
    _script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    sentinel_one_v2.add_threat(TEST_THREAT_ID, MOCK_THREAT)
    AddThreatNote.main()
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert "Successfully added note" in action_output.results.output_message


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_add_threat_note_api_error(
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    sentinel_one_v2.simulate_api_error = True
    AddThreatNote.main()
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
