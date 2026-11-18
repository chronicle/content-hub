# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import importlib
import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from microsoft_teams.core.MicrosoftExceptions import MicrosoftTeamsChannelNotFoundError
from microsoft_teams.core.MicrosoftManager import MicrosoftTeamsManager
from microsoft_teams.tests.conftest import CONFIG
from microsoft_teams.tests.test_actions.utils import run_action_with_parameters

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from microsoft_teams.tests.core.session import MicrosoftTeamsSession

CARD = {
    "type": "AdaptiveCard",
    "version": "1.5",
    "body": [{"type": "TextBlock", "text": "Hello"}],
    "actions": [{"type": "Action.OpenUrl", "title": "Open", "url": "https://example.com"}],
}


pytestmark = pytest.mark.usefixtures("_resolve_names")


def _run(mocker: MockerFixture, **parameters: str) -> MagicMock:
    return run_action_with_parameters(mocker, "SendCardMessage", parameters, CONFIG)


@pytest.fixture
def _resolve_names(mocker: MockerFixture) -> None:
    mocker.patch.object(MicrosoftTeamsManager, "get_team_id", return_value="t1")
    mocker.patch.object(MicrosoftTeamsManager, "get_channel_id", return_value="c1")


def _end_args(siemplify: MagicMock) -> tuple:
    siemplify.end.assert_called_once()
    return siemplify.end.call_args.args


def test_send_card_to_channel_success(mocker: MockerFixture, script_session: MicrosoftTeamsSession) -> None:
    siemplify = _run(
        mocker,
        **{
            "Destination Type": "Channel",
            "Team Name": "Team",
            "Channel Name": "Channel",
            "Card JSON": json.dumps(CARD),
        },
    )

    output_message, result_value, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_COMPLETED
    assert result_value is True
    assert "Successfully sent a card to channel Channel in team Team" in output_message
    siemplify.result.add_result_json.assert_called_once()
    assert siemplify.result.add_result_json.call_args.args[0]["id"] == "card_msg_1"
    post_requests = [
        record.request
        for record in script_session.request_history
        if record.request.url.path.endswith("/channels/c1/messages")
    ]
    assert len(post_requests) == 1


def test_send_card_to_chat_success(mocker: MockerFixture) -> None:
    siemplify = _run(
        mocker,
        **{
            "Destination Type": "Chat",
            "Chat ID": "chat1",
            "Card JSON": json.dumps(CARD),
        },
    )

    output_message, result_value, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_COMPLETED
    assert result_value is True
    assert "chat with ID chat1" in output_message


def test_send_card_accepts_bot_framework_envelope(mocker: MockerFixture) -> None:
    envelope = {
        "type": "message",
        "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "content": CARD}],
    }

    siemplify = _run(
        mocker,
        **{"Destination Type": "Chat", "Chat ID": "chat1", "Card JSON": json.dumps(envelope)},
    )

    _, result_value, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_COMPLETED
    assert result_value is True


def test_send_card_includes_warnings_in_output(mocker: MockerFixture) -> None:
    card = {**CARD, "version": "1.6"}

    siemplify = _run(
        mocker,
        **{"Destination Type": "Chat", "Chat ID": "chat1", "Card JSON": json.dumps(card)},
    )

    output_message, _, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_COMPLETED
    assert "Warnings:" in output_message
    assert "higher than 1.5" in output_message


def test_send_card_rejects_submit_without_calling_the_api(
    mocker: MockerFixture, script_session: MicrosoftTeamsSession
) -> None:
    card = {**CARD, "actions": [{"type": "Action.Submit", "title": "Go"}]}

    siemplify = _run(
        mocker,
        **{"Destination Type": "Chat", "Chat ID": "chat1", "Card JSON": json.dumps(card)},
    )

    output_message, result_value, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_FAILED
    assert result_value is False
    assert "Action.Submit" in output_message
    assert not script_session.request_history


def test_send_card_invalid_json(mocker: MockerFixture) -> None:
    siemplify = _run(
        mocker,
        **{"Destination Type": "Chat", "Chat ID": "chat1", "Card JSON": '{"type": '},
    )

    output_message, _, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_FAILED
    assert "not valid JSON" in output_message


@pytest.mark.parametrize(
    ("parameters", "expected"),
    [
        ({"Destination Type": "Channel", "Team Name": "Team"}, "Channel Name"),
        ({"Destination Type": "Chat"}, "Chat ID"),
        ({"Destination Type": "Other", "Chat ID": "chat1"}, "Unsupported"),
    ],
    ids=["missing_channel", "missing_chat_id", "unsupported_destination"],
)
def test_send_card_missing_destination_parameters(mocker: MockerFixture, parameters: dict, expected: str) -> None:
    siemplify = _run(mocker, **parameters, **{"Card JSON": json.dumps(CARD)})

    output_message, result_value, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_FAILED
    assert result_value is False
    assert expected in output_message


def test_send_card_chat_not_found(mocker: MockerFixture) -> None:
    mocker.patch.object(
        MicrosoftTeamsManager,
        "send_card_to_chat",
        side_effect=MicrosoftTeamsChannelNotFoundError("404"),
    )

    siemplify = _run(
        mocker,
        **{"Destination Type": "Chat", "Chat ID": "chat1", "Card JSON": json.dumps(CARD)},
    )

    output_message, _, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_FAILED
    assert "chat with ID chat1 was not found" in output_message


@pytest.mark.parametrize("module_name", ["SendCardMessage", "UpdateCard"])
def test_missing_configuration_returns_a_failed_result(mocker: MockerFixture, module_name: str) -> None:
    """The action must end with a clear message and not raise before `end`."""
    module = importlib.import_module(f"microsoft_teams.actions.{module_name}")
    siemplify = MagicMock()
    siemplify.parameters = {"Destination Type": "Chat", "Chat ID": "chat1", "Card JSON": json.dumps(CARD)}
    siemplify.get_configuration.return_value = {}
    mocker.patch.object(module, "SiemplifyAction", return_value=siemplify)

    module.main()

    output_message, result_value, status = _end_args(siemplify)
    assert status == EXECUTION_STATE_FAILED
    assert result_value is False
    assert "Client ID" in output_message
