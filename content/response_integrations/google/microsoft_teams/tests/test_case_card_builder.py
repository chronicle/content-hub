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
from types import SimpleNamespace

import pytest
from TIPCommon.data_models import CaseDetails

from microsoft_teams.core.CardUtils import validate_card
from microsoft_teams.core.CaseCardBuilder import (
    CaseCardAlert,
    CaseCardData,
    build_case_card,
    build_case_card_for_case,
    case_card_data_from_details,
    escape_text,
    extract_activities,
    resolve_case_id,
)
from microsoft_teams.core.MicrosoftExceptions import MicrosoftTeamsActionError

DETAILS_PATH = pathlib.Path(__file__).parent / "case_details_example.json"


def _details() -> CaseDetails:
    return CaseDetails.from_json(json.loads(DETAILS_PATH.read_text(encoding="utf-8")))


def _texts(node: object) -> list[str]:
    """Collect every string in a card, to search for rendered text."""
    if isinstance(node, dict):
        return [text for value in node.values() for text in _texts(value)]
    if isinstance(node, list):
        return [text for value in node for text in _texts(value)]
    return [node] if isinstance(node, str) else []


def _facts(container: dict) -> dict[str, str]:
    return {fact["title"]: fact["value"] for fact in container["facts"]}


class TestBuildCaseCard:
    def test_card_from_case_details(self) -> None:
        data = case_card_data_from_details(_details(), ["Tag added"])

        card = build_case_card(data)

        header, facts, alert_heading, alert, tags_heading, tags, activity_heading, activity = card["body"]
        assert card["type"] == "AdaptiveCard"
        assert card["msteams"] == {"width": "Full"}
        assert header["style"] == "accent"
        assert "CASE #1234" in header["items"][0]["columns"][0]["items"][0]["text"]
        assert header["items"][0]["columns"][1]["items"][0]["text"] == "INFORMATIONAL"
        assert header["items"][1]["text"] == "Service sweep from 10.0.0.5"
        assert header["items"][2]["text"].startswith("Created {{DATE(2026-10-30T15:29:02Z,LONG)}}")
        assert _facts(facts) == {
            "Stage": "Triage",
            "Status": "Open",
            "Priority": "Informational",
            "Environment": "Default Environment",
        }
        assert alert_heading["text"] == "Alert"
        assert alert["items"][0]["text"] == "NETWORK - POSSIBLE SERVICE SWEEP"
        assert _facts(alert["items"][1]) == {
            "Product": "Acme Sensor",
            "Rule generator": "Service sweep from 10.0.0.5",
            "Events": "1",
        }
        assert tags_heading["text"] == "Tags"
        assert "Sensor" in tags["text"]
        assert activity_heading["text"] == "Recent activity"
        assert activity["text"] == "- Tag added"
        assert "actions" not in card

    def test_card_passes_validation_without_warnings(self) -> None:
        card = build_case_card(case_card_data_from_details(_details(), ["Tag added"]))

        assert validate_card(card) == []

    def test_card_is_json_serializable_and_small(self) -> None:
        card = build_case_card(case_card_data_from_details(_details(), ["Tag added"]))

        assert len(json.dumps(card)) < 5000

    @pytest.mark.parametrize(
        ("priority", "style", "color"),
        [
            (-1, "accent", "Accent"),
            (40, "good", "Good"),
            (60, "warning", "Warning"),
            (80, "attention", "Attention"),
            (100, "attention", "Attention"),
        ],
    )
    def test_priority_sets_header_style(self, priority: int, style: str, color: str) -> None:
        details = _details()
        details.priority = SimpleNamespace(value=priority)

        card = build_case_card(case_card_data_from_details(details))

        header = card["body"][0]
        assert header["style"] == style
        assert header["items"][0]["columns"][1]["items"][0]["color"] == color

    def test_empty_sections_are_left_out(self) -> None:
        data = CaseCardData(case_id=1, title="Title", priority="High")

        card = build_case_card(data)

        assert [block["type"] for block in card["body"]] == ["Container", "FactSet"]

    def test_alerts_are_capped(self) -> None:
        alerts = [CaseCardAlert(name=f"Alert {index}") for index in range(5)]
        data = CaseCardData(case_id=1, title="Title", priority="High", alerts=alerts)

        card = build_case_card(data)

        texts = _texts(card)
        assert "Alerts (5)" in texts
        assert "Alert 2" in texts
        assert "Alert 3" not in texts
        assert "+2 more" in texts

    def test_missing_created_time_is_left_out(self) -> None:
        data = CaseCardData(case_id=1, title="Title", priority="High")

        header = build_case_card(data)["body"][0]

        assert len(header["items"]) == 2


class TestEscapeText:
    def test_markdown_links_are_neutralized(self) -> None:
        escaped = escape_text("[Click here](http://evil.example)")

        assert "[" not in escaped.replace("\\[", "")
        assert escaped == "\\[Click here\\](http://evil.example)"

    def test_emphasis_and_html_are_escaped(self) -> None:
        assert escape_text("*bold* _it_ `code` <b>") == "\\*bold\\* \\_it\\_ \\`code\\` \\<b\\>"

    def test_teams_date_functions_are_broken_up(self) -> None:
        escaped = escape_text("{{DATE(2026-01-01T00:00:00Z,LONG)}}")

        assert "{{" not in escaped

    def test_newlines_are_collapsed_and_long_text_is_truncated(self) -> None:
        assert escape_text("a\n\nb   c") == "a b c"
        assert escape_text("x" * 500, max_length=20) == "x" * 17 + "..."

    def test_hostile_case_data_cannot_inject_card_content(self) -> None:
        data = CaseCardData(
            case_id=1,
            title="[phish](http://evil.example) {{TIME(2026-01-01T00:00:00Z)}}",
            priority="High",
            tags=["*x*"],
            activities=["[a](http://evil.example)"],
        )

        card_text = " ".join(_texts(build_case_card(data)))

        assert "](" not in card_text.replace("\\](", "")
        assert "{{TIME" not in card_text


class TestExtractActivities:
    def test_legacy_wall_data_newest_first_and_empty_values_skipped(self) -> None:
        records = {
            "wallData": [
                {"description": "old", "creationTimeUnixTimeInMs": 1},
                {"description": "None", "creationTimeUnixTimeInMs": 5},
                {"description": "new", "creationTimeUnixTimeInMs": 3},
            ]
        }

        assert extract_activities(records) == ["new", "old"]

    def test_one_platform_records(self) -> None:
        records = {
            "caseWallRecords": [
                {
                    "activityDataJson": json.dumps({"activityDescription": "Case assigned"}),
                    "createTime": "2026-10-30T15:30:00Z",
                },
                {"activityDataJson": json.dumps({"comment": "A comment"}), "createTime": "2026-10-30T15:31:00Z"},
            ]
        }

        assert extract_activities(records) == ["A comment", "Case assigned"]

    def test_limit_and_unexpected_shapes(self) -> None:
        records = [{"description": str(index)} for index in range(10)]

        assert len(extract_activities(records, limit=2)) == 2
        assert extract_activities(None) == []
        assert extract_activities({"unknown": 1}) == []
        assert extract_activities([{"activityDataJson": "not json"}]) == []


class TestResolveCaseId:
    def test_parameter_wins_over_context(self) -> None:
        assert resolve_case_id(SimpleNamespace(case_id=5), 1234) == 1234

    def test_context_case_is_used_by_default(self) -> None:
        assert resolve_case_id(SimpleNamespace(case_id="5"), None) == "5"

    @pytest.mark.parametrize("context_id", [None, 0, "0", "-1"])
    def test_no_case_raises(self, context_id: object) -> None:
        with pytest.raises(MicrosoftTeamsActionError, match="Case ID"):
            resolve_case_id(SimpleNamespace(case_id=context_id), None)


class TestBuildCaseCardForCase:
    def test_builds_card_and_collects_no_warnings(self, mocker: pytest.MockFixture) -> None:
        mocker.patch("microsoft_teams.core.CaseCardBuilder.get_case_overview_details", return_value=_details())
        mocker.patch(
            "microsoft_teams.core.CaseCardBuilder.get_case_wall_records",
            return_value={"wallData": [{"description": "Tag added", "creationTimeUnixTimeInMs": 1}]},
        )
        siemplify = SimpleNamespace()

        card, warnings = build_case_card_for_case(siemplify, 1234)

        assert warnings == []
        assert "- Tag added" in _texts(card)

    def test_wall_failure_only_leaves_out_the_activity(self, mocker: pytest.MockFixture) -> None:
        mocker.patch("microsoft_teams.core.CaseCardBuilder.get_case_overview_details", return_value=_details())
        mocker.patch("microsoft_teams.core.CaseCardBuilder.get_case_wall_records", side_effect=RuntimeError("boom"))
        siemplify = SimpleNamespace()

        card, warnings = build_case_card_for_case(siemplify, 1234)

        assert any("case wall is unavailable" in warning for warning in warnings)
        assert "Recent activity" not in _texts(card)
