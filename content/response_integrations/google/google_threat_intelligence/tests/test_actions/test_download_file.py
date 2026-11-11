from __future__ import annotations

from unittest.mock import mock_open, patch

import pytest
from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.base.data_models import ActionJsonOutput, ActionOutput

from google_threat_intelligence.actions import download_file
from google_threat_intelligence.tests.common import CONFIG_PATH
from google_threat_intelligence.tests.core.session import (
    GoogleThreatIntelligenceSession,
)
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

NO_PARAMS_ERROR_MESSAGE = (
    "Failed during parameter extraction, Error: "
    "Missing mandatory parameter Download Folder Path\n"
)
VALID_SHA_256_HASH = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"
SUCCESS_ACTION_OUTPUT_MESSAGE = (
    f"{download_file.SUCCESS_MESSAGE}"
    f"{download_file.INTEGRATION_DISPLAY_NAME}: "
    f"{VALID_SHA_256_HASH} \n"
)

ERROR_OUTPUT_MESSAGE = (
    "Error executing action GoogleThreatIntelligence - Download File.\n"
    "Reason: \nNo related files were found for the provided entities.\n "
    "Failed to download in Google Threat Intelligence: \n "
    f"{VALID_SHA_256_HASH} \n"
    f"Exception for entity '{VALID_SHA_256_HASH}': "
    f"files with path /tmp/{VALID_SHA_256_HASH} already exist. "
    "Please delete the files or set 'Overwrite' to true."
)


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={},
)
def test_download_file_no_input_params_error() -> None:
    with pytest.raises(Exception) as error:
        download_file.main()

    assert type(error.value).__name__ == "ParameterExtractionError"
    assert str(error.value) == NO_PARAMS_ERROR_MESSAGE


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={"Download Folder Path": "/tmp/"},
)
def test_download_file_no_target_entities(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
) -> None:
    download_file.main()

    assert len(script_session.request_history) == 1
    assert (script_session.request_history[0].request.url.path ==
            "/api/v3/metadata")
    assert action_output.results == ActionOutput(
        output_message=download_file.NON_RELATED_FILES_ERROR_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
        debug_output="",
    )


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={"Download Folder Path": "/tmp/"},
    entities=[create_entity("aasdasd.txt", EntityTypesEnum.FILE_HASH)],
)
def test_download_file_invalid_hash_name(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
) -> None:
    mock_file_open = mock_open(read_data="some file content")
    with patch("utils.open", mock_file_open):
        download_file.main()

    assert len(script_session.request_history) == 1
    assert (script_session.request_history[0].request.url.path ==
            "/api/v3/metadata")

    assert action_output.results == ActionOutput(
        output_message=download_file.NON_RELATED_FILES_ERROR_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
        debug_output="",
    )


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={"Download Folder Path": "/tmp/", "Overwrite": True},
    entities=[create_entity(VALID_SHA_256_HASH, EntityTypesEnum.FILE_HASH)],
)
def test_download_file_valid_hash_name(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
) -> None:
    mock_file_open = mock_open(read_data="some file content")
    with patch("utils.open", mock_file_open):
        download_file.main()

    assert len(script_session.request_history) == 2
    assert (script_session.request_history[0].request.url.path ==
            "/api/v3/metadata")
    assert (
        script_session.request_history[1].request.url.path
        == f"/api/v3/files/{VALID_SHA_256_HASH}/download"
    )
    print("========== action_output.results ======================")
    print(action_output.results)
    print("================================")
    assert action_output.results == ActionOutput(
        output_message=SUCCESS_ACTION_OUTPUT_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=ActionJsonOutput(
            title="JsonResult",
            content="",
            type=None,
            is_for_entity=False,
            json_result={"absolute_file_paths": [f"/tmp/{VALID_SHA_256_HASH}"]},
        ),
        debug_output="",
    )


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={"Download Folder Path": "/tmp/", "Overwrite": False},
    entities=[create_entity(VALID_SHA_256_HASH, EntityTypesEnum.FILE_HASH)],
)
def test_download_file_does_not_exist_exception(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
) -> None:
    mock_file_open = mock_open(read_data="some file content")

    with patch("utils.open", mock_file_open):
        with patch("os.path.exists", return_value=True):
            download_file.main()

    assert len(script_session.request_history) == 1
    assert (script_session.request_history[0].request.url.path ==
            "/api/v3/metadata")
    assert action_output.results == ActionOutput(
        output_message=ERROR_OUTPUT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
        debug_output="",
    )
