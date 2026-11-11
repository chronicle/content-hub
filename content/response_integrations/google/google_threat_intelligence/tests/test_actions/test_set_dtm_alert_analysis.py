from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput

from google_threat_intelligence.actions import set_dtm_alert_analysis
from google_threat_intelligence.core.constants import (
    INTEGRATION_DISPLAY_NAME,
    SET_DTM_ALERT_ANALYSIS_SCRIPT_NAME
)
from google_threat_intelligence.tests.common import CONFIG_PATH
from google_threat_intelligence.tests.core.session import (
    GoogleThreatIntelligenceSession,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from integration_testing.requests.response import MockResponse


ALERT_ID: str = "c4huif0mhcmiku5g7jsg"

SET_DTM_ALERT_ANALYSIS_SUCCESS_MESSAGE: str = (
    f"Successfully updated the alert with the ID '{ALERT_ID}' "
    f"in {INTEGRATION_DISPLAY_NAME}."
)


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "Alert ID": ALERT_ID,
        "Text": "Test DTM Alert Analysis",
    },
)
def test_update_analysis_text_on_an_alert(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
) -> None:

    set_dtm_alert_analysis.main()

    assert len(script_session.request_history) == 2
    assert action_output.results == ActionOutput(
        output_message=SET_DTM_ALERT_ANALYSIS_SUCCESS_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
        debug_output="",
    )


ATTACHMENT_FILE_NAME = "attachment.txt"
ATTACHMENT_FILE_CONTENT = "Test DTM Alert Analysis"

TEMP_DIR_OBJ = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
SESSION_PATH = Path(TEMP_DIR_OBJ.name)

FILE_PATH_1 = SESSION_PATH / ATTACHMENT_FILE_NAME
FILE_PATH_1.write_text(ATTACHMENT_FILE_CONTENT)

FILE_PATH_2 = SESSION_PATH / ATTACHMENT_FILE_NAME
FILE_PATH_2.write_text(ATTACHMENT_FILE_CONTENT)

ATTACHMENT_PATHS = ", ".join(
    [
        FILE_PATH_1.absolute().as_posix(),
        FILE_PATH_2.absolute().as_posix()
    ]
)


@pytest.fixture
def cleanup_temp_directory():
    """Cleans up the temporary directory after the test using it has finished."""
    yield
    TEMP_DIR_OBJ.cleanup()


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "Alert ID": ALERT_ID,
        "Text": "Test DTM Alert Analysis",
        "Attachment File Paths": ATTACHMENT_PATHS,
    },
)
def test_upload_attachments_to_an_alert_analysis(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    cleanup_temp_directory: None  # pylint: disable=redefined-outer-name, unused-argument
) -> None:
    set_dtm_alert_analysis.main()

    assert len(script_session.request_history) == 3
    assert action_output.results == ActionOutput(
        output_message=SET_DTM_ALERT_ANALYSIS_SUCCESS_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
        debug_output="",
    )


FAILED_ATTACHMENT_FILE_NAME = "400.txt"
FAILED_ATTACHMENT_FILE_CONTENT = "Test DTM Alert Analysis: HTTP 400 response"

FAILED_TEMP_DIR_OBJ = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
FAILED_SESSION_PATH = Path(FAILED_TEMP_DIR_OBJ.name)

FAILED_FILE_PATH = FAILED_SESSION_PATH / FAILED_ATTACHMENT_FILE_NAME
FAILED_FILE_PATH.write_text(FAILED_ATTACHMENT_FILE_NAME)

SET_DTM_ALERT_ANALYSIS_HTTP_400_ATTACHMENT_ERROR_MESSAGE = (
    f"Error executing action \"{SET_DTM_ALERT_ANALYSIS_SCRIPT_NAME}\"\n"
    "Reason: Attachments upload failed. The Alert may not have been saved correctly. "
    "An error occurred: 400 Client Error: None for url: None"
)


@pytest.fixture
def cleanup_failed_temp_directory():
    """Cleans up the temporary directory after the test using it has finished."""
    yield
    FAILED_TEMP_DIR_OBJ.cleanup()


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "Alert ID": ALERT_ID,
        "Text": "Test DTM Alert Analysis",
        "Attachment File Paths": FAILED_FILE_PATH.absolute().as_posix(),
    },
)
def test_upload_attachments_to_an_alert_analysis_failed_attachment(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    cleanup_failed_temp_directory: None  # pylint: disable=redefined-outer-name, unused-argument
) -> None:
    handler = MagicMock()
    handler.side_effect = [MockResponse(status_code=400)]
    script_session.routes["POST"]["/api/v3/dtm/alerts/[0-9a-z]+/attachments"] = handler

    set_dtm_alert_analysis.main()

    assert len(script_session.request_history) == 3
    assert action_output.results == ActionOutput(
        output_message=SET_DTM_ALERT_ANALYSIS_HTTP_400_ATTACHMENT_ERROR_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
        debug_output="",
    )


NONEXISTENT_FILE_PATH = (SESSION_PATH / "nonexistent" / "file.txt").absolute().as_posix()

SET_DTM_ALERT_ANALYSIS_FILE_NOT_FOUND_ERROR_MESSAGE = (
    f"Error executing action \"{SET_DTM_ALERT_ANALYSIS_SCRIPT_NAME}\"\n"
    f"Reason: The following files were not found: {NONEXISTENT_FILE_PATH}. "
    "Please check the spelling."
)

@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "Alert ID": ALERT_ID,
        "Text": "Test DTM Alert Analysis",
        "Attachment File Paths": NONEXISTENT_FILE_PATH,
    },
)
def test_upload_attachments_to_an_alert_analysis_invalid_file(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
) -> None:
    set_dtm_alert_analysis.main()

    assert len(script_session.request_history) == 0
    assert action_output.results == ActionOutput(
        output_message=SET_DTM_ALERT_ANALYSIS_FILE_NOT_FOUND_ERROR_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
        debug_output="",
    )
