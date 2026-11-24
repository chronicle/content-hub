import pathlib

from TIPCommon.base.action import EntityTypesEnum
from TIPCommon.types import Entity, SingleJson
from TIPCommon.utils import is_first_run

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from integration_testing.common import get_def_file_content
from integration_testing.common import create_entity
from integration_testing.common import set_is_first_run_to_true, set_is_first_run_to_false

from sentinel_one_v2.tests.common import MOCK_AGENT, get_endpoint_list
from sentinel_one_v2.tests.core.product import SentinelOneV2
from sentinel_one_v2.tests.core.session import SentinelOneV2Session
from sentinel_one_v2.actions import GetEventsForEndpointHoursBack


CONFIG_FILE_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent / "config.json"
INTEGRATION_CONFIG: SingleJson = get_def_file_content(CONFIG_FILE_PATH)

ACTION_PARAMETERS: dict[str, int | bool] = {
    "Hours Back": 24,
    "Events Amount Limit": 50,
    "Include File Events Information": False,
    "Include Indicator Events Information": False,
    "Include DNS Events Information": False,
    "Include Network Action Events Information": False,
    "Include URL Events Information": False,
    "Include Registry Events Information": False,
    "Include Scheduled Task Events Information": False,
}

VALID_HOST_NAME_ENTITY_OUTPUT_MSG: str = (
    "Successfully retrieved information about the"
    " events for the following endpoints:\n"
    "   windows-server\n"
)
NO_AGENT_FOUND_MSG: str = "No suitable endpoints were found."
TEST_HOST_NAME: str = "windows-server"
HOST_NAME_ENTITY: Entity = create_entity(
    identifier=TEST_HOST_NAME, type_=EntityTypesEnum.HOST_NAME
)


@set_metadata(
    parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG, entities=[]
)
def test_empty_run(
    script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    set_is_first_run_to_true()
    GetEventsForEndpointHoursBack.main(is_first_run)
    accessed_endpoints: list[str] = get_endpoint_list(script_session.request_history)

    assert accessed_endpoints == ["/web/api/v2.1/agents/count"]
    assert action_output.results.output_message == NO_AGENT_FOUND_MSG
    assert action_output.results.result_value is False


@set_metadata(
    parameters=ACTION_PARAMETERS,
    integration_config=INTEGRATION_CONFIG,
    entities=[HOST_NAME_ENTITY],
)
def test_run_with_entity(
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    set_is_first_run_to_true()
    sentinel_one_v2.add_agent(TEST_HOST_NAME, MOCK_AGENT)

    GetEventsForEndpointHoursBack.main(is_first_run)

    accessed_endpoints: list[str] = get_endpoint_list(script_session.request_history)

    assert accessed_endpoints == [
        "/web/api/v2.1/agents/count",
        "/web/api/v2.1/agents",
        "/web/api/v2.1/dv/init-query",
        "/web/api/v2.1/dv/query-status",
        "/web/api/v2.1/dv/query-status",
        "/web/api/v2.1/dv/events/process",
    ]
    assert action_output.results.output_message == VALID_HOST_NAME_ENTITY_OUTPUT_MSG
    assert action_output.results.result_value is True


@set_metadata(
    parameters=ACTION_PARAMETERS,
    integration_config=INTEGRATION_CONFIG,
    entities=[HOST_NAME_ENTITY],
)
def test_run_not_first_run(
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    set_is_first_run_to_false()
    sentinel_one_v2.add_agent(TEST_HOST_NAME, MOCK_AGENT)

    GetEventsForEndpointHoursBack.main(False)

    accessed_endpoints: list[str] = get_endpoint_list(script_session.request_history)

    assert accessed_endpoints == ["/web/api/v2.1/agents/count"]
    assert action_output.results.output_message == NO_AGENT_FOUND_MSG
    assert action_output.results.result_value is False
