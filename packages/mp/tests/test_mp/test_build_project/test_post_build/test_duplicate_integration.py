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
import shutil
from typing import TYPE_CHECKING

import pytest

import mp.build_project.post_build.duplicate_integrations
import mp.core.constants
from mp.build_project.post_build.duplicate_integrations import (
    raise_errors_for_duplicate_integrations,
)

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


@pytest.fixture
def temp_marketplace_paths(
    tmp_path: Path,
) -> Generator[tuple[Path, Path], None, None]:
    commercial = tmp_path / "commercial"
    community = tmp_path / "community"
    commercial.mkdir()
    community.mkdir()

    # Create marketplace.json files to avoid test failures
    _create_marketplace_json(commercial)
    _create_marketplace_json(community)

    yield commercial, community
    shutil.rmtree(tmp_path)


def _create_marketplace_json(marketplace_path: Path) -> None:
    """Create an empty marketplace.json file in the given marketplace path.

    Args:
        marketplace_path: Path to the marketplace directory

    """
    mp_json_path = marketplace_path / mp.core.constants.MARKETPLACE_JSON_NAME
    mp_json_path.write_text(json.dumps([]), encoding="utf-8")


def test_duplicate_integration_same_marketplace(temp_marketplace_paths: tuple[Path, Path]) -> None:
    commercial, _ = temp_marketplace_paths
    integration_path = commercial / "test_integration"
    integration_path.mkdir(parents=True)

    # Create an ` integration.def ` file with identifier
    _create_integration_def(integration_path, "test-integration")

    # Create a duplicate integration in the same marketplace
    duplicate_path = commercial / "test_integration_copy"
    duplicate_path.mkdir(parents=True)
    _create_integration_def(duplicate_path, "test-integration")  # Same identifier

    # Update marketplace.json with duplicates
    _create_marketplace_json_with_integrations(
        commercial,
        [
            {"Identifier": "test-integration", "DisplayName": "Test Integration"},
            {"Identifier": "test-integration", "DisplayName": "Test Integration Copy"},
        ],
    )

    with pytest.raises(
        mp.build_project.post_build.duplicate_integrations.IntegrationExistsError,
        match=r"Found multiple integrations with the same identifier: .*",
    ):
        raise_errors_for_duplicate_integrations(commercial, commercial)


def test_duplicate_integration_across_marketplaces(
    temp_marketplace_paths: tuple[Path, Path],
) -> None:
    commercial, community = temp_marketplace_paths

    # Create the same integration in both marketplaces
    integration_path = commercial / "test_integration"
    integration_path.mkdir(parents=True)
    _create_integration_def(integration_path, "test-integration")

    community_integration = community / "test_integration"
    community_integration.mkdir(parents=True)
    _create_integration_def(community_integration, "test-integration")

    # Update marketplace.json files with the same identifier in both marketplaces
    _create_marketplace_json_with_integrations(
        commercial,
        [{"Identifier": "test-integration", "DisplayName": "Test Integration"}],
    )
    _create_marketplace_json_with_integrations(
        community,
        [{"Identifier": "test-integration", "DisplayName": "Test Integration"}],
    )

    with pytest.raises(
        mp.build_project.post_build.duplicate_integrations.IntegrationExistsError,
        match="The following integrations found in more than one marketplace:",
    ):
        raise_errors_for_duplicate_integrations(commercial, community)


def _create_integration_def(integration_path: Path, identifier: str) -> None:
    """Create an integration definition file with the given identifier.

    Args:
        integration_path: Path to the integration directory
        identifier: The integration identifier to use

    """
    def_file_path = integration_path / mp.core.constants.INTEGRATION_DEF_FILE.format(
        integration_path.name
    )
    def_file_content = {
        "Identifier": identifier,
        "DisplayName": f"{integration_path.name} Integration",
        "Version": "1",
    }
    def_file_path.write_text(json.dumps(def_file_content), encoding="utf-8")


def _create_marketplace_json_with_integrations(
    marketplace_path: Path,
    integrations: list[dict],
) -> None:
    """Create a marketplace.json file with the given integrations.

    Args:
        marketplace_path: Path to the marketplace directory
        integrations: List of integration dictionaries to include

    """
    mp_json_path = marketplace_path / mp.core.constants.MARKETPLACE_JSON_NAME
    mp_json_path.write_text(json.dumps(integrations), encoding="utf-8")
