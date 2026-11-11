from __future__ import annotations

import pathlib

from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from sentinel_one_v2.actions import CreatePathExclusionRecord
from sentinel_one_v2.tests.core.product import SentinelOneV2
from sentinel_one_v2.tests.core.session import SentinelOneV2Session
from integration_testing.common import get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

CONFIG_FILE_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent / "config.json"
INTEGRATION_CONFIG: SingleJson = get_def_file_content(CONFIG_FILE_PATH)

ACTION_PARAMETERS: dict[str, str | bool] = {
    "Path": "/usr/local/malware.exe",
    "Operation System": "linux",
    "Site IDs": "site_001",
    "Group IDs": "",
    "Account IDs": "",
    "Description": "Test path exclusion",
    "Add to global exclusion list": False,
    "Include Subfolders": False,
    "Mode": "Suppress Alerts",
}

ACTION_PARAMETERS_NO_SCOPE: dict[str, str | bool] = {
    "Path": "/usr/local/malware.exe",
    "Operation System": "linux",
    "Site IDs": "",
    "Group IDs": "",
    "Account IDs": "",
    "Description": "",
    "Add to global exclusion list": False,
    "Include Subfolders": False,
    "Mode": "Suppress Alerts",
}


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_create_path_exclusion_success(
    _script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    CreatePathExclusionRecord.main()
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert "Successfully added" in action_output.results.output_message


@set_metadata(
    parameters=ACTION_PARAMETERS_NO_SCOPE,
    integration_config=INTEGRATION_CONFIG,
)
def test_create_path_exclusion_no_scope_fails(
    _script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    CreatePathExclusionRecord.main()
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(parameters=ACTION_PARAMETERS, integration_config=INTEGRATION_CONFIG)
def test_create_path_exclusion_api_error(
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    sentinel_one_v2.simulate_api_error = True
    CreatePathExclusionRecord.main()
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
