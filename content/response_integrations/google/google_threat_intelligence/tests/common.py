from __future__ import annotations
from integration_testing.common import get_def_file_content

import json
import pathlib

from TIPCommon.types import SingleJson

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent


def get_json_file_content(json_file_path: str | pathlib.Path | None) -> SingleJson:
    """Get the content of a json file"""

    if isinstance(json_file_path, str):
        json_file_path: pathlib.Path = pathlib.Path(json_file_path)

    return json.loads(json_file_path.read_text(encoding="utf-8"))


AGENT_SESSION_TITLE: str = "Threat Investigation"
TABLE_WIDGET: SingleJson = {"table_widget": {"rows": []}}
MITRE_TREE_WIDGET: SingleJson = {"widget_type": "MITRE_TREE", "mitre_tree_widget": {"tree": {"tactics": []}}}
HISTORY_PROMPT_TEMPLATE: str = "Earlier question {number}"
HISTORY_ANSWER_TEMPLATE: str = "Earlier answer {number}"
HISTORY_SECTION_TEMPLATE: str = "#### Earlier section {number}"


def build_user_message_event(text: str) -> SingleJson:
    """Build a user message event of an agentic session."""
    return {
        "message_type": "USER_MESSAGE",
        "user_message": {"widgets": [{"markdown_text_widget": {"text": text}}]},
    }


def build_agent_thought_event() -> SingleJson:
    """Build an agent thought event of an agentic session."""
    return {"message_type": "AGENT_THOUGHT", "agent_thought": {"text": "Reviewing threat intelligence."}}


def build_final_response_event(*texts: str) -> SingleJson:
    """Build an agent final response event with a markdown widget per text, or a table widget."""
    widgets = [{"markdown_text_widget": {"text": text}} for text in texts] or [TABLE_WIDGET]

    return {
        "message_type": "AGENT_FINAL_RESPONSE",
        "agent_final_response": {"widgets": widgets},
    }


def build_split_final_response_event(*texts: str) -> SingleJson:
    """Build a final response with a MITRE tree widget after each markdown text, as the agent sends it."""
    final_response = build_final_response_event(*texts)
    widgets = final_response["agent_final_response"]["widgets"]
    final_response["agent_final_response"]["widgets"] = [
        item for widget in widgets for item in (widget, MITRE_TREE_WIDGET)
    ]

    return final_response


def build_conversation_history(turns: int) -> list[SingleJson]:
    """Build the events of several earlier prompts, each with a thought and a split final answer."""
    events: list[SingleJson] = []
    for number in range(1, turns + 1):
        events.extend(
            [
                build_user_message_event(HISTORY_PROMPT_TEMPLATE.format(number=number)),
                build_agent_thought_event(),
                build_split_final_response_event(
                    HISTORY_ANSWER_TEMPLATE.format(number=number),
                    HISTORY_SECTION_TEMPLATE.format(number=number),
                ),
            ]
        )

    return events


def build_agentic_session(events: list[SingleJson], session_id: str) -> SingleJson:
    """Build an agentic session payload."""
    return {
        "data": {
            "id": session_id,
            "type": "agentic_session",
            "attributes": {"title": AGENT_SESSION_TITLE, "events": events},
        }
    }
CONFIG: dict = get_def_file_content(CONFIG_PATH) if CONFIG_PATH.exists() else {}
