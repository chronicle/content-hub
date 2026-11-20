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

"""Build an Adaptive Card that summarizes a Google SecOps case."""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
from typing import TYPE_CHECKING

from TIPCommon.rest.soar_api import get_case_overview_details, get_case_wall_records

from .MicrosoftConstants import (
    ADAPTIVE_CARD_DEFAULT_VERSION,
    ADAPTIVE_CARD_SCHEMA,
    ADAPTIVE_CARD_TYPE,
    CASE_CARD_MAX_ACTIVITIES,
    CASE_CARD_MAX_ACTIVITY_LENGTH,
    CASE_CARD_MAX_ALERTS,
    CASE_CARD_MAX_TAGS,
    CASE_CARD_MAX_TEXT_LENGTH,
    CASE_PRIORITY_LABELS,
    CASE_PRIORITY_STYLES,
    CASE_STATUS_LABELS,
)
from .MicrosoftExceptions import MicrosoftTeamsActionError

if TYPE_CHECKING:
    from soar_sdk.SiemplifyAction import SiemplifyAction
    from TIPCommon.types import SingleJson

ELLIPSIS = "..."
ZERO_WIDTH_SPACE = "\u200b"
MARKDOWN_ESCAPED_CHARS = "\\[]*_`<>"
EMPTY_ACTIVITY_VALUES = {"", "none", "null"}


@dataclasses.dataclass(slots=True)
class CaseCardAlert:
    """The alert fields shown on the card."""

    name: str
    vendor: str | None = None
    product: str | None = None
    rule_generator: str | None = None
    events_count: int | None = None


@dataclasses.dataclass(slots=True)
class CaseCardData:
    """The case fields shown on the card."""

    case_id: int | str
    title: str
    priority: str
    stage: str | None = None
    status: str | None = None
    environment: str | None = None
    created_unix_ms: int | None = None
    tags: list[str] = dataclasses.field(default_factory=list)
    alerts: list[CaseCardAlert] = dataclasses.field(default_factory=list)
    activities: list[str] = dataclasses.field(default_factory=list)


def escape_text(value: object, max_length: int = CASE_CARD_MAX_TEXT_LENGTH) -> str:
    """Make case-derived text safe to show in a card.

    Case data comes from external products, so it must not be able to render
    links, emphasis, or Teams date functions inside the card.

    Args:
        value: The text to escape.
        max_length: The maximum length before the text is truncated.

    Returns:
        The single-line, escaped and truncated text.

    """
    text = " ".join(str(value).split())
    if len(text) > max_length:
        text = text[: max_length - len(ELLIPSIS)] + ELLIPSIS

    escaped = "".join(f"\\{char}" if char in MARKDOWN_ESCAPED_CHARS else char for char in text)
    return escaped.replace("{{", "{" + ZERO_WIDTH_SPACE + "{")


def build_case_card(data: CaseCardData) -> SingleJson:
    """Build the Adaptive Card for a case.

    Args:
        data: The case fields to show.

    Returns:
        The Adaptive Card dictionary.

    """
    style, color = CASE_PRIORITY_STYLES.get(data.priority, CASE_PRIORITY_STYLES["Informational"])
    body: list[SingleJson] = [_build_header(data, style, color), _build_case_facts(data)]
    body.extend(_build_alert_section(data.alerts))
    body.extend(_build_tags_section(data.tags))
    body.extend(_build_activity_section(data.activities))

    card: SingleJson = {
        "$schema": ADAPTIVE_CARD_SCHEMA,
        "type": ADAPTIVE_CARD_TYPE,
        "version": ADAPTIVE_CARD_DEFAULT_VERSION,
        "msteams": {"width": "Full"},
        "body": body,
    }
    return card


def case_card_data_from_details(
    details: object,
    activities: list[str] | None = None,
) -> CaseCardData:
    """Convert TIPCommon case details into the data shown on the card.

    Args:
        details: A `TIPCommon.data_models.CaseDetails` object.
        activities: The recent activity lines to show.

    Returns:
        The card data.

    """
    priority_value = getattr(details.priority, "value", details.priority)
    status_value = getattr(details.status, "value", details.status)
    return CaseCardData(
        case_id=details.id_,
        title=details.name or f"Case {details.id_}",
        priority=CASE_PRIORITY_LABELS.get(priority_value, "Informational"),
        stage=details.stage,
        status=CASE_STATUS_LABELS.get(status_value, str(status_value)),
        environment=details.environment,
        created_unix_ms=details.creation_time_unix_time_ms,
        tags=[_tag_name(tag) for tag in details.tags or []],
        alerts=[
            CaseCardAlert(
                name=alert.name or alert.title or "Alert",
                vendor=alert.device_vendor,
                product=alert.device_product,
                rule_generator=alert.rule_generator,
                events_count=alert.events_count,
            )
            for alert in details.alerts or []
        ],
        activities=activities or [],
    )


def extract_activities(wall_records: object, limit: int = CASE_CARD_MAX_ACTIVITIES) -> list[str]:
    """Extract the most recent activity descriptions from case wall records.

    Both the legacy and the One Platform record shapes are supported.

    Args:
        wall_records: The response of the case wall records API.
        limit: The maximum number of activities to return.

    Returns:
        The activity descriptions, newest first.

    """
    if isinstance(wall_records, dict):
        records = wall_records.get("wallData") or wall_records.get("caseWallRecords") or wall_records.get("items") or []
    else:
        records = wall_records or []

    dated = [(_record_time(record), _record_text(record)) for record in records if isinstance(record, dict)]
    dated = [(time, text) for time, text in dated if text]
    if any(time for time, _ in dated):
        dated.sort(key=lambda item: item[0] or 0, reverse=True)

    return [text for _, text in dated[:limit]]


def resolve_case_id(siemplify: SiemplifyAction, case_id: int | str | None) -> int | str:
    """Return the given case ID or the ID of the case the action runs in.

    Args:
        siemplify: The SOAR SDK object.
        case_id: The optional case ID action parameter.

    Returns:
        The case ID to use.

    Raises:
        MicrosoftTeamsActionError: If there is no case ID to use.

    """
    resolved = case_id or getattr(siemplify, "case_id", None)
    if not resolved or str(resolved) in {"0", "-1"}:
        message = "'Case ID' is required when the action doesn't run in the context of a case."
        raise MicrosoftTeamsActionError(message)

    return resolved


def build_case_card_for_case(siemplify: SiemplifyAction, case_id: int | str) -> tuple[SingleJson, list[str]]:
    """Fetch a case and build its card.

    Args:
        siemplify: The SOAR SDK object.
        case_id: The case ID.

    Returns:
        The Adaptive Card and the non-blocking warnings.

    """
    warnings: list[str] = []
    details = get_case_overview_details(siemplify, case_id)

    activities: list[str] = []
    try:
        activities = extract_activities(get_case_wall_records(siemplify, case_id))
    except Exception as error:  # ruff: ignore[blind-except]
        warnings.append(f"The recent activity was left out because the case wall is unavailable: {error}")

    return build_case_card(case_card_data_from_details(details, activities)), warnings


def _build_header(data: CaseCardData, style: str, color: str) -> SingleJson:
    items: list[SingleJson] = [
        {
            "type": "ColumnSet",
            "columns": [
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": f"GOOGLE SECOPS  |  CASE #{escape_text(data.case_id)}",
                            "size": "Small",
                            "weight": "Bolder",
                            "isSubtle": True,
                        }
                    ],
                },
                {
                    "type": "Column",
                    "width": "auto",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": data.priority.upper(),
                            "size": "Small",
                            "weight": "Bolder",
                            "color": color,
                        }
                    ],
                },
            ],
        },
        {
            "type": "TextBlock",
            "text": escape_text(data.title),
            "size": "Large",
            "weight": "Bolder",
            "wrap": True,
            "spacing": "Small",
        },
    ]
    created = _format_created(data.created_unix_ms)
    if created:
        items.append({"type": "TextBlock", "text": created, "size": "Small", "isSubtle": True, "spacing": "None"})

    return {"type": "Container", "style": style, "bleed": True, "items": items}


def _build_case_facts(data: CaseCardData) -> SingleJson:
    candidates = [
        ("Stage", data.stage),
        ("Status", data.status),
        ("Priority", data.priority),
        ("Environment", data.environment),
    ]
    return {
        "type": "FactSet",
        "spacing": "Medium",
        "facts": [{"title": title, "value": escape_text(value)} for title, value in candidates if value],
    }


def _build_alert_section(alerts: list[CaseCardAlert]) -> list[SingleJson]:
    if not alerts:
        return []

    heading = "Alert" if len(alerts) == 1 else f"Alerts ({len(alerts)})"
    section = [_section_heading(heading)]
    for alert in alerts[:CASE_CARD_MAX_ALERTS]:
        facts = _alert_facts(alert)
        items: list[SingleJson] = [
            {"type": "TextBlock", "text": escape_text(alert.name), "weight": "Bolder", "wrap": True}
        ]
        if facts:
            items.append({"type": "FactSet", "facts": facts})

        section.append({"type": "Container", "style": "emphasis", "spacing": "Small", "items": items})

    hidden = len(alerts) - CASE_CARD_MAX_ALERTS
    if hidden > 0:
        section.append({"type": "TextBlock", "text": f"+{hidden} more", "isSubtle": True, "spacing": "Small"})

    return section


def _alert_facts(alert: CaseCardAlert) -> list[dict[str, str]]:
    product = " ".join(part for part in (alert.vendor, alert.product) if part)
    candidates = [
        ("Product", product),
        ("Rule generator", alert.rule_generator if alert.rule_generator != alert.name else None),
        ("Events", alert.events_count),
    ]
    return [
        {"title": title, "value": escape_text(value)} for title, value in candidates if value is not None and str(value)
    ]


def _build_tags_section(tags: list[str]) -> list[SingleJson]:
    if not tags:
        return []

    shown = [escape_text(tag, max_length=40) for tag in tags[:CASE_CARD_MAX_TAGS]]
    return [_section_heading("Tags"), {"type": "TextBlock", "text": "  |  ".join(shown), "wrap": True}]


def _build_activity_section(activities: list[str]) -> list[SingleJson]:
    if not activities:
        return []

    lines = "\n".join(f"- {escape_text(activity, CASE_CARD_MAX_ACTIVITY_LENGTH)}" for activity in activities)
    return [
        _section_heading("Recent activity"),
        {"type": "TextBlock", "text": lines, "wrap": True, "isSubtle": True},
    ]


def _section_heading(text: str) -> SingleJson:
    return {
        "type": "TextBlock",
        "text": text,
        "weight": "Bolder",
        "size": "Medium",
        "separator": True,
        "spacing": "Medium",
    }


def _format_created(created_unix_ms: int | None) -> str | None:
    if not created_unix_ms:
        return None

    created = dt.datetime.fromtimestamp(int(created_unix_ms) / 1000, dt.UTC)
    iso_time = created.strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"Created {{{{DATE({iso_time},LONG)}}}} {{{{TIME({iso_time})}}}}"


def _tag_name(tag: object) -> str:
    if isinstance(tag, dict):
        return str(tag.get("displayName") or tag.get("tag") or tag.get("name") or "")

    return str(tag)


def _record_time(record: SingleJson) -> int | None:
    value = record.get("creationTimeUnixTimeInMs") or record.get("createTime") or record.get("updateTime")
    if isinstance(value, (int, float)):
        return int(value)

    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            try:
                return int(dt.datetime.fromisoformat(value).timestamp() * 1000)
            except ValueError:
                return None

    return None


def _record_text(record: SingleJson) -> str | None:
    candidates = [record.get("description"), record.get("activityDescription")]
    activity_data = record.get("activityDataJson")
    if isinstance(activity_data, str):
        try:
            activity_data = json.loads(activity_data)
        except ValueError:
            activity_data = None

    if isinstance(activity_data, dict):
        candidates.extend([activity_data.get("activityDescription"), activity_data.get("comment")])

    for candidate in candidates:
        text = str(candidate).strip() if candidate is not None else ""
        if text.lower() not in EMPTY_ACTIVITY_VALUES:
            return text

    return None
