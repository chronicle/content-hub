from __future__ import annotations

import pathlib
import shutil
import tempfile
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

import pytest
import requests
from pytest_mock import MockerFixture

from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from google_threat_intelligence.core.constants import (
    AGENT_CONNECTIVITY_ERROR_MESSAGE,
    AGENT_DIRECTORY_PATHS_ERROR_MESSAGE,
    AGENT_EMPTY_FILES_ERROR_MESSAGE,
    AGENT_MISSING_SESSION_ID_ERROR_MESSAGE,
    AGENT_NO_FINAL_RESPONSE_ERROR_MESSAGE,
    AGENT_NO_RESPONSE_TEXT_MESSAGE,
    AGENT_RESPONSE_TEXT_SEPARATOR,
)
from google_threat_intelligence.core.exceptions import GoogleThreatIntelligenceHTTPException
from google_threat_intelligence.actions.ask_threat_intelligence_agent import (
    AskThreatIntelligenceAgent,
)
from google_threat_intelligence.tests.common import (
    AGENT_SESSION_TITLE,
    build_agent_thought_event,
    build_agentic_session,
    build_conversation_history,
    build_final_response_event,
    build_split_final_response_event,
    build_user_message_event,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

if TYPE_CHECKING:
    from pytest_mock import MockType

SCRIPT_NAME: str = "GoogleThreatIntelligence - Ask Threat Intelligence Agent"
INTEGRATION_CONFIG: SingleJson = {
    "API Root": "https://www.virustotal.com",
    "API Key": "TEST_KEY",
    "ASM Project Name": "",
    "Verify SSL": True,
}
PROMPT: str = "What is APT29?"
FOLLOW_UP_PROMPT: str = "APT29"
FILES_PROMPT: str = "Analyze these files."
NEW_SESSION_ID: str = "test-session-123"
EXISTING_SESSION_ID: str = "existing-session-456"
PREVIOUS_ANSWER: str = "APT29 is a sophisticated threat group."
NEW_ANSWER: str = "APT29 commonly uses spear phishing for initial access."
ATTACHMENTS_DIR: pathlib.Path = pathlib.Path(tempfile.gettempdir()) / "gti_ask_agent_attachments"
ATTACHMENT_PATHS: list[str] = [str(ATTACHMENTS_DIR / "file1.exe"), str(ATTACHMENTS_DIR / "file2.dll")]
ATTACHMENT_CONTENT: str = "sample content"
QUOTED_DUPLICATED_FILE_PATHS: str = (
    f"\"{ATTACHMENT_PATHS[0]}\", {ATTACHMENT_PATHS[0]}, '{ATTACHMENT_PATHS[1]}'"
)
EMPTY_FILE_PATH: str = str(ATTACHMENTS_DIR / "empty.txt")
MISSING_FILE_PATH: str = str(ATTACHMENTS_DIR / "missing.exe")
MISSING_FILE_ERROR: str = (
    f"The following files were not found: {MISSING_FILE_PATH}. Please check the spelling."
)
UNAUTHORIZED_ERROR: str = "Error: 401 - Wrong API key"
SERVER_ERROR: str = "Error: 500 - Internal server error."
SUCCESS_MESSAGE: str = "Successfully executed prompt in Google Threat Intelligence."
NEW_SESSION_PARAMETERS: SingleJson = {
    "Prompt": PROMPT,
    "Session ID": "",
    "File Paths": "",
    "Delete Session After Completion": False,
}
EXISTING_SESSION_PARAMETERS: SingleJson = {
    **NEW_SESSION_PARAMETERS,
    "Prompt": FOLLOW_UP_PROMPT,
    "Session ID": EXISTING_SESSION_ID,
}
PREVIOUS_TURN_EVENTS: list[SingleJson] = [
    build_user_message_event(PROMPT),
    build_final_response_event(PREVIOUS_ANSWER),
]
HISTORY_TURNS: int = 10
LONG_HISTORY_EVENTS: list[SingleJson] = [
    *build_conversation_history(HISTORY_TURNS),
    build_user_message_event(FOLLOW_UP_PROMPT),
    build_split_final_response_event(PREVIOUS_ANSWER),
]
NEW_ANSWER_TABLE: str = "| Name | Sponsor |\n| :--- | :--- |\n| APT29 | SVR |"
NEW_ANSWER_HEADING: str = "#### APT29 Tactics & Techniques"
EXPECTED_SPLIT_ANSWER: str = AGENT_RESPONSE_TEXT_SEPARATOR.join(
    [NEW_ANSWER, NEW_ANSWER_TABLE, NEW_ANSWER_HEADING],
)


@pytest.fixture(name="attachments")
def attachments_fixture() -> Iterator[None]:
    """Create the attachment files on disk and remove them after the test."""
    ATTACHMENTS_DIR.mkdir(exist_ok=True)
    for attachment_path in ATTACHMENT_PATHS:
        pathlib.Path(attachment_path).write_text(ATTACHMENT_CONTENT, encoding="utf-8")
    pathlib.Path(EMPTY_FILE_PATH).touch()
    yield
    shutil.rmtree(ATTACHMENTS_DIR)


def patch_api(mocker: MockerFixture, method: str, **kwargs: Any) -> MockType:
    """Patch an ApiManager method."""
    return mocker.patch(f"api_manager.ApiManager.{method}", **kwargs)


def run_action() -> None:
    """Run the action."""
    AskThreatIntelligenceAgent(SCRIPT_NAME).run()


def build_new_split_answer_event() -> SingleJson:
    """Build the newest prompt's answer, split around MITRE tree widgets."""
    return build_split_final_response_event(NEW_ANSWER, NEW_ANSWER_TABLE, NEW_ANSWER_HEADING)


@set_metadata(integration_config=INTEGRATION_CONFIG, parameters=NEW_SESSION_PARAMETERS)
def test_new_session_completes_with_answer(
    action_output: MockActionOutput,
    mocker: MockerFixture,
) -> None:
    """Test a new session completes with the answer from the synchronous response."""
    patch_api(mocker, "test_connectivity")
    mock_delete = patch_api(mocker, "delete_agent_session")
    mock_post = patch_api(
        mocker,
        "post_agent_prompt",
        return_value=build_agentic_session(
            [build_user_message_event(PROMPT), build_final_response_event(NEW_ANSWER)],
            NEW_SESSION_ID,
        ),
    )

    run_action()

    mock_post.assert_called_once_with(prompt=PROMPT, session_id=None, file_paths=None)
    mock_delete.assert_not_called()
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert action_output.results.output_message == SUCCESS_MESSAGE
    assert action_output.results.json_output.json_result == {
        "session_id": NEW_SESSION_ID,
        "title": AGENT_SESSION_TITLE,
        "response_text": NEW_ANSWER,
    }


@set_metadata(
    integration_config=INTEGRATION_CONFIG,
    parameters={**NEW_SESSION_PARAMETERS, "Delete Session After Completion": True},
)
def test_new_session_deletes_session_when_requested(
    action_output: MockActionOutput,
    mocker: MockerFixture,
) -> None:
    """Test the session is deleted after the answer is retrieved when cleanup is requested."""
    patch_api(mocker, "test_connectivity")
    mock_delete = patch_api(mocker, "delete_agent_session")
    patch_api(
        mocker,
        "post_agent_prompt",
        return_value=build_agentic_session([build_final_response_event(NEW_ANSWER)], NEW_SESSION_ID),
    )

    run_action()

    mock_delete.assert_called_once_with(NEW_SESSION_ID)
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output.json_result["response_text"] == NEW_ANSWER


@set_metadata(integration_config=INTEGRATION_CONFIG, parameters=NEW_SESSION_PARAMETERS)
def test_response_without_final_answer_fails_with_session_id(
    action_output: MockActionOutput,
    mocker: MockerFixture,
) -> None:
    """Test the action fails with the session ID when the response has no final answer."""
    patch_api(mocker, "test_connectivity")
    mock_delete = patch_api(mocker, "delete_agent_session")
    patch_api(
        mocker,
        "post_agent_prompt",
        return_value=build_agentic_session([build_agent_thought_event()], NEW_SESSION_ID),
    )

    run_action()

    mock_delete.assert_not_called()
    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
    assert (
        AGENT_NO_FINAL_RESPONSE_ERROR_MESSAGE.format(session_id=NEW_SESSION_ID)
        in action_output.results.output_message
    )


@set_metadata(
    integration_config=INTEGRATION_CONFIG,
    parameters={**NEW_SESSION_PARAMETERS, "Delete Session After Completion": True},
)
def test_response_without_final_answer_still_deletes_session_when_requested(
    action_output: MockActionOutput,
    mocker: MockerFixture,
) -> None:
    """Test the session is cleaned up when requested, even when the response has no final answer."""
    patch_api(mocker, "test_connectivity")
    mock_delete = patch_api(mocker, "delete_agent_session")
    patch_api(
        mocker,
        "post_agent_prompt",
        return_value=build_agentic_session([build_agent_thought_event()], NEW_SESSION_ID),
    )

    run_action()

    mock_delete.assert_called_once_with(NEW_SESSION_ID)
    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(integration_config=INTEGRATION_CONFIG, parameters=NEW_SESSION_PARAMETERS)
def test_final_answer_without_text_sets_is_success_false(
    action_output: MockActionOutput,
    mocker: MockerFixture,
) -> None:
    """Test a final answer without text completes the action with is_success set to false."""
    patch_api(mocker, "test_connectivity")
    patch_api(
        mocker,
        "post_agent_prompt",
        return_value=build_agentic_session(
            [build_user_message_event(PROMPT), build_final_response_event()],
            NEW_SESSION_ID,
        ),
    )

    run_action()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is False
    assert action_output.results.output_message == AGENT_NO_RESPONSE_TEXT_MESSAGE.format(
        session_id=NEW_SESSION_ID
    )
    assert action_output.results.json_output.json_result["response_text"] is None


@set_metadata(integration_config=INTEGRATION_CONFIG, parameters=EXISTING_SESSION_PARAMETERS)
def test_existing_session_completes_with_answer_from_turn_only_response(
    action_output: MockActionOutput,
    mocker: MockerFixture,
) -> None:
    """Test a follow-up completes when the response holds only the new prompt's events.

    This is how GTI replies to a message posted to an existing session.
    """
    patch_api(mocker, "test_connectivity")
    mock_post = patch_api(
        mocker,
        "post_agent_prompt",
        return_value=build_agentic_session(
            [build_agent_thought_event(), build_final_response_event(NEW_ANSWER)],
            EXISTING_SESSION_ID,
        ),
    )

    run_action()

    mock_post.assert_called_once_with(
        prompt=FOLLOW_UP_PROMPT,
        session_id=EXISTING_SESSION_ID,
        file_paths=None,
    )
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert action_output.results.output_message == SUCCESS_MESSAGE
    assert action_output.results.json_output.json_result["response_text"] == NEW_ANSWER


@set_metadata(
    integration_config=INTEGRATION_CONFIG,
    parameters={**EXISTING_SESSION_PARAMETERS, "Delete Session After Completion": True},
)
def test_existing_session_ignores_answers_to_earlier_prompts(
    action_output: MockActionOutput,
    mocker: MockerFixture,
) -> None:
    """Test a response with the whole session returns only the answer to the new prompt."""
    patch_api(mocker, "test_connectivity")
    mock_delete = patch_api(mocker, "delete_agent_session")
    patch_api(
        mocker,
        "post_agent_prompt",
        return_value=build_agentic_session(
            [
                *PREVIOUS_TURN_EVENTS,
                build_user_message_event(FOLLOW_UP_PROMPT),
                build_final_response_event(NEW_ANSWER),
            ],
            EXISTING_SESSION_ID,
        ),
    )

    run_action()

    mock_delete.assert_called_once_with(EXISTING_SESSION_ID)
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output.json_result["response_text"] == NEW_ANSWER


@set_metadata(integration_config=INTEGRATION_CONFIG, parameters=EXISTING_SESSION_PARAMETERS)
def test_existing_session_fails_when_only_earlier_prompts_have_answers(
    action_output: MockActionOutput,
    mocker: MockerFixture,
) -> None:
    """Test an earlier answer is never returned when the new prompt has no answer."""
    patch_api(mocker, "test_connectivity")
    patch_api(
        mocker,
        "post_agent_prompt",
        return_value=build_agentic_session(
            [*PREVIOUS_TURN_EVENTS, build_user_message_event(FOLLOW_UP_PROMPT)],
            EXISTING_SESSION_ID,
        ),
    )

    run_action()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert (
        AGENT_NO_FINAL_RESPONSE_ERROR_MESSAGE.format(session_id=EXISTING_SESSION_ID)
        in action_output.results.output_message
    )


@set_metadata(integration_config=INTEGRATION_CONFIG, parameters=EXISTING_SESSION_PARAMETERS)
def test_long_session_returns_only_new_split_answer_from_turn_only_response(
    action_output: MockActionOutput,
    mocker: MockerFixture,
) -> None:
    """Test a follow-up in a long session returns only the new answer, with all its text widgets."""
    patch_api(mocker, "test_connectivity")
    patch_api(
        mocker,
        "post_agent_prompt",
        return_value=build_agentic_session(
            [build_agent_thought_event(), build_new_split_answer_event()],
            EXISTING_SESSION_ID,
        ),
    )

    run_action()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert action_output.results.json_output.json_result["response_text"] == EXPECTED_SPLIT_ANSWER


@set_metadata(integration_config=INTEGRATION_CONFIG, parameters=EXISTING_SESSION_PARAMETERS)
def test_long_session_returns_only_new_split_answer_from_full_session_response(
    action_output: MockActionOutput,
    mocker: MockerFixture,
) -> None:
    """Test a response with a whole long session returns only the split answer to the newest prompt."""
    patch_api(mocker, "test_connectivity")
    patch_api(
        mocker,
        "post_agent_prompt",
        return_value=build_agentic_session(
            [
                *LONG_HISTORY_EVENTS,
                build_user_message_event(FOLLOW_UP_PROMPT),
                build_new_split_answer_event(),
            ],
            EXISTING_SESSION_ID,
        ),
    )

    run_action()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output.json_result["response_text"] == EXPECTED_SPLIT_ANSWER


@set_metadata(integration_config=INTEGRATION_CONFIG, parameters=EXISTING_SESSION_PARAMETERS)
def test_long_session_fails_when_newest_prompt_has_no_answer(
    action_output: MockActionOutput,
    mocker: MockerFixture,
) -> None:
    """Test earlier answers in a long session, including one to the same prompt, are never returned."""
    patch_api(mocker, "test_connectivity")
    patch_api(
        mocker,
        "post_agent_prompt",
        return_value=build_agentic_session(
            [*LONG_HISTORY_EVENTS, build_user_message_event(FOLLOW_UP_PROMPT)],
            EXISTING_SESSION_ID,
        ),
    )

    run_action()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert (
        AGENT_NO_FINAL_RESPONSE_ERROR_MESSAGE.format(session_id=EXISTING_SESSION_ID)
        in action_output.results.output_message
    )


@set_metadata(integration_config=INTEGRATION_CONFIG, parameters=NEW_SESSION_PARAMETERS)
def test_connectivity_failure_uses_spec_message(
    action_output: MockActionOutput,
    mocker: MockerFixture,
) -> None:
    """Test a failed connectivity check fails the action with the credentials message."""
    patch_api(
        mocker,
        "test_connectivity",
        side_effect=GoogleThreatIntelligenceHTTPException(UNAUTHORIZED_ERROR),
    )
    mock_post = patch_api(mocker, "post_agent_prompt")

    run_action()

    mock_post.assert_not_called()
    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
    assert AGENT_CONNECTIVITY_ERROR_MESSAGE in action_output.results.output_message


@set_metadata(integration_config=INTEGRATION_CONFIG, parameters=NEW_SESSION_PARAMETERS)
def test_fails_when_session_id_is_missing(
    action_output: MockActionOutput,
    mocker: MockerFixture,
) -> None:
    """Test the action fails when the API doesn't return a session ID."""
    patch_api(mocker, "test_connectivity")
    patch_api(mocker, "post_agent_prompt", return_value={"data": {}})

    run_action()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert AGENT_MISSING_SESSION_ID_ERROR_MESSAGE in action_output.results.output_message


@pytest.mark.usefixtures("attachments")
@set_metadata(
    integration_config=INTEGRATION_CONFIG,
    parameters={
        **NEW_SESSION_PARAMETERS,
        "Prompt": FILES_PROMPT,
        "File Paths": QUOTED_DUPLICATED_FILE_PATHS,
    },
)
def test_cleans_and_attaches_file_paths(
    action_output: MockActionOutput,
    mocker: MockerFixture,
) -> None:
    """Test quoted and duplicated file paths are cleaned once and attached to the prompt."""
    patch_api(mocker, "test_connectivity")
    mock_post = patch_api(
        mocker,
        "post_agent_prompt",
        return_value=build_agentic_session([build_final_response_event(NEW_ANSWER)], NEW_SESSION_ID),
    )

    run_action()

    mock_post.assert_called_once_with(prompt=FILES_PROMPT, session_id=None, file_paths=ATTACHMENT_PATHS)
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config=INTEGRATION_CONFIG,
    parameters={**NEW_SESSION_PARAMETERS, "Prompt": FILES_PROMPT, "File Paths": MISSING_FILE_PATH},
)
def test_missing_file_path_failure(
    action_output: MockActionOutput,
    mocker: MockerFixture,
) -> None:
    """Test the action fails before submitting when a file doesn't exist."""
    patch_api(mocker, "test_connectivity")
    mock_post = patch_api(mocker, "post_agent_prompt")

    run_action()

    mock_post.assert_not_called()
    assert action_output.results.execution_state == ExecutionState.FAILED
    assert MISSING_FILE_ERROR in action_output.results.output_message


@pytest.mark.usefixtures("attachments")
@set_metadata(
    integration_config=INTEGRATION_CONFIG,
    parameters={**NEW_SESSION_PARAMETERS, "Prompt": FILES_PROMPT, "File Paths": str(ATTACHMENTS_DIR)},
)
def test_directory_path_failure(
    action_output: MockActionOutput,
    mocker: MockerFixture,
) -> None:
    """Test the action fails before submitting when a path is a directory."""
    patch_api(mocker, "test_connectivity")
    mock_post = patch_api(mocker, "post_agent_prompt")

    run_action()

    mock_post.assert_not_called()
    assert action_output.results.execution_state == ExecutionState.FAILED
    assert (
        AGENT_DIRECTORY_PATHS_ERROR_MESSAGE.format(paths=ATTACHMENTS_DIR)
        in action_output.results.output_message
    )


@pytest.mark.usefixtures("attachments")
@set_metadata(
    integration_config=INTEGRATION_CONFIG,
    parameters={**NEW_SESSION_PARAMETERS, "Prompt": FILES_PROMPT, "File Paths": EMPTY_FILE_PATH},
)
def test_empty_file_failure(
    action_output: MockActionOutput,
    mocker: MockerFixture,
) -> None:
    """Test the action fails before submitting when a file is empty."""
    patch_api(mocker, "test_connectivity")
    mock_post = patch_api(mocker, "post_agent_prompt")

    run_action()

    mock_post.assert_not_called()
    assert action_output.results.execution_state == ExecutionState.FAILED
    assert (
        AGENT_EMPTY_FILES_ERROR_MESSAGE.format(paths=EMPTY_FILE_PATH)
        in action_output.results.output_message
    )


@set_metadata(
    integration_config=INTEGRATION_CONFIG,
    parameters={**NEW_SESSION_PARAMETERS, "Delete Session After Completion": True},
)
def test_post_failure_fails_without_deleting_session(
    action_output: MockActionOutput,
    mocker: MockerFixture,
) -> None:
    """Test an API error while posting the prompt fails the action, with no session to delete."""
    patch_api(mocker, "test_connectivity")
    patch_api(
        mocker,
        "post_agent_prompt",
        side_effect=GoogleThreatIntelligenceHTTPException(SERVER_ERROR),
    )
    mock_delete = patch_api(mocker, "delete_agent_session")

    run_action()

    mock_delete.assert_not_called()
    assert action_output.results.execution_state == ExecutionState.FAILED
    assert SERVER_ERROR in action_output.results.output_message


@set_metadata(
    integration_config=INTEGRATION_CONFIG,
    parameters={**NEW_SESSION_PARAMETERS, "Delete Session After Completion": True},
)
def test_delete_network_error_does_not_fail_completed_action(
    action_output: MockActionOutput,
    mocker: MockerFixture,
) -> None:
    """Test a network error while deleting the session keeps the completed result."""
    patch_api(mocker, "test_connectivity")
    patch_api(
        mocker,
        "post_agent_prompt",
        return_value=build_agentic_session([build_final_response_event(NEW_ANSWER)], NEW_SESSION_ID),
    )
    mock_delete = patch_api(
        mocker,
        "delete_agent_session",
        side_effect=requests.exceptions.ConnectionError(),
    )

    run_action()

    mock_delete.assert_called_once_with(NEW_SESSION_ID)
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert action_output.results.json_output.json_result["response_text"] == NEW_ANSWER
