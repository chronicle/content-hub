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

"""Helpers for parsing, validating and packaging Adaptive Cards for Teams."""

from __future__ import annotations

import json
import uuid
from typing import Any

from .MicrosoftConstants import (
    ACTION_OPEN_URL,
    ACTION_TYPE_PREFIX,
    ADAPTIVE_CARD_CONTENT_TYPE,
    ADAPTIVE_CARD_DEFAULT_VERSION,
    ADAPTIVE_CARD_MAX_VERSION,
    ADAPTIVE_CARD_SCHEMA,
    ADAPTIVE_CARD_TYPE,
    BOT_FRAMEWORK_MESSAGE_TYPE,
    CARD_SOFT_SIZE_LIMIT_BYTES,
    DESTINATION_CHANNEL,
    DESTINATION_CHAT,
    INPUT_TYPE_PREFIX,
    REJECTED_CARD_ACTIONS,
    UNSAFE_URL_SCHEMES,
)
from .MicrosoftExceptions import MicrosoftTeamsActionError, MicrosoftTeamsCardError

JSON_ERROR_HINT = (
    "If the card contains placeholders, make sure the substituted values do not "
    "contain unescaped quotes or line breaks."
)


def parse_card(raw_card: str | dict[str, Any], warnings: list[str] | None = None) -> dict[str, Any]:
    """Parse card input into an Adaptive Card dictionary.

    Accepts a bare Adaptive Card or a Bot Framework message envelope that wraps
    the card in ``attachments[].content``. A missing ``$schema`` or ``version``
    is filled in with defaults.

    Args:
        raw_card: The card as a JSON string or an already parsed dictionary.
        warnings: Optional list that non-blocking findings are appended to.

    Returns:
        The Adaptive Card as a dictionary.

    Raises:
        MicrosoftTeamsCardError: If the input is not a valid Adaptive Card.

    """
    warnings = warnings if warnings is not None else []
    card = _load_json(raw_card)

    if not isinstance(card, dict):
        message = "The card must be a JSON object."
        raise MicrosoftTeamsCardError(message)

    if card.get("type") == BOT_FRAMEWORK_MESSAGE_TYPE:
        card = _unwrap_envelope(card, warnings)

    if card.get("type") != ADAPTIVE_CARD_TYPE:
        message = f"The card 'type' must be '{ADAPTIVE_CARD_TYPE}', got '{card.get('type')}'."
        raise MicrosoftTeamsCardError(message)

    card.setdefault("$schema", ADAPTIVE_CARD_SCHEMA)
    card.setdefault("version", ADAPTIVE_CARD_DEFAULT_VERSION)
    return card


def validate_card(card: dict[str, Any]) -> list[str]:
    """Validate an Adaptive Card against what Graph can deliver to Teams.

    Args:
        card: The Adaptive Card dictionary.

    Returns:
        A list of non-blocking warnings.

    Raises:
        MicrosoftTeamsCardError: If the card contains blocking problems.

    """
    errors: list[str] = []
    warnings: list[str] = []

    _check_version(card, warnings)
    _walk(card, "card", errors, warnings)

    if errors:
        message = "The card cannot be sent: " + "; ".join(errors) + "."
        raise MicrosoftTeamsCardError(message)

    payload_size = len(json.dumps(build_card_message_payload(card)).encode("utf-8"))
    if payload_size > CARD_SOFT_SIZE_LIMIT_BYTES:
        warnings.append(
            f"The message payload is {payload_size} bytes, above the "
            f"{CARD_SOFT_SIZE_LIMIT_BYTES} bytes Teams commonly allows. "
            "Teams may reject it."
        )

    return warnings


def build_card_attachment(card: dict[str, Any], attachment_id: str | None = None) -> tuple[str, list[dict[str, Any]]]:
    """Build the message body and attachments that carry a card.

    Args:
        card: The Adaptive Card dictionary.
        attachment_id: Optional ID to reuse. A new one is generated otherwise.

    Returns:
        A tuple of the HTML body referencing the attachment and the attachments
        list. The ID is the same in both, as Graph requires.

    """
    attachment_id = attachment_id or uuid.uuid4().hex
    body = f'<attachment id="{attachment_id}"></attachment>'
    attachments = [
        {
            "id": attachment_id,
            "contentType": ADAPTIVE_CARD_CONTENT_TYPE,
            "contentUrl": None,
            "content": json.dumps(card),
        }
    ]
    return body, attachments


def build_card_message_payload(card: dict[str, Any], attachment_id: str | None = None) -> dict[str, Any]:
    """Build the chatMessage request body that carries a card.

    Args:
        card: The Adaptive Card dictionary.
        attachment_id: Optional ID to reuse. A new one is generated otherwise.

    Returns:
        The request body with the HTML body and the card attachment.

    """
    body, attachments = build_card_attachment(card, attachment_id)
    return {
        "body": {"contentType": "html", "content": body},
        "attachments": attachments,
    }


def validate_destination(destination: str, team_name: str, channel_name: str, chat_id: str) -> None:
    """Validate the parameters required by the selected destination.

    Raises:
        MicrosoftTeamsActionError: If a required parameter is missing.

    """
    if destination == DESTINATION_CHANNEL:
        if not team_name or not channel_name:
            message = f"'Team Name' and 'Channel Name' are required when 'Destination Type' is '{DESTINATION_CHANNEL}'."
            raise MicrosoftTeamsActionError(message)
    elif destination == DESTINATION_CHAT:
        if not chat_id:
            message = f"'Chat ID' is required when 'Destination Type' is '{DESTINATION_CHAT}'."
            raise MicrosoftTeamsActionError(message)
    else:
        message = f"Unsupported 'Destination Type' '{destination}'."
        raise MicrosoftTeamsActionError(message)


def format_warnings(warnings: list[str]) -> str:
    """Format card warnings for an action output message.

    Args:
        warnings: The warnings to format.

    Returns:
        The text to append to the output message, empty if there are no warnings.

    """
    if not warnings:
        return ""

    return "\nWarnings:\n" + "\n".join(f"- {warning}" for warning in warnings)


def find_card_attachment_id(message: dict[str, Any]) -> str | None:
    """Return the ID of the first Adaptive Card attachment of a message.

    Args:
        message: The chatMessage as returned by the Microsoft Graph API.

    Returns:
        The attachment ID, or None if the message has no Adaptive Card.

    """
    for attachment in message.get("attachments") or []:
        if attachment.get("contentType") == ADAPTIVE_CARD_CONTENT_TYPE:
            return attachment.get("id")

    return None


def _load_json(raw_card: str | dict[str, Any]) -> object:
    if not isinstance(raw_card, str):
        return raw_card

    try:
        return json.loads(raw_card)
    except json.JSONDecodeError as error:
        message = (
            f"The card is not valid JSON (line {error.lineno}, column {error.colno}): {error.msg}. {JSON_ERROR_HINT}"
        )
        raise MicrosoftTeamsCardError(message) from error


def _unwrap_envelope(envelope: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    adaptive = [
        attachment
        for attachment in envelope.get("attachments") or []
        if isinstance(attachment, dict) and attachment.get("contentType") == ADAPTIVE_CARD_CONTENT_TYPE
    ]
    if not adaptive:
        message = (
            f"The Bot Framework message does not contain an attachment with contentType '{ADAPTIVE_CARD_CONTENT_TYPE}'."
        )
        raise MicrosoftTeamsCardError(message)

    if len(envelope["attachments"]) > 1:
        warnings.append("The message contains multiple attachments. Only the first Adaptive Card is used.")

    content = _load_json(adaptive[0].get("content"))
    if not isinstance(content, dict):
        message = "The attachment 'content' must be an Adaptive Card JSON object."
        raise MicrosoftTeamsCardError(message)

    return content


def _check_version(card: dict[str, Any], warnings: list[str]) -> None:
    version = str(card.get("version", ""))
    try:
        parsed = tuple(int(part) for part in version.split(".")[:2])
    except ValueError:
        warnings.append(f"The card version '{version}' is not a valid version.")
        return

    if parsed > ADAPTIVE_CARD_MAX_VERSION:
        warnings.append(
            f"The card version {version} is higher than "
            f"{'.'.join(str(part) for part in ADAPTIVE_CARD_MAX_VERSION)}, "
            "which Teams desktop and web support."
        )


def _walk(node: object, path: str, errors: list[str], warnings: list[str]) -> None:
    if isinstance(node, list):
        for index, item in enumerate(node):
            _walk(item, f"{path}[{index}]", errors, warnings)
        return

    if not isinstance(node, dict):
        return

    node_type = node.get("type")
    if isinstance(node_type, str):
        if node_type.startswith(ACTION_TYPE_PREFIX):
            _check_action(node, node_type, path, errors, warnings)
        elif node_type.startswith(INPUT_TYPE_PREFIX):
            warnings.append(
                f"{path} is an input element. Inputs cannot be submitted from "
                "a card sent through the Microsoft Graph API."
            )
        elif node_type == "Image":
            _check_image(node, path, errors, warnings)

    for key, value in node.items():
        _walk(value, f"{path}.{key}", errors, warnings)


def _check_action(
    node: dict[str, Any],
    action_type: str,
    path: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    if action_type in REJECTED_CARD_ACTIONS:
        errors.append(f"{path} uses '{action_type}', which {REJECTED_CARD_ACTIONS[action_type]}")
    elif action_type == ACTION_OPEN_URL:
        url = str(node.get("url", "")).strip()
        if url.lower().startswith(UNSAFE_URL_SCHEMES):
            errors.append(f"{path} uses an unsafe URL scheme in '{url[:30]}'")
        elif not url.lower().startswith("https://"):
            warnings.append(f"{path} opens a URL that is not https.")
    else:
        warnings.append(
            f"{path} uses '{action_type}', which the Microsoft Graph API may "
            f"not support. Only '{ACTION_OPEN_URL}' is guaranteed to work."
        )


def _check_image(node: dict[str, Any], path: str, errors: list[str], warnings: list[str]) -> None:
    url = str(node.get("url", "")).strip().lower()
    if url.startswith(("javascript:", "file:", "vbscript:")):
        errors.append(f"{path} uses an unsafe image URL scheme")
    elif url.startswith("http://"):
        warnings.append(f"{path} loads an image over http.")
