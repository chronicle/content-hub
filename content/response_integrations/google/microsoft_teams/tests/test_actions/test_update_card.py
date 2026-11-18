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

from microsoft_teams.actions import update_card
from microsoft_teams.tests.common import CONFIG_PATH

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput

    from microsoft_teams.tests.core.session import MicrosoftTeamsSession

CARD = {
    "type": "AdaptiveCard",
    "version": "1.5",
    "body": [{"type": "TextBlock", "text": "Updated"}],
}


def _parameters(message_id: str = "m1", card: dict | None = None, **destination: str) -> dict[str, str]:
    return {**destination, "Message ID": message_id, "Card JSON": json.dumps(card or CARD)}


def _requests(script_session: MicrosoftTeamsSession, method: str) -> list:
    return [record.request for record in script_session.request_history if record.request.method.value == method]


class TestUpdateCard:
    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=_parameters(**{"Destination Type": "Chat", "Chat ID": "chat1"}),
    )
    def test_replaces_the_card_of_a_chat_message(
        self, script_session: MicrosoftTeamsSession, action_output: MockActionOutput
    ) -> None:
        update_card.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "Successfully updated the card of message m1" in action_output.results.output_message
        assert action_output.results.json_output.json_result == {"id": "m1", "status": "updated"}
        assert [record.request.method.value for record in script_session.request_history][-2:] == ["GET", "PATCH"]
        (patch,) = _requests(script_session, "PATCH")
        assert patch.url.path == "/v1.0/chats/chat1/messages/m1"
        attachment = patch.kwargs["json"]["attachments"][0]
        assert attachment["id"] == "att1"
        assert json.loads(attachment["content"])["body"] == CARD["body"]

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=_parameters(**{"Destination Type": "Channel", "Team Name": "test", "Channel Name": "c1"}),
    )
    def test_replaces_the_card_of_a_channel_message(
        self, script_session: MicrosoftTeamsSession, action_output: MockActionOutput
    ) -> None:
        update_card.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "channel c1 in team test" in action_output.results.output_message
        (patch,) = _requests(script_session, "PATCH")
        assert patch.url.path == "/v1.0/teams/id_test_team/channels/id_test_channel/messages/m1"

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=_parameters("m403", **{"Destination Type": "Chat", "Chat ID": "chat1"}),
    )
    def test_uses_a_new_attachment_id_when_the_message_cannot_be_read(
        self, script_session: MicrosoftTeamsSession, action_output: MockActionOutput
    ) -> None:
        update_card.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        (patch,) = _requests(script_session, "PATCH")
        assert patch.kwargs["json"]["attachments"][0]["id"] != "att1"

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=_parameters("m404", **{"Destination Type": "Chat", "Chat ID": "chat1"}),
    )
    def test_reports_a_message_that_was_not_found(self, action_output: MockActionOutput) -> None:
        update_card.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "message m404 in chat with ID chat1 was not found" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=_parameters("m2", **{"Destination Type": "Chat", "Chat ID": "chat1"}),
    )
    def test_reports_a_message_without_a_card(
        self, script_session: MicrosoftTeamsSession, action_output: MockActionOutput
    ) -> None:
        update_card.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "does not contain an Adaptive Card" in action_output.results.output_message
        assert not _requests(script_session, "PATCH")

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=_parameters(
            card={**CARD, "actions": [{"type": "Action.Execute"}]},
            **{"Destination Type": "Chat", "Chat ID": "chat1"},
        ),
    )
    def test_rejects_an_unsupported_action_without_calling_the_api(
        self, script_session: MicrosoftTeamsSession, action_output: MockActionOutput
    ) -> None:
        update_card.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Action.Execute" in action_output.results.output_message
        assert not script_session.request_history

    @pytest.mark.parametrize(
        ("destination", "expected"),
        [
            ({"Destination Type": "Channel", "Team Name": "test"}, "Channel Name"),
            ({"Destination Type": "Chat"}, "Chat ID"),
        ],
        ids=["missing_channel", "missing_chat_id"],
    )
    def test_reports_missing_destination_parameters(
        self, action_output: MockActionOutput, destination: dict[str, str], expected: str
    ) -> None:
        @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=_parameters(**destination))
        def run() -> None:
            update_card.main()

        run()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert expected in action_output.results.output_message
