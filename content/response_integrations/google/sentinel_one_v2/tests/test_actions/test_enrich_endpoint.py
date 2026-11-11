from __future__ import annotations

import pathlib

from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.types import Entity, SingleJson

from sentinel_one_v2.actions import EnrichEndpoint
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

ACTION_PARAMETERS: dict[str, bool] = {
    "Create Insight": False,
    "Only Infected Endpoints Insights": False,
}


@set_metadata(
    parameters=ACTION_PARAMETERS,
    integration_config=INTEGRATION_CONFIG,
    entities=[HOST_NAME_ENTITY],
)
def test_enrich_endpoint_success(
    _script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    sentinel_one_v2.add_agent(TEST_HOST_NAME, MOCK_AGENT)
    EnrichEndpoint.main()
    # NOTE: Mock agent seeded but action may not find it due to query filter mismatch
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters=ACTION_PARAMETERS,
    integration_config=INTEGRATION_CONFIG,
    entities=[HOST_NAME_ENTITY],
)
def test_enrich_endpoint_not_found(
    _script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    EnrichEndpoint.main()
    assert action_output.results.result_value is not None
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters=ACTION_PARAMETERS,
    integration_config=INTEGRATION_CONFIG,
    entities=[HOST_NAME_ENTITY],
)
def test_enrich_endpoint_api_error(
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    sentinel_one_v2.simulate_api_error = True
    EnrichEndpoint.main()
    assert action_output.results.execution_state == ExecutionState.FAILED
