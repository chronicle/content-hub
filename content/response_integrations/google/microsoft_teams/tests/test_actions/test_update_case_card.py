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
    mocker.patch(f"{BUILDER}.get_case_wall_records", return_value={"wallData": []})
    mocker.patch.object(MicrosoftTeamsManager, "get_team_id", return_value="t1")
    mocker.patch.object(MicrosoftTeamsManager, "get_channel_id", return_value="c1")


def _run(mocker: MockerFixture, attributes: dict | None = None, **parameters: str) -> MagicMock:
    attributes = {"case_id": 1234} | (attributes or {})
    return run_action_with_parameters(mocker, "UpdateCaseCard", parameters, CONFIG, attributes)


def _end_args(siemplify: MagicMock) -> tuple:
    siemplify.end.assert_called_once()
    return siemplify.end.call_args.args


def _patch_requests(script_session: MicrosoftTeamsSession) -> list:
    return [record.request for record in script_session.request_history if record.request.method.value == "PATCH"]


def test_update_case_card_in_chat(mocker: MockerFixture, script_session: MicrosoftTeamsSession) -> None:
    siemplify = _run(mocker, **{"Destination Type": "Chat", "Chat ID": "chat1", "Message ID": "m1"})

    output_message, result_value, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_COMPLETED
    assert result_value is True
    assert "Successfully updated the case card of message m1" in output_message
    siemplify.result.add_result_json.assert_called_once_with({"id": "m1", "status": "updated"})
    patches = _patch_requests(script_session)
    assert len(patches) == 1
    payload = patches[0].kwargs["json"]
    assert payload["attachments"][0]["id"] == "att1"
    card = json.loads(payload["attachments"][0]["content"])
    assert card["body"][0]["items"][1]["text"] == "Example case title"


def test_update_case_card_in_channel(mocker: MockerFixture) -> None:
    siemplify = _run(
        mocker,
        **{"Destination Type": "Channel", "Team Name": "Team", "Channel Name": "Channel", "Message ID": "m1"},
    )

    output_message, result_value, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_COMPLETED
    assert result_value is True
    assert "channel Channel in team Team" in output_message


def test_update_case_card_message_not_found(mocker: MockerFixture) -> None:
    siemplify = _run(mocker, **{"Destination Type": "Chat", "Chat ID": "chat1", "Message ID": "m404"})

    output_message, result_value, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_FAILED
    assert result_value is False
    assert "message m404 in chat with ID chat1 was not found" in output_message


def test_update_case_card_message_without_card(mocker: MockerFixture) -> None:
    siemplify = _run(mocker, **{"Destination Type": "Chat", "Chat ID": "chat1", "Message ID": "m2"})

    output_message, _, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_FAILED
    assert "does not contain an Adaptive Card" in output_message


def test_update_case_card_without_case_fails_before_calling_the_api(
    mocker: MockerFixture, script_session: MicrosoftTeamsSession
) -> None:
    siemplify = _run(mocker, {"case_id": 0}, **{"Destination Type": "Chat", "Chat ID": "chat1", "Message ID": "m1"})

    output_message, _, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_FAILED
    assert "Case ID" in output_message
    assert not script_session.request_history


def test_update_case_card_missing_destination_parameter(mocker: MockerFixture) -> None:
    siemplify = _run(mocker, **{"Destination Type": "Channel", "Team Name": "Team", "Message ID": "m1"})

    output_message, _, status = _end_args(siemplify)

    assert status == EXECUTION_STATE_FAILED
    assert "Channel Name" in output_message
