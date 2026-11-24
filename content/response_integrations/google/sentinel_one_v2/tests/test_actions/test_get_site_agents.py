from __future__ import annotations

import pathlib

from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson
from sentinel_one_v2.actions import GetSiteAgents

from sentinel_one_v2.tests.common import MOCK_SITE_DATA, MOCK_AGENT
from sentinel_one_v2.tests.core.product import SentinelOneV2
from sentinel_one_v2.tests.core.session import SentinelOneV2Session
from integration_testing.common import get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


CONFIG_FILE_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent / "config.json"
INTEGRATION_CONFIG: SingleJson = get_def_file_content(CONFIG_FILE_PATH)

ACTION_PARAMETERS: dict[str, str | int] = {
    "Site Name": "HOP",
    "Max Agents To Return": 1000,
}


@set_metadata(
    parameters=ACTION_PARAMETERS,
    integration_config=INTEGRATION_CONFIG,
)
def test_get_site_agents_success(
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    """Test for GetSiteAgents action success scenario."""

    sentinel_one_v2.add_site(MOCK_SITE_DATA)
    sentinel_one_v2.add_agent_to_site(MOCK_AGENT)
    GetSiteAgents.main()
    assert len(script_session.request_history) == 3
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert (
        action_output.results.output_message.strip()
        == "Successfully returned information about the hosts from Site HOP in "
        "SentinelOne"
    )


@set_metadata(
    integration_config=INTEGRATION_CONFIG,
    parameters=ACTION_PARAMETERS,
)
def test_get_site_agents_no_agents_found(
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    """Test for GetSiteAgents action when site exists but has no agents."""
    sentinel_one_v2.add_site(MOCK_SITE_DATA)
    GetSiteAgents.main()
    assert len(script_session.request_history) == 3
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert (
        action_output.results.output_message.strip()
        == "No hosts are associated with Site HOP in SentinelOne"
    )


@set_metadata(
    integration_config=INTEGRATION_CONFIG,
    parameters=ACTION_PARAMETERS,
)
def test_get_site_agents_site_not_found(
    script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    """Test for GetSiteAgents action when the site is not found."""

    GetSiteAgents.main()

    assert len(script_session.request_history) == 2
    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
    expected_message = (
        'Error executing action "SentinelOneV2 - Get Site Agents"\n'
        'Reason: Site "HOP" not found in SentinelOne. Please check the spelling.'
    )
    assert action_output.results.output_message.strip() == expected_message


@set_metadata(
    integration_config=INTEGRATION_CONFIG,
    parameters=ACTION_PARAMETERS,
)
def test_get_site_agents_api_error(
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    """Test for GetSiteAgents action when the API returns an error."""
    sentinel_one_v2.add_site(MOCK_SITE_DATA)
    sentinel_one_v2.simulate_api_error = True

    GetSiteAgents.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
    assert "Simulated API Error" in action_output.results.output_message
