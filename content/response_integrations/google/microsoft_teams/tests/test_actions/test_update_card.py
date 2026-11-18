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

import json
from typing import TYPE_CHECKING

import pytest
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from microsoft_teams.core.MicrosoftManager import MicrosoftTeamsManager
from microsoft_teams.tests.conftest import CONFIG
from microsoft_teams.tests.test_actions.utils import run_action_with_parameters

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture

    from microsoft_teams.tests.core.session import MicrosoftTeamsSession

CARD = {
    "type": "AdaptiveCard",
    "version": "1.5",
    "body": [{"type": "TextBlock", "text": "Updated"}],
}


pytestmark = pytest.mark.usefixtures("_resolve_names")


def _run(mocker: MockerFixture, **parameters: str) -> MagicMock:
    return run_action_with_parameters(mocker, "UpdateCard", parameters, CONFIG)


@pytest.fixture
def _resolve_names(mocker: MockerFixture) -> None:
    mocker.patch.object(MicrosoftTeamsManager, "get_team_id", return_value="t1")
    mocker.patch.object(MicrosoftTeamsManager, "get_channel_id", return_value="c1")


def _end_args(siemplify: MagicMock) -> tuple:
    siemplify.end.assert_called_once()
    return siemplify.end.call_args.args


def test_update_card_in_channel_success(mocker: MockerFixture, script_session: MicrosoftTeamsSession) -> None:
    siemplify = _run(
        mocker,
        **{
            "Destination Type": "Channel",
            "Team Name": "Team",
            "Channel Name": "Channel",
            "Message ID": "m1",
            "Card JSON": json.dumps(CARD),
        },
    )

    output_message, result_value, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_COMPLETED
    assert result_value is True
    assert "Successfully updated the card of message m1" in output_message
    siemplify.result.add_result_json.assert_called_once_with({"id": "m1", "status": "updated"})
    methods = [record.request.method.value for record in script_session.request_history]
    assert methods[-2:] == ["GET", "PATCH"]


def test_update_card_in_chat_success(mocker: MockerFixture) -> None:
    siemplify = _run(
        mocker,
        **{
            "Destination Type": "Chat",
            "Chat ID": "chat1",
            "Message ID": "m1",
            "Card JSON": json.dumps(CARD),
        },
    )

    output_message, result_value, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_COMPLETED
    assert result_value is True
    assert "chat with ID chat1" in output_message


def test_update_card_message_not_found(mocker: MockerFixture) -> None:
    siemplify = _run(
        mocker,
        **{
            "Destination Type": "Chat",
            "Chat ID": "chat1",
            "Message ID": "m404",
            "Card JSON": json.dumps(CARD),
        },
    )

    output_message, result_value, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_FAILED
    assert result_value is False
    assert "message m404 in chat with ID chat1 was not found" in output_message


def test_update_card_message_without_card(mocker: MockerFixture) -> None:
    siemplify = _run(
        mocker,
        **{
            "Destination Type": "Chat",
            "Chat ID": "chat1",
            "Message ID": "m2",
            "Card JSON": json.dumps(CARD),
        },
    )

    output_message, _, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_FAILED
    assert "does not contain an Adaptive Card" in output_message


def test_update_card_rejects_submit_without_calling_the_api(
    mocker: MockerFixture, script_session: MicrosoftTeamsSession
) -> None:
    card = {**CARD, "actions": [{"type": "Action.Execute"}]}

    siemplify = _run(
        mocker,
        **{
            "Destination Type": "Chat",
            "Chat ID": "chat1",
            "Message ID": "m1",
            "Card JSON": json.dumps(card),
        },
    )

    output_message, _, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_FAILED
    assert "Action.Execute" in output_message
    assert not script_session.request_history


def test_update_card_missing_destination_parameter(mocker: MockerFixture) -> None:
    siemplify = _run(
        mocker,
        **{
            "Destination Type": "Channel",
            "Team Name": "Team",
            "Message ID": "m1",
            "Card JSON": json.dumps(CARD),
        },
    )

    output_message, _, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_FAILED
    assert "Channel Name" in output_message
