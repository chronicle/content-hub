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
import pathlib
from typing import TYPE_CHECKING

import pytest
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState
from TIPCommon.data_models import CaseDetails

from microsoft_teams.actions import update_case_card
from microsoft_teams.tests.common import CONFIG_PATH

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput
    from pytest_mock import MockerFixture

    from microsoft_teams.tests.core.session import MicrosoftTeamsSession

DETAILS_PATH = pathlib.Path(__file__).parents[1] / "case_details_example.json"
BUILDER = "microsoft_teams.core.case_card_builder"
CHAT = {"Destination Type": "Chat", "Chat ID": "chat1", "Case ID": "1234", "Message ID": "m1"}
CHANNEL = {
    "Destination Type": "Channel",
    "Team Name": "test",
    "Channel Name": "c1",
    "Case ID": "1234",
    "Message ID": "m1",
}


@pytest.fixture(autouse=True)
def case_data(mocker: MockerFixture) -> None:
    details = CaseDetails.from_json(json.loads(DETAILS_PATH.read_text(encoding="utf-8")))
    mocker.patch(f"{BUILDER}.get_case_overview_details", return_value=details)
    mocker.patch(f"{BUILDER}.get_case_wall_records", return_value={"wallData": []})


def _patches(script_session: MicrosoftTeamsSession) -> list:
    return [record.request for record in script_session.request_history if record.request.method.value == "PATCH"]


class TestUpdateCaseCard:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=CHAT)
    def test_refreshes_the_case_card_of_a_chat_message(
        self, script_session: MicrosoftTeamsSession, action_output: MockActionOutput
    ) -> None:
        update_case_card.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "Successfully updated the case card of message m1" in action_output.results.output_message
        assert action_output.results.json_output.json_result == {"id": "m1", "status": "updated"}
        (patch,) = _patches(script_session)
        assert patch.url.path == "/v1.0/chats/chat1/messages/m1"
        attachment = patch.kwargs["json"]["attachments"][0]
        assert attachment["id"] == "att1"
        assert json.loads(attachment["content"])["body"][0]["items"][1]["text"] == "Example case title"

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=CHANNEL)
    def test_refreshes_the_case_card_of_a_channel_message(
        self, script_session: MicrosoftTeamsSession, action_output: MockActionOutput
    ) -> None:
        update_case_card.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "channel c1 in team test" in action_output.results.output_message
        (patch,) = _patches(script_session)
        assert patch.url.path == "/v1.0/teams/id_test_team/channels/id_test_channel/messages/m1"

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters={**CHAT, "Message ID": "m404"})
    def test_reports_a_message_that_was_not_found(self, action_output: MockActionOutput) -> None:
        update_case_card.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "message m404 in chat with ID chat1 was not found" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters={**CHAT, "Message ID": "m2"})
    def test_reports_a_message_without_a_card(
        self, script_session: MicrosoftTeamsSession, action_output: MockActionOutput
    ) -> None:
        update_case_card.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "does not contain an Adaptive Card" in action_output.results.output_message
        assert not _patches(script_session)

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Destination Type": "Chat", "Chat ID": "chat1", "Message ID": "m1"},
    )
    def test_fails_without_a_case_before_calling_the_api(
        self, script_session: MicrosoftTeamsSession, action_output: MockActionOutput
    ) -> None:
        update_case_card.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Case ID" in action_output.results.output_message
        assert not script_session.request_history

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Destination Type": "Channel", "Team Name": "test", "Case ID": "1234", "Message ID": "m1"},
    )
    def test_reports_a_missing_destination_parameter(self, action_output: MockActionOutput) -> None:
        update_case_card.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Channel Name" in action_output.results.output_message
