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

from typing import TYPE_CHECKING, Any

from .constants import MIN_MASK_LENGTH

if TYPE_CHECKING:
    from collections.abc import Callable

    from TIPCommon.base.interfaces import ScriptLogger
    from TIPCommon.types import SingleJson


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
