from __future__ import annotations

import pathlib

from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.types import Entity, SingleJson

from sentinel_one_v2.actions import ReconnectAgentToTheNetwork
from sentinel_one_v2.tests.common import MOCK_AGENT
from sentinel_one_v2.tests.core.product import SentinelOneV2
from sentinel_one_v2.tests.core.session import SentinelOneV2Session
from integration_testing.common import create_entity, get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

CONFIG_FILE_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent / "config.json"
INTEGRATION_CONFIG: SingleJson = get_def_file_content(CONFIG_FILE_PATH)

TEST_HOST_NAME: str = "windows-server"
HOST_NAME_ENTITY: Entity = create_entity(identifier=TEST_HOST_NAME, type_=EntityTypesEnum.HOST_NAME)


@set_metadata(
    integration_config=INTEGRATION_CONFIG,
    entities=[HOST_NAME_ENTITY],
)
def test_reconnect_agent_success(
    _script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    sentinel_one_v2.add_agent(TEST_HOST_NAME, MOCK_AGENT)
    ReconnectAgentToTheNetwork.main()
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert TEST_HOST_NAME in action_output.results.output_message


@set_metadata(
    integration_config=INTEGRATION_CONFIG,
    entities=[HOST_NAME_ENTITY],
)
def test_reconnect_agent_not_found(
    _script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    ReconnectAgentToTheNetwork.main()
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config=INTEGRATION_CONFIG,
    entities=[HOST_NAME_ENTITY],
)
def test_reconnect_agent_api_error(
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    sentinel_one_v2.simulate_api_error = True
    ReconnectAgentToTheNetwork.main()
    assert action_output.results.execution_state == ExecutionState.FAILED
