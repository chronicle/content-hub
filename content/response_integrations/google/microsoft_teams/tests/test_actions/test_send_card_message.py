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
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from microsoft_teams.actions import send_card_message
from microsoft_teams.tests.common import CONFIG_PATH

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput

    from microsoft_teams.tests.core.session import MicrosoftTeamsSession

CARD = {
    "type": "AdaptiveCard",
    "version": "1.5",
    "body": [{"type": "TextBlock", "text": "Hello"}],
    "actions": [{"type": "Action.OpenUrl", "title": "Open", "url": "https://example.com"}],
}
CHAT_PARAMETERS = {"Destination Type": "Chat", "Chat ID": "chat1"}


def _card_parameters(card: dict | str, **parameters: str) -> dict[str, str]:
    return {**parameters, "Card JSON": card if isinstance(card, str) else json.dumps(card)}


def _post_requests(script_session: MicrosoftTeamsSession) -> list:
    return [
        record.request
        for record in script_session.request_history
        if record.request.method.value == "POST" and record.request.url.path.endswith("/messages")
    ]


class TestSendCardMessage:
    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=_card_parameters(CARD, **CHAT_PARAMETERS),
    )
    def test_sends_the_card_to_a_chat(
        self, script_session: MicrosoftTeamsSession, action_output: MockActionOutput
    ) -> None:
        send_card_message.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "Successfully sent a card in chat with ID chat1" in action_output.results.output_message
        assert action_output.results.json_output.json_result["id"] == "card_msg_1"
        (request,) = _post_requests(script_session)
        assert request.url.path == "/v1.0/chats/chat1/messages"
        payload = request.kwargs["json"]
        attachment = payload["attachments"][0]
        assert payload["body"]["content"] == f'<attachment id="{attachment["id"]}"></attachment>'
        assert json.loads(attachment["content"])["body"] == CARD["body"]

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=_card_parameters(CARD, **{"Destination Type": "Channel", "Team Name": "test", "Channel Name": "c1"}),
    )
    def test_sends_the_card_to_a_channel(
        self, script_session: MicrosoftTeamsSession, action_output: MockActionOutput
    ) -> None:
        send_card_message.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "channel c1 in team test" in action_output.results.output_message
        (request,) = _post_requests(script_session)
        assert request.url.path == "/v1.0/teams/id_test_team/channels/id_test_channel/messages"

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=_card_parameters(
            {
                "type": "message",
                "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "content": CARD}],
            },
            **CHAT_PARAMETERS,
        ),
    )
    def test_accepts_a_bot_framework_message(self, action_output: MockActionOutput) -> None:
        send_card_message.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=_card_parameters({**CARD, "version": "1.6"}, **CHAT_PARAMETERS),
    )
    def test_adds_card_warnings_to_the_output_message(self, action_output: MockActionOutput) -> None:
        send_card_message.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Warnings:" in action_output.results.output_message
        assert "higher than 1.5" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=_card_parameters({**CARD, "actions": [{"type": "Action.Submit", "title": "Go"}]}, **CHAT_PARAMETERS),
    )
    def test_rejects_an_unsupported_action_without_calling_the_api(
        self, script_session: MicrosoftTeamsSession, action_output: MockActionOutput
    ) -> None:
        send_card_message.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Action.Submit" in action_output.results.output_message
        assert not script_session.request_history

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=_card_parameters('{"type": ', **CHAT_PARAMETERS),
    )
    def test_reports_invalid_json(self, action_output: MockActionOutput) -> None:
        send_card_message.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "not valid JSON" in action_output.results.output_message

    @pytest.mark.parametrize(
        ("destination_parameters", "expected"),
        [
            ({"Destination Type": "Channel", "Team Name": "test"}, "Channel Name"),
            ({"Destination Type": "Chat"}, "Chat ID"),
            ({"Destination Type": "Other", "Chat ID": "chat1"}, "Unsupported"),
        ],
        ids=["missing_channel", "missing_chat_id", "unsupported_destination"],
    )
    def test_reports_missing_destination_parameters(
        self, action_output: MockActionOutput, destination_parameters: dict[str, str], expected: str
    ) -> None:
        @set_metadata(
            integration_config_file_path=CONFIG_PATH,
            parameters=_card_parameters(CARD, **destination_parameters),
        )
        def run() -> None:
            send_card_message.main()

        run()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert expected in action_output.results.output_message
