from __future__ import annotations

import pathlib

from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_first_run

from sentinel_one_v2.actions import DownloadThreatFile
from sentinel_one_v2.tests.common import MOCK_THREAT
from sentinel_one_v2.tests.core.product import SentinelOneV2
from sentinel_one_v2.tests.core.session import SentinelOneV2Session
from integration_testing.common import get_def_file_content, set_is_first_run_to_true, set_is_first_run_to_false
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

CONFIG_FILE_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent / "config.json"
INTEGRATION_CONFIG: SingleJson = get_def_file_content(CONFIG_FILE_PATH)

TEST_THREAT_ID: str = "123456789012345678"

ACTION_PARAMETERS_VALID_PATH: dict[str, str | bool] = {
    "Threat ID": TEST_THREAT_ID,
    "Password": "test_password",
    "Download Folder Path": "/tmp",
    "Overwrite": True,
}

ACTION_PARAMETERS_INVALID_PATH: dict[str, str | bool] = {
    "Threat ID": TEST_THREAT_ID,
    "Password": "test_password",
    "Download Folder Path": "/nonexistent_path_xyz_abc",
    "Overwrite": True,
}


@set_metadata(parameters=ACTION_PARAMETERS_VALID_PATH, integration_config=INTEGRATION_CONFIG)
def test_download_threat_file_first_run_no_file_yet(
    _script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    """First run: fetch job created but timeline has no download link => IN_PROGRESS."""
    set_is_first_run_to_true()
    sentinel_one_v2.add_threat(TEST_THREAT_ID, MOCK_THREAT)
    DownloadThreatFile.main(is_first_run)
    # Timeline mock returns empty data list => waiting for file
    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS


@set_metadata(parameters=ACTION_PARAMETERS_INVALID_PATH, integration_config=INTEGRATION_CONFIG)
def test_download_threat_file_invalid_path(
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    set_is_first_run_to_true()
    sentinel_one_v2.add_threat(TEST_THREAT_ID, MOCK_THREAT)
    DownloadThreatFile.main(is_first_run)
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(parameters=ACTION_PARAMETERS_VALID_PATH, integration_config=INTEGRATION_CONFIG)
def test_download_threat_file_api_error(
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    set_is_first_run_to_true()
    sentinel_one_v2.simulate_api_error = True
    DownloadThreatFile.main(is_first_run)
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
