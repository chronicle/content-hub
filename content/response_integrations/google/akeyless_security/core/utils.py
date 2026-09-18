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

"""Shared utility helpers for the Akeyless integration."""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from .authentication import extract_integration_parameters
from .constants import MIN_MASK_LENGTH
from .exceptions import AkeylessError

__all__ = [
    "build_lookup_with_warnings",
    "extract_integration_parameters",
    "mask_id",
    "validate_response",
]

if TYPE_CHECKING:
    from collections.abc import Callable

    from TIPCommon.base.interfaces import ScriptLogger
    from TIPCommon.types import SingleJson


def _extract_error_from_dict(data: dict[str, object]) -> str | None:
    """Extract a human-readable error message from a parsed JSON dictionary.

    Args:
        data: Parsed JSON dictionary from an API error response.

    Returns:
        str | None: The extracted error message, or None if not found.

    """
    error_val = data.get("error")
    if isinstance(error_val, str) and error_val.strip():
        return error_val.strip()
    if isinstance(error_val, dict):
        nested = (
            error_val.get("message")
            or error_val.get("description")
            or error_val.get("error")
        )
        if isinstance(nested, str) and nested.strip():
            return nested.strip()

    for key in ("message", "detail", "error_description"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()

    return None


def _extract_error_from_body(raw_body: str | bytes | None) -> str | None:
    """Extract a human-readable error message from an HTTP response body.

    Args:
        raw_body: The raw HTTP response body as string, bytes, or None.

    Returns:
        str | None: The extracted error message, or None if empty.

    """
    if raw_body is None:
        return None

    text = (
        raw_body.decode("utf-8", errors="replace").strip()
        if isinstance(raw_body, bytes)
        else str(raw_body).strip()
    )
    if not text:
        return None

    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return text

    if isinstance(data, dict):
        return _extract_error_from_dict(data) or text

    return text


def _format_status_detail(
    status: int | str | None,
    reason: str | None,
    raw_body: str | bytes | None,
    fallback: str = "",
) -> str:
    """Format HTTP status code, reason, and extracted body error into a single string.

    Args:
        status: HTTP status code.
        reason: HTTP status reason phrase.
        raw_body: Raw HTTP response body.
        fallback: Fallback message when status, reason, and body are empty.

    Returns:
        str: The formatted status and error detail string.

    """
    body_error = _extract_error_from_body(raw_body)
    if status and reason:
        status_part = f"({status}) {reason}"
    elif status:
        status_part = f"({status})"
    elif reason:
        status_part = str(reason)
    else:
        status_part = ""

    if status_part and body_error:
        return f"{status_part} - {body_error}"
    return body_error or status_part or fallback


def validate_response(
    response: object,
    error_msg: str | None = None,
    exception_cls: type[AkeylessError] = AkeylessError,
) -> None:
    """Validate an Akeyless API response or exception and raise a concise error.

    Parses the HTTP response body (e.g. ``{"error": "..."}`` JSON payloads) and
    status code/reason while omitting verbose HTTP response headers.

    Args:
        response: An HTTP response object, SDK response, or raised exception.
        error_msg: Optional prefix message describing the failed operation.
        exception_cls: Exception class to raise on error. Defaults to ``AkeylessError``.

    """
    if isinstance(response, Exception):
        target_err: object = response
        if isinstance(response, AttributeError) and getattr(
            getattr(response, "__context__", None), "reason", None
        ):
            target_err = response.__context__

        status = getattr(target_err, "status", None)
        reason = getattr(target_err, "reason", None)
        body = getattr(target_err, "body", None)
        detail = (
            _format_status_detail(status, reason, body, fallback=str(target_err))
            if (status is not None or reason is not None or body is not None)
            else str(target_err)
        )
        msg = (
            f"{error_msg}: {detail}"
            if error_msg and not detail.startswith(error_msg)
            else detail
        )
        raise exception_cls(msg) from response

    status = getattr(response, "status", None) or getattr(
        response, "status_code", None
    )
    if isinstance(status, int) and not (
        HTTPStatus.OK <= status < HTTPStatus.MULTIPLE_CHOICES
    ):
        reason = getattr(response, "reason", None)
        raw_body = (
            getattr(response, "data", None)
            or getattr(response, "text", None)
            or getattr(response, "body", None)
        )
        detail = _format_status_detail(status, reason, raw_body)
        msg = f"{error_msg}: {detail}" if error_msg else detail
        raise exception_cls(msg)


def mask_id(value: str) -> str:
    """Mask a secret ID for safe logging.

    Returns:
        str: The masked secret ID.

    """
    if len(value) <= MIN_MASK_LENGTH:
        return "***"

    return f"{value[:3]}***{value[-3:]}"


def build_lookup_with_warnings(
    items: list[Any],
    get_key: Callable[[Any], str],
    get_value: Callable[[Any], Any],
    entity_type: str,
    logger: ScriptLogger,
) -> SingleJson:
    """Build a lookup dict and warn on duplicates.

    Args:
        items: The list of items to process.
        get_key: Function to extract the key from an item.
        get_value: Function to extract the value from an item.
        entity_type: Label for logging (e.g., 'job name').
        logger: The logger instance to use for warnings.

    Returns:
        The constructed dictionary mapping.

    """
    lookup: SingleJson = {}
    for item in items:
        key = get_key(item)
        if not key:
            continue
        if key in lookup:
            logger.warn(f"Duplicate {entity_type} '{key}' detected. Later entry will overwrite.")
        lookup[key] = get_value(item)

    return lookup
