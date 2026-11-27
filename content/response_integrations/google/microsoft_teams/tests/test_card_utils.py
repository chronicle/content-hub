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

import copy
import json
import re

import pytest

from microsoft_teams.core.card_utils import (
    build_card_attachment,
    build_card_message_payload,
    find_card_attachment_id,
    format_warnings,
    parse_card,
    validate_card,
    validate_destination,
)
from microsoft_teams.core.MicrosoftConstants import ADAPTIVE_CARD_CONTENT_TYPE
from microsoft_teams.core.MicrosoftExceptions import (
    MicrosoftTeamsActionError,
    MicrosoftTeamsCardError,
)

BARE_CARD = {
    "type": "AdaptiveCard",
    "version": "1.5",
    "body": [{"type": "TextBlock", "text": "Hello"}],
    "actions": [{"type": "Action.OpenUrl", "title": "Open", "url": "https://example.com"}],
}


def _envelope(content: object) -> dict:
    return {
        "type": "message",
        "attachments": [{"contentType": ADAPTIVE_CARD_CONTENT_TYPE, "content": content}],
    }


def _card_with(**overrides: object) -> dict:
    card = copy.deepcopy(BARE_CARD)
    card.update(overrides)
    return card


class TestParseCard:
    def test_bare_card_from_string(self) -> None:
        card = parse_card(json.dumps(BARE_CARD))

        assert card["body"] == BARE_CARD["body"]

    def test_fills_missing_schema_and_version(self) -> None:
        card = parse_card({"type": "AdaptiveCard", "body": []})

        assert card["$schema"] == "http://adaptivecards.io/schemas/adaptive-card.json"
        assert card["version"] == "1.5"

    def test_does_not_override_existing_version(self) -> None:
        assert parse_card(_card_with(version="1.3"))["version"] == "1.3"

    def test_envelope_with_dict_content(self) -> None:
        card = parse_card(json.dumps(_envelope(BARE_CARD)))

        assert card["type"] == "AdaptiveCard"
        assert card["actions"] == BARE_CARD["actions"]

    def test_envelope_with_string_content(self) -> None:
        card = parse_card(json.dumps(_envelope(json.dumps(BARE_CARD))))

        assert card["body"] == BARE_CARD["body"]

    def test_envelope_with_extra_attachments_warns(self) -> None:
        envelope = _envelope(BARE_CARD)
        envelope["attachments"].append({"contentType": "text/plain"})
        warnings: list[str] = []

        parse_card(envelope, warnings)

        assert any("multiple attachments" in warning for warning in warnings)

    def test_envelope_without_adaptive_attachment(self) -> None:
        envelope = {"type": "message", "attachments": [{"contentType": "x"}]}

        with pytest.raises(MicrosoftTeamsCardError, match="does not contain"):
            parse_card(envelope)

    def test_invalid_json_reports_location(self) -> None:
        with pytest.raises(MicrosoftTeamsCardError, match=r"line 2, column"):
            parse_card('{"type": "AdaptiveCard",\n "body": [}')

    def test_wrong_type(self) -> None:
        with pytest.raises(MicrosoftTeamsCardError, match="'type' must be"):
            parse_card({"type": "HeroCard"})

    def test_non_object(self) -> None:
        with pytest.raises(MicrosoftTeamsCardError, match="JSON object"):
            parse_card("[1, 2]")


class TestValidateCard:
    def test_valid_card_has_no_warnings(self) -> None:
        assert validate_card(BARE_CARD) == []

    @pytest.mark.parametrize(
        "card",
        [
            _card_with(actions=[{"type": "Action.Submit", "title": "Go"}]),
            _card_with(actions=[{"type": "Action.Execute", "verb": "go"}]),
            _card_with(
                body=[
                    {
                        "type": "Container",
                        "selectAction": {"type": "Action.Submit"},
                        "items": [],
                    }
                ]
            ),
            _card_with(
                actions=[
                    {
                        "type": "Action.ShowCard",
                        "card": {
                            "type": "AdaptiveCard",
                            "actions": [{"type": "Action.Submit"}],
                        },
                    }
                ]
            ),
            _card_with(
                body=[
                    {
                        "type": "Table",
                        "rows": [
                            {
                                "cells": [
                                    {
                                        "items": [
                                            {
                                                "type": "ActionSet",
                                                "actions": [{"type": "Action.Execute"}],
                                            }
                                        ]
                                    }
                                ]
                            }
                        ],
                    }
                ]
            ),
        ],
        ids=["submit", "execute", "select_action", "show_card", "table_cell"],
    )
    def test_unsupported_actions_are_rejected(self, card: dict) -> None:
        with pytest.raises(MicrosoftTeamsCardError, match=r"Action\."):
            validate_card(card)

    def test_error_reports_location(self) -> None:
        card = _card_with(actions=[{"type": "Action.Submit"}])

        with pytest.raises(MicrosoftTeamsCardError, match=re.escape("card.actions[0]")):
            validate_card(card)

    @pytest.mark.parametrize(
        "url",
        ["javascript:alert(1)", "data:text/html,x", "file:///etc/passwd", "VBScript:x"],
    )
    def test_unsafe_open_url_schemes_are_rejected(self, url: str) -> None:
        card = _card_with(actions=[{"type": "Action.OpenUrl", "url": url}])

        with pytest.raises(MicrosoftTeamsCardError, match="unsafe URL"):
            validate_card(card)

    def test_http_open_url_warns(self) -> None:
        card = _card_with(actions=[{"type": "Action.OpenUrl", "url": "http://example.com"}])

        assert any("not https" in warning for warning in validate_card(card))

    def test_unresolved_placeholder_url_warns(self) -> None:
        card = _card_with(actions=[{"type": "Action.OpenUrl", "url": "[Event.url]"}])

        assert any("not https" in warning for warning in validate_card(card))

    def test_unknown_action_warns(self) -> None:
        card = _card_with(actions=[{"type": "Action.ToggleVisibility", "targetElements": []}])

        warnings = validate_card(card)

        assert any("Action.ToggleVisibility" in warning for warning in warnings)

    def test_input_warns(self) -> None:
        card = _card_with(body=[{"type": "Input.Text", "id": "name"}])

        assert any("input element" in warning for warning in validate_card(card))

    def test_unsafe_image_is_rejected_and_http_image_warns(self) -> None:
        with pytest.raises(MicrosoftTeamsCardError, match="unsafe image"):
            validate_card(_card_with(body=[{"type": "Image", "url": "javascript:x"}]))

        warnings = validate_card(_card_with(body=[{"type": "Image", "url": "http://example.com/a.png"}]))
        assert any("image over http" in warning for warning in warnings)

    def test_null_url_is_not_treated_as_the_text_none(self) -> None:
        card = _card_with(
            body=[{"type": "Image", "url": None}],
            actions=[{"type": "Action.OpenUrl", "title": "Open", "url": None}],
        )

        warnings = validate_card(card)

        assert all("None" not in warning for warning in warnings)
        assert any("not https" in warning for warning in warnings)

    def test_null_version_gives_an_invalid_version_warning_without_none(self) -> None:
        warnings = validate_card(_card_with(version=None))

        assert any("not a valid version" in warning for warning in warnings)
        assert all("'None'" not in warning for warning in warnings)

    def test_data_image_is_allowed(self) -> None:
        card = _card_with(body=[{"type": "Image", "url": "data:image/png;base64,AA"}])

        assert validate_card(card) == []

    def test_newer_version_warns(self) -> None:
        warnings = validate_card(_card_with(version="1.6"))

        assert any("higher than 1.5" in warning for warning in warnings)

    def test_invalid_version_warns(self) -> None:
        warnings = validate_card(_card_with(version="latest"))

        assert any("not a valid version" in warning for warning in warnings)

    def test_oversized_card_warns(self) -> None:
        card = _card_with(body=[{"type": "TextBlock", "text": "x" * 30000}])

        assert any("bytes" in warning for warning in validate_card(card))


class TestBuildCardAttachment:
    def test_attachment_id_matches_and_content_is_string(self) -> None:
        body, attachments = build_card_attachment(BARE_CARD)

        attachment = attachments[0]
        assert body == f'<attachment id="{attachment["id"]}"></attachment>'
        assert attachment["contentType"] == ADAPTIVE_CARD_CONTENT_TYPE
        assert isinstance(attachment["content"], str)
        assert json.loads(attachment["content"]) == BARE_CARD

    def test_reuses_given_attachment_id(self) -> None:
        body, attachments = build_card_attachment(BARE_CARD, "existing")

        assert attachments[0]["id"] == "existing"
        assert "existing" in body

    def test_generated_ids_are_unique(self) -> None:
        first = build_card_attachment(BARE_CARD)[1][0]["id"]
        second = build_card_attachment(BARE_CARD)[1][0]["id"]

        assert first != second

    def test_message_payload_shape(self) -> None:
        payload = build_card_message_payload(BARE_CARD, "abc")

        assert payload["body"] == {
            "contentType": "html",
            "content": '<attachment id="abc"></attachment>',
        }
        assert payload["attachments"][0]["id"] == "abc"


def test_find_card_attachment_id() -> None:
    message = {
        "attachments": [
            {"id": "file1", "contentType": "reference"},
            {"id": "card1", "contentType": ADAPTIVE_CARD_CONTENT_TYPE},
        ]
    }

    assert find_card_attachment_id(message) == "card1"
    assert find_card_attachment_id({"attachments": []}) is None
    assert find_card_attachment_id({"attachments": None}) is None
    assert find_card_attachment_id({}) is None


def test_format_warnings() -> None:
    assert format_warnings([]) == ""
    assert format_warnings(["a", "b"]) == "\nWarnings:\n- a\n- b"


class TestValidateDestination:
    def test_channel_requires_team_and_channel(self) -> None:
        validate_destination("Channel", "team", "channel", "")

        with pytest.raises(MicrosoftTeamsActionError, match="Team Name"):
            validate_destination("Channel", "team", "", "")

    def test_chat_requires_chat_id(self) -> None:
        validate_destination("Chat", "", "", "chat1")

        with pytest.raises(MicrosoftTeamsActionError, match="Chat ID"):
            validate_destination("Chat", "team", "channel", "")

    def test_unsupported_destination(self) -> None:
        with pytest.raises(MicrosoftTeamsActionError, match="Unsupported"):
            validate_destination("Other", "t", "c", "chat")
