"""Utilities for validating integration uniqueness across marketplaces.

This module provides functions to check for duplicate integration identifiers
between different marketplace repositories, such as commercial and community
offerings. It defines an exception to be raised when such duplicates are found.
"""

# Copyright 2025 Google LLC
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
from typing import TYPE_CHECKING

import mp.core.constants

if TYPE_CHECKING:
    from pathlib import Path

    from .data_models import BuiltFullDetailsIntegrationMetadata


class IntegrationExistsError(Exception):
    """Integration already exists in the marketplace."""


def raise_errors_for_duplicate_integrations(commercial_path: Path, community_path: Path) -> None:
    """Check for duplicate integrations between commercial and third party repos.

    Args:
        commercial_path: path to the commercial marketplace
        community_path: path to the third_party marketplace

    """
    commercials: set[str] = _get_marketplace_integrations(
        commercial_path / mp.core.constants.MARKETPLACE_JSON_NAME,
    )
    communities: set[str] = _get_marketplace_integrations(
        community_path / mp.core.constants.MARKETPLACE_JSON_NAME,
    )
    _raise_error_for_integration_duplicates(communities, commercials)


def _get_marketplace_integrations(mp_json_path: Path) -> set[str]:
    """Get a set of all marketplace integration identifiers.

    Args:
        mp_json_path: path to the `marketplace.json` file

    Returns:
        A set of all integration identifiers of the marketplace that `mp_json_path`
        contains.

    Raises:
        IntegrationExistsError:
            when an integration with the same identifier is found in both of the
            marketplaces

    """
    content: str = mp_json_path.read_text(encoding="utf-8")
    integrations: list[BuiltFullDetailsIntegrationMetadata] = json.loads(content)
    results: set[str] = set()
    duplicates: set[str] = set()
    for integration in integrations:
        identifier: str = integration["Identifier"]
        if identifier in results:
            duplicates.add(identifier)

        else:
            results.add(identifier)

    if duplicates:
        ids: str = ", ".join(duplicates)
        msg: str = f"Found multiple integrations with the same identifier: {', '.join(ids)}"
        raise IntegrationExistsError(msg)

    return results


def _raise_error_for_integration_duplicates(s1: set[str], s2: set[str], /) -> None:
    duplicates: set[str] = s1.intersection(s2)
    if duplicates:
        msg: str = (
            "The following integrations found in more than one marketplace: "
            f"{', '.join(duplicates)}"
        )
        raise IntegrationExistsError(msg)
