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

from microsoft_teams.actions import send_case_card
from microsoft_teams.tests.common import CONFIG_PATH

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from integration_testing.platform.script_output import MockActionOutput
    from pytest_mock import MockerFixture

    from microsoft_teams.tests.core.session import MicrosoftTeamsSession

DETAILS_PATH = pathlib.Path(__file__).parents[1] / "case_details_example.json"
BUILDER = "microsoft_teams.core.case_card_builder"
CHAT = {"Destination Type": "Chat", "Chat ID": "chat1", "Case ID": "1234"}
CHANNEL = {"Destination Type": "Channel", "Team Name": "test", "Channel Name": "c1", "Case ID": "1234"}


pytestmark = pytest.mark.usefixtures("case_overview")


@pytest.fixture
def case_overview(mocker: MockerFixture) -> MagicMock:
    details = CaseDetails.from_json(json.loads(DETAILS_PATH.read_text(encoding="utf-8")))
    mocker.patch(
        f"{BUILDER}.get_case_wall_records",
        return_value={"wallData": [{"description": "Tag added", "creationTimeUnixTimeInMs": 1}]},
    )
    return mocker.patch(f"{BUILDER}.get_case_overview_details", return_value=details)


def _sent_card(script_session: MicrosoftTeamsSession) -> dict:
    posts = [
        record.request
        for record in script_session.request_history
        if record.request.method.value == "POST" and record.request.url.path.endswith("/messages")
    ]
    assert len(posts) == 1
    return json.loads(posts[0].kwargs["json"]["attachments"][0]["content"])


class TestSendCaseCard:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=CHAT)
    def test_sends_the_case_card_to_a_chat(
        self, script_session: MicrosoftTeamsSession, action_output: MockActionOutput
    ) -> None:
        send_case_card.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "Successfully sent the case card in chat with ID chat1" in action_output.results.output_message
        assert action_output.results.json_output.json_result["id"] == "card_msg_1"
        card = _sent_card(script_session)
        assert card["body"][0]["items"][1]["text"] == "Example case title"
        assert "actions" not in card

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=CHANNEL)
    def test_sends_the_case_card_to_a_channel(
        self, script_session: MicrosoftTeamsSession, action_output: MockActionOutput
    ) -> None:
        send_case_card.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "channel c1 in team test" in action_output.results.output_message
        assert _sent_card(script_session)["type"] == "AdaptiveCard"

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters={**CHAT, "Case ID": "999"})
    def test_uses_the_case_id_parameter(self, case_overview: MagicMock, action_output: MockActionOutput) -> None:
        send_case_card.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert case_overview.call_args.args[1] == "999"

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Destination Type": "Chat", "Chat ID": "chat1"},
    )
    def test_fails_without_a_case_before_calling_the_api(
        self, script_session: MicrosoftTeamsSession, action_output: MockActionOutput
    ) -> None:
        send_case_card.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Case ID" in action_output.results.output_message
        assert not script_session.request_history

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=CHAT)
    def test_leaves_out_the_activity_when_the_case_wall_is_unavailable(
        self, mocker: MockerFixture, script_session: MicrosoftTeamsSession, action_output: MockActionOutput
    ) -> None:
        mocker.patch(f"{BUILDER}.get_case_wall_records", side_effect=RuntimeError("wall down"))

        send_case_card.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "case wall is unavailable" in action_output.results.output_message
        assert "Recent activity" not in json.dumps(_sent_card(script_session))

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=CHAT)
    def test_reports_a_case_lookup_failure(self, mocker: MockerFixture, action_output: MockActionOutput) -> None:
        mocker.patch(f"{BUILDER}.get_case_overview_details", side_effect=RuntimeError("case not found"))

        send_case_card.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "case not found" in action_output.results.output_message

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
        @set_metadata(integration_config_file_path=CONFIG_PATH, parameters={**destination, "Case ID": "1234"})
        def run() -> None:
            send_case_card.main()

        run()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert expected in action_output.results.output_message
