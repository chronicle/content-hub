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

"""Shared utility helpers for the AkeylessSecurity integration."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, NoReturn

from .constants import (
    DEFAULT_SECRET_VERSION,
    MIN_MASK_LENGTH,
    RESOURCE_NAME_PATTERN,
)
from .exceptions import AkeylessSecurityError, InvalidConfigurationError

__all__ = [
    "build_lookup_with_warnings",
    "mask_id",
    "raise_api_error",
    "resolve_secret_and_version",
    "validate_param_mappings",
]

if TYPE_CHECKING:
    from collections.abc import Callable

    from TIPCommon.base.interfaces import ScriptLogger
    from TIPCommon.types import SingleJson


def _extract_error_from_dict(data: SingleJson) -> str | None:
    """Extract a human-readable error message from a parsed JSON dictionary.

    Args:
        data: Parsed JSON dictionary from an API error response.

    Returns:
        The extracted error message, or None if not found.

    """
    error_val: object = data.get("error")
    if isinstance(error_val, str) and error_val.strip():
        return error_val.strip()
    if isinstance(error_val, dict):
        nested: object = error_val.get("message") or error_val.get("description") or error_val.get("error")
        if isinstance(nested, str) and nested.strip():
            return nested.strip()

    for key in ("message", "detail", "error_description"):
        val: object = data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()

    return None


def _extract_error_from_body(raw_body: str | bytes | None) -> str | None:
    """Extract a human-readable error message from an HTTP response body.

    Args:
        raw_body: The raw HTTP response body as string, bytes, or None.

    Returns:
        The extracted error message, or None if empty.

    """
    if raw_body is None:
        return None

    text: str = (
        raw_body.decode("utf-8", errors="replace").strip() if isinstance(raw_body, bytes) else str(raw_body).strip()
    )
    if not text:
        return None

    try:
        data: object = json.loads(text)
    except (ValueError, TypeError):
        return text

    if isinstance(data, dict):
        return _extract_error_from_dict(data) or text

    return text


def _format_status_detail(
    status: int | str | None,
    reason: str | None,
    raw_body: str | bytes | None,
) -> str:
    """Format HTTP status code, reason, and extracted body error into a single string.

    Args:
        status: HTTP status code.
        reason: HTTP status reason phrase.
        raw_body: Raw HTTP response body.

    Returns:
        The formatted status and error detail string.

    """
    body_error: str | None = _extract_error_from_body(raw_body)
    status_part: str
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

    return body_error or status_part


def raise_api_error(
    error: Exception,
    exception_cls: type[AkeylessSecurityError] = AkeylessSecurityError,
) -> NoReturn:
    """Extract details from an AkeylessSecurity API exception and raise a concise error.

    Args:
        error: The exception caught from the Akeyless SDK or HTTP request.
        exception_cls: Exception class to raise.

    """
    target_err: object = error
    if isinstance(error, AttributeError) and getattr(getattr(error, "__context__", None), "reason", None):
        target_err = error.__context__

    status: int | str | None = getattr(target_err, "status", None)
    reason: str | None = getattr(target_err, "reason", None)
    body: str | bytes | None = getattr(target_err, "body", None)
    detail: str = (
        _format_status_detail(status, reason, body) or str(target_err)
        if (status is not None or reason is not None or body is not None)
        else str(target_err)
    )
    raise exception_cls(detail) from None


def mask_id(value: str) -> str:
    """Mask a secret ID for safe logging.

    Args:
        value: The raw secret ID string.

    Returns:
        The masked secret ID.

    """
    if len(value) <= MIN_MASK_LENGTH:
        return "***"

    return f"{value[:3]}***{value[-3:]}"


def resolve_secret_and_version(mapped_value: str) -> tuple[str, str]:
    """Parse the mapped string, defaulting to DEFAULT_SECRET_VERSION if not explicitly provided.

    Args:
        mapped_value: The value from the JSON/YAML mapping (e.g., 'secret-id:version').

    Returns:
        The (secret_id, resolved_version) tuple.

    Raises:
        InvalidConfigurationError: If the mapped value is in an invalid format.

    """
    mapped_value = str(mapped_value).strip()
    match = RESOURCE_NAME_PATTERN.match(mapped_value)
    if not match:
        msg = (
            f"Invalid credential mapping format for value '{mapped_value}'. "
            f"Expected format: 'secret_name' or 'secret_name:version' "
            f"(where version is a positive integer or '{DEFAULT_SECRET_VERSION}')."
        )
        raise InvalidConfigurationError(msg)

    gd: dict[str, str | None] = match.groupdict()
    secret_id: str = gd["secret"] or ""
    version_id: str = gd["version"] or DEFAULT_SECRET_VERSION

    return secret_id, version_id


def validate_param_mappings(
    category: str,
    category_mapping: SingleJson,
) -> int:
    """Validate component parameter mappings within a category.

    Args:
        category: Category name (instances, connectors, or jobs).
        category_mapping: Dictionary of component to parameter mappings.

    Returns:
        Number of valid mapped parameters found.

    Raises:
        InvalidConfigurationError: If any component or parameter format is invalid.

    """
    if not isinstance(category_mapping, dict):
        msg = f"Category '{category}' must be a dictionary."
        raise InvalidConfigurationError(msg)

    mappings_count: int = 0
    for component_name, param_mapping in category_mapping.items():
        if not isinstance(param_mapping, dict):
            msg = f"Parameters for '{component_name}' in category '{category}' must be a dictionary."
            raise InvalidConfigurationError(msg)

        for param_name, mapped_value in param_mapping.items():
            mappings_count += 1
            val = str(mapped_value).strip()
            if not RESOURCE_NAME_PATTERN.match(val):
                msg = (
                    f"Invalid format for parameter '{param_name}' of '{component_name}' "
                    f"in category '{category}': '{val}'. "
                    f"Expected format: 'secret_name' or 'secret_name:version'."
                )
                raise InvalidConfigurationError(msg)

    return mappings_count


def build_lookup_with_warnings(
    items: list[Any],
    extract_pair: Callable[[Any], tuple[str, Any]],
    logger: ScriptLogger,
) -> SingleJson:
    """Build a lookup dictionary and log a warning on duplicate keys.

    Args:
        items: The list of items to process.
        extract_pair: Function returning (key, value) for each item.
        logger: The logger instance to use for warnings.

    Returns:
        The constructed dictionary mapping.

    """
    lookup: SingleJson = {}
    for item in items:
        key, value = extract_pair(item)
        if not key:
            continue
        if key in lookup:
            logger.warn(f"Duplicate entry '{key}' detected. Later entry will overwrite.")
        lookup[key] = value

    return lookup
