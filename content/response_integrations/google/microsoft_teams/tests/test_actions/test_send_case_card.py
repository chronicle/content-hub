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
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon.data_models import CaseDetails

from microsoft_teams.core.MicrosoftManager import MicrosoftTeamsManager
from microsoft_teams.tests.conftest import CONFIG
from microsoft_teams.tests.test_actions.utils import run_action_with_parameters

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture

    from microsoft_teams.tests.core.session import MicrosoftTeamsSession

DETAILS_PATH = pathlib.Path(__file__).parents[1] / "case_details_example.json"
BUILDER = "microsoft_teams.core.CaseCardBuilder"


@pytest.fixture(autouse=True)
def _case_and_names(mocker: MockerFixture) -> None:
    details = CaseDetails.from_json(json.loads(DETAILS_PATH.read_text(encoding="utf-8")))
    mocker.patch(f"{BUILDER}.get_case_overview_details", return_value=details)
    mocker.patch(
        f"{BUILDER}.get_case_wall_records",
        return_value={"wallData": [{"description": "Tag added", "creationTimeUnixTimeInMs": 1}]},
    )
    mocker.patch.object(MicrosoftTeamsManager, "get_team_id", return_value="t1")
    mocker.patch.object(MicrosoftTeamsManager, "get_channel_id", return_value="c1")


def _run(mocker: MockerFixture, attributes: dict | None = None, **parameters: str) -> MagicMock:
    attributes = {"case_id": 1234} | (attributes or {})
    return run_action_with_parameters(mocker, "SendCaseCard", parameters, CONFIG, attributes)


def _end_args(siemplify: MagicMock) -> tuple:
    siemplify.end.assert_called_once()
    return siemplify.end.call_args.args


def _sent_card(script_session: MicrosoftTeamsSession) -> dict:
    posts = [
        record.request
        for record in script_session.request_history
        if record.request.method.value == "POST" and record.request.url.path.endswith("/messages")
    ]
    assert len(posts) == 1
    attachment = posts[0].kwargs["json"]["attachments"][0]
    return json.loads(attachment["content"])


def test_send_case_card_to_chat(mocker: MockerFixture, script_session: MicrosoftTeamsSession) -> None:
    siemplify = _run(mocker, **{"Destination Type": "Chat", "Chat ID": "chat1"})

    output_message, result_value, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_COMPLETED
    assert result_value is True
    assert "Successfully sent the case card in chat with ID chat1" in output_message
    siemplify.result.add_result_json.assert_called_once()
    card = _sent_card(script_session)
    assert card["body"][0]["items"][1]["text"] == "Example case title"
    assert "actions" not in card


def test_send_case_card_to_channel(mocker: MockerFixture) -> None:
    siemplify = _run(mocker, **{"Destination Type": "Channel", "Team Name": "Team", "Channel Name": "Channel"})

    output_message, result_value, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_COMPLETED
    assert result_value is True
    assert "Successfully sent the case card to channel Channel in team Team" in output_message


def test_case_id_parameter_overrides_the_context(mocker: MockerFixture) -> None:
    overview = mocker.patch(f"{BUILDER}.get_case_overview_details", wraps=None)
    overview.return_value = CaseDetails.from_json(json.loads(DETAILS_PATH.read_text(encoding="utf-8")))

    _run(mocker, **{"Destination Type": "Chat", "Chat ID": "chat1", "Case ID": "999"})

    assert overview.call_args.args[1] == 999


def test_no_case_context_and_no_case_id_fails(mocker: MockerFixture, script_session: MicrosoftTeamsSession) -> None:
    siemplify = _run(mocker, {"case_id": 0}, **{"Destination Type": "Chat", "Chat ID": "chat1"})

    output_message, result_value, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_FAILED
    assert result_value is False
    assert "Case ID" in output_message
    assert not script_session.request_history


@pytest.mark.parametrize(
    ("parameters", "expected"),
    [
        ({"Destination Type": "Channel", "Team Name": "Team"}, "Channel Name"),
        ({"Destination Type": "Chat"}, "Chat ID"),
    ],
    ids=["missing_channel", "missing_chat_id"],
)
def test_missing_destination_parameters(mocker: MockerFixture, parameters: dict, expected: str) -> None:
    siemplify = _run(mocker, **parameters)

    output_message, _, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_FAILED
    assert expected in output_message


def test_case_lookup_failure_returns_a_failed_result(mocker: MockerFixture) -> None:
    mocker.patch(f"{BUILDER}.get_case_overview_details", side_effect=RuntimeError("case not found"))

    siemplify = _run(mocker, **{"Destination Type": "Chat", "Chat ID": "chat1"})

    output_message, result_value, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_FAILED
    assert result_value is False
    assert "case not found" in output_message
