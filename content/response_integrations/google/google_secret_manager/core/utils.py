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

"""Shared utility helpers for the Google Secret Manager integration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def mask_id(value: str) -> str:
    """Mask a secret ID for safe logging."""
    if len(value) <= 6:
        return "***"

    return f"{value[:3]}***{value[-3:]}"


def build_lookup_with_warnings(
    items: list,
    get_key: Callable[[Any], Any],
    get_value: Callable[[Any], Any],
    entity_type: str,
    logger: Any,
) -> dict:
    """Generic helper to build a lookup dict and warn on duplicates.

    Args:
        items: The list of items to process.
        get_key: Function to extract the key from an item.
        get_value: Function to extract the value from an item.
        entity_type: Label for logging (e.g., 'job name').
        logger: The logger instance to use for warnings.

    Returns:
        The constructed dictionary mapping.

    """
    lookup: dict = {}
    for item in items:
        key = get_key(item)
        if not key:
            continue
        if key in lookup:
            logger.warn(f"Duplicate {entity_type} '{key}' detected. Later entry will overwrite.")
        lookup[key] = get_value(item)

    return lookup
