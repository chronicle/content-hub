from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

import pytest
import requests
from pytest_mock import MockerFixture

from TIPCommon.types import SingleJson

from google_threat_intelligence.core.api_data_parser import (
    build_agentic_session_object,
    build_agentic_turn_object,
    get_agentic_session_events,
)
from google_threat_intelligence.core.api_manager import ApiManager
from google_threat_intelligence.core.api_utils import validate_agent_session_response
from google_threat_intelligence.core.constants import (
    AGENT_JSON_ACCEPT_HEADERS,
    AGENT_REQUEST_TIMEOUT_IN_SECONDS,
    AGENT_RESPONSE_TEXT_SEPARATOR,
    AGENT_SESSION_ID_HEADER,
)
from google_threat_intelligence.core.exceptions import (
    GoogleThreatIntelligenceHTTPException,
    GoogleThreatIntelligenceNotFoundException,
)
from google_threat_intelligence.tests.common import (
    AGENT_SESSION_TITLE,
    TABLE_WIDGET,
    build_agent_thought_event,
    build_agentic_session,
    build_conversation_history,
    build_final_response_event,
    build_split_final_response_event,
    build_user_message_event,
)

if TYPE_CHECKING:
    from pytest_mock import MockType

API_ROOT: str = "https://www.virustotal.com"
SESSIONS_URL: str = f"{API_ROOT}/api/v3/agentspace/sessions"
PROMPT: str = "Analyze this file."
SESSION_ID: str = "session-123"
HEADER_SESSION_ID: str = "session-from-header"
UNSAFE_SESSION_ID: str = "../a/b?c"
ENCODED_UNSAFE_SESSION_ID: str = "..%2Fa%2Fb%3Fc"
ATTACHMENT_NAME: str = "sample.txt"
ATTACHMENT_CONTENT: str = "sample content"
QUOTA_STATUS_CODE: int = 429
QUOTA_ERROR_PAYLOAD: SingleJson = {"error": {"code": "QuotaExceededError", "message": "Quota exceeded."}}
NOT_FOUND_STATUS_CODE: int = 404
NOT_FOUND_TEXT: str = "Session not found"
PREVIOUS_ANSWER: str = "The file is a known dropper."
NEW_ANSWER: str = "The file contacts two command and control domains."
PREVIOUS_TURN_EVENTS: list[SingleJson] = [
    build_user_message_event(PROMPT),
    build_final_response_event(PREVIOUS_ANSWER),
]
ANSWER_WITH_TABLE: str = (
    "APT28 and APT29 are Russian state-sponsored groups.\n\n"
    "| Name | Sponsor |\n| :--- | :--- |\n| APT28 | GRU |\n| APT29 | SVR |"
)
ANSWER_SECTION_HEADING: str = "\n\n#### APT29 Tactics & Techniques\n"
HISTORY_TURNS: int = 10


@pytest.fixture(name="session")
def session_fixture(mocker: MockerFixture) -> MockType:
    """Create a mocked requests session whose calls succeed."""
    session = mocker.Mock()
    session.post.return_value.json.return_value = {"data": {"id": SESSION_ID}}

    return session


@pytest.fixture(name="manager")
def manager_fixture(session: MockType, mocker: MockerFixture) -> ApiManager:
    """Create an ApiManager that uses the mocked session."""
    return ApiManager(
        api_root=API_ROOT,
        session=session,
        asm_project_name="",
        logger=mocker.Mock(),
    )


def build_error_response(
    mocker: MockerFixture,
    status_code: int,
    payload: SingleJson | None = None,
    text: str = "",
) -> MockType:
    """Build a failed HTTP response, without a JSON body when no payload is given."""
    response = mocker.Mock()
    response.status_code = status_code
    response.text = text
    response.reason = ""
    response.raise_for_status.side_effect = requests.HTTPError(f"{status_code} Client Error")
    if payload is None:
        response.json.side_effect = ValueError("No JSON body.")
    else:
        response.json.return_value = payload

    return response


def test_post_agent_prompt_sends_message_as_multipart_without_files(
    manager: ApiManager,
    session: MockType,
) -> None:
    """Test the prompt is sent as multipart/form-data without a timeout, since posting is synchronous."""
    manager.post_agent_prompt(prompt=PROMPT)

    session.post.assert_called_once_with(SESSIONS_URL, files=[("message", (None, PROMPT))])


def test_post_agent_prompt_attaches_files_to_existing_session(
    manager: ApiManager,
    session: MockType,
    tmp_path: pathlib.Path,
) -> None:
    """Test attachments are sent as multipart `files` fields to the existing session endpoint."""
    attachment = tmp_path / ATTACHMENT_NAME
    attachment.write_text(ATTACHMENT_CONTENT)

    manager.post_agent_prompt(prompt=PROMPT, session_id=SESSION_ID, file_paths=[str(attachment)])

    assert session.post.call_args.args[0] == f"{SESSIONS_URL}/{SESSION_ID}"
    multipart_fields = session.post.call_args.kwargs["files"]
    assert [(name, value[0]) for name, value in multipart_fields] == [
        ("message", None),
        ("files", ATTACHMENT_NAME),
    ]


def test_post_agent_prompt_uses_session_id_header_when_body_has_no_id(
    manager: ApiManager,
    session: MockType,
) -> None:
    """Test the documented session ID header is used when the response body has no session ID."""
    session.post.return_value.json.return_value = {"data": {"type": "agentic_session"}}
    session.post.return_value.headers = {AGENT_SESSION_ID_HEADER: HEADER_SESSION_ID}

    session_data = manager.post_agent_prompt(prompt=PROMPT)

    assert session_data["data"]["id"] == HEADER_SESSION_ID


def test_delete_session_encodes_session_id_and_accepts_json(manager: ApiManager, session: MockType) -> None:
    """Test the session ID can't change the request path and JSON is requested, as in the spec."""
    manager.delete_agent_session(UNSAFE_SESSION_ID)

    session.delete.assert_called_once_with(
        f"{SESSIONS_URL}/{ENCODED_UNSAFE_SESSION_ID}",
        headers=AGENT_JSON_ACCEPT_HEADERS,
        timeout=AGENT_REQUEST_TIMEOUT_IN_SECONDS,
    )


def test_validate_agent_session_response_uses_spec_error_format(mocker: MockerFixture) -> None:
    """Test HTTP errors use the "Error: {status_code} - {error_details}." format."""
    response = build_error_response(mocker, QUOTA_STATUS_CODE, payload=QUOTA_ERROR_PAYLOAD)

    with pytest.raises(GoogleThreatIntelligenceHTTPException, match=r"^Error: 429 - Quota exceeded\.$"):
        validate_agent_session_response(response)


def test_validate_agent_session_response_keeps_not_found_exception(mocker: MockerFixture) -> None:
    """Test 404 errors keep their exception type and fall back to the response text."""
    response = build_error_response(mocker, NOT_FOUND_STATUS_CODE, text=NOT_FOUND_TEXT)

    with pytest.raises(
        GoogleThreatIntelligenceNotFoundException,
        match=r"^Error: 404 - Session not found\.$",
    ):
        validate_agent_session_response(response)


def test_get_agentic_session_events_keeps_api_order() -> None:
    """Test the session events are returned in the order sent by the API."""
    session_data = build_agentic_session(PREVIOUS_TURN_EVENTS, SESSION_ID)

    assert get_agentic_session_events(session_data) == PREVIOUS_TURN_EVENTS


def test_new_session_is_completed_by_final_response() -> None:
    """Test a new session is completed once the agent's final response is present."""
    session = build_agentic_session_object(build_agentic_session(PREVIOUS_TURN_EVENTS, SESSION_ID))

    assert session.is_completed is True
    assert session.to_json() == {
        "session_id": SESSION_ID,
        "title": AGENT_SESSION_TITLE,
        "response_text": PREVIOUS_ANSWER,
    }


def test_session_without_final_response_is_not_completed() -> None:
    """Test a session isn't completed while the agent hasn't sent its final response."""
    session = build_agentic_session_object(
        build_agentic_session([build_user_message_event(PROMPT)], SESSION_ID)
    )

    assert session.is_completed is False
    assert session.response_text is None


def test_repeated_prompt_ignores_answer_to_earlier_prompt() -> None:
    """Test asking the same prompt again in a session never completes with the earlier answer."""
    waiting_session = build_agentic_session(
        [*PREVIOUS_TURN_EVENTS, build_user_message_event(PROMPT)],
        SESSION_ID,
    )
    answered_session = build_agentic_session(
        [*PREVIOUS_TURN_EVENTS, build_user_message_event(PROMPT), build_final_response_event(NEW_ANSWER)],
        SESSION_ID,
    )

    waiting = build_agentic_session_object(waiting_session, events_offset=len(PREVIOUS_TURN_EVENTS))
    answered = build_agentic_session_object(answered_session, events_offset=len(PREVIOUS_TURN_EVENTS))

    assert waiting.is_completed is False
    assert waiting.response_text is None
    assert answered.is_completed is True
    assert answered.response_text == NEW_ANSWER


def test_response_text_comes_from_last_final_response() -> None:
    """Test only the last final response is used, skipping empty markdown texts and other widgets."""
    first_final_response = build_final_response_event(PREVIOUS_ANSWER)
    first_final_response["agent_final_response"]["widgets"].append(TABLE_WIDGET)
    last_final_response = build_final_response_event(NEW_ANSWER, "")

    session = build_agentic_session_object(
        build_agentic_session(
            [build_user_message_event(PROMPT), first_final_response, last_final_response],
            SESSION_ID,
        )
    )

    assert session.is_completed is True
    assert session.response_text == NEW_ANSWER


def test_response_text_joins_markdown_widgets_split_by_other_widgets() -> None:
    """Test an answer split around MITRE tree widgets keeps all its text, including the table."""
    session = build_agentic_turn_object(
        build_agentic_session(
            [
                build_agent_thought_event(),
                build_split_final_response_event(ANSWER_WITH_TABLE, ANSWER_SECTION_HEADING),
            ],
            SESSION_ID,
        )
    )

    assert session.is_completed is True
    assert session.response_text == (
        f"{ANSWER_WITH_TABLE}{AGENT_RESPONSE_TEXT_SEPARATOR}{ANSWER_SECTION_HEADING.strip()}"
    )


def test_split_answers_of_many_earlier_prompts_are_not_joined() -> None:
    """Test a session with many earlier prompts only joins the text widgets of the newest prompt's answer."""
    history = build_conversation_history(HISTORY_TURNS)
    session_data = build_agentic_session(
        [
            *history,
            build_user_message_event(PROMPT),
            build_split_final_response_event(ANSWER_WITH_TABLE, ANSWER_SECTION_HEADING),
        ],
        SESSION_ID,
    )
    expected_text = f"{ANSWER_WITH_TABLE}{AGENT_RESPONSE_TEXT_SEPARATOR}{ANSWER_SECTION_HEADING.strip()}"

    from_offset = build_agentic_session_object(session_data, events_offset=len(history))
    from_turn = build_agentic_turn_object(session_data)

    assert from_offset.response_text == expected_text
    assert from_turn.response_text == expected_text


def test_final_response_without_markdown_text_is_completed_without_text() -> None:
    """Test a final response that has no markdown widget completes the session without text."""
    session = build_agentic_session_object(
        build_agentic_session([build_user_message_event(PROMPT), build_final_response_event()], SESSION_ID)
    )

    assert session.is_completed is True
    assert session.response_text is None


def test_turn_object_uses_all_events_of_turn_only_reply() -> None:
    """Test a POST reply with only the new prompt's agent events completes with its answer."""
    session = build_agentic_turn_object(
        build_agentic_session(
            [build_agent_thought_event(), build_final_response_event(NEW_ANSWER)],
            SESSION_ID,
        )
    )

    assert session.is_completed is True
    assert session.response_text == NEW_ANSWER


def test_turn_object_ignores_earlier_turns_of_full_session_reply() -> None:
    """Test a POST reply with the whole session only counts events after the last user message."""
    waiting = build_agentic_turn_object(
        build_agentic_session(
            [*PREVIOUS_TURN_EVENTS, build_user_message_event(PROMPT), build_agent_thought_event()],
            SESSION_ID,
        )
    )
    answered = build_agentic_turn_object(
        build_agentic_session(
            [*PREVIOUS_TURN_EVENTS, build_user_message_event(PROMPT), build_final_response_event(NEW_ANSWER)],
            SESSION_ID,
        )
    )

    assert waiting.is_completed is False
    assert waiting.response_text is None
    assert answered.is_completed is True
    assert answered.response_text == NEW_ANSWER
