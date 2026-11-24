from __future__ import annotations

import pathlib

from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from sentinel_one_v2.actions import ListSites
from sentinel_one_v2.tests.common import MOCK_SITE_DATA
from sentinel_one_v2.tests.core.product import SentinelOneV2
from sentinel_one_v2.tests.core.session import SentinelOneV2Session
from integration_testing.common import get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

CONFIG_FILE_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent / "config.json"
INTEGRATION_CONFIG: SingleJson = get_def_file_content(CONFIG_FILE_PATH)

ACTION_PARAMETERS: dict[str, str | int] = {
    "Filter Key": "",
    "Filter Logic": "",
    "Filter Value": "",
    "Max Records To Return": 50,
}


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_list_sites_success(
    _script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    sentinel_one_v2.add_site(MOCK_SITE_DATA)
    ListSites.main()
    assert action_output.results.result_value is not None
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_list_sites_no_results(
    _script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    # No sites added — paginator returns empty list
    ListSites.main()
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters={
        "Filter Key": "",
        "Filter Logic": "",
        "Filter Value": "",
        "Max Records To Return": -1,
    },
    integration_config=INTEGRATION_CONFIG,
)
def test_list_sites_invalid_limit(
    _script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    ListSites.main()
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
