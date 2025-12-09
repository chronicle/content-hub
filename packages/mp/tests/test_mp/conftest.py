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

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import mp.core.constants

if TYPE_CHECKING:
    from mp.core.config import RuntimeParams

MOCK_CONTENT_HUB_DIR_NAME: str = "mock_content_hub"

INTEGRATION_NAME: str = "mock_integration"
BUILT_INTEGRATION_DIR_NAME: str = "mock_built_integration"

NON_BUILT_PLAYBOOK: str = "mock_non_built_playbook"
MOCK_NON_BUILT_BLOCK: str = "mock_non_built_block"
BUILT_PLAYBOOK: str = "mock_built_playbook/mock_built_playbook.json"
BUILT_BLOCK: str = "mock_built_block/mock_built_block.json"


@pytest.fixture(autouse=True)
def set_runtime_params() -> None:
    params: RuntimeParams = mp.core.config.RuntimeParams(quiet=True, verbose=False)
    params.set_in_config()


@pytest.fixture
def mock_get_marketplace_path() -> str:
    """Mock the import path of the `mp.core.config.get_marketplace_path()` function."""
    return "mp.core.config.get_marketplace_path"


@pytest.fixture
def mock_content_hub() -> Path:
    """Path of a mocked marketplace."""
    return Path(__file__).parent / MOCK_CONTENT_HUB_DIR_NAME


@pytest.fixture
def mock_response_integrations(mock_content_hub: Path) -> Path:
    """Path to the mocked response integrations."""
    return mock_content_hub / mp.core.constants.INTEGRATIONS_DIR_NAME


@pytest.fixture
def mock_community(mock_response_integrations: Path) -> Path:
    """Path of mocked third_party community integrations."""
    return mock_response_integrations / mp.core.constants.COMMUNITY_DIR_NAME


@pytest.fixture
def mock_commercial(mock_response_integrations: Path) -> Path:
    """Path of mocked commercial integrations."""
    return mock_response_integrations / mp.core.constants.COMMERCIAL_DIR_NAME


@pytest.fixture
def built_integration(mock_response_integrations: Path) -> Path:
    """Path of a mocked built integration."""
    return mock_response_integrations / BUILT_INTEGRATION_DIR_NAME / INTEGRATION_NAME


@pytest.fixture
def half_built_integration(mock_commercial: Path) -> Path:
    """Path of a mocked half-built integration."""
    return mock_commercial / INTEGRATION_NAME


@pytest.fixture
def non_built_integration(mock_community: Path) -> Path:
    """Path of a mocked non-built integration."""
    return mock_community / INTEGRATION_NAME


@pytest.fixture
def full_details(built_integration: Path) -> Path:
    """Path to a mock `full-details` file."""
    return built_integration / mp.core.constants.INTEGRATION_FULL_DETAILS_FILE.format(
        INTEGRATION_NAME,
    )


@pytest.fixture
def marketplace_json(mock_response_integrations: Path) -> Path:
    """Path to a mock `marketplace.json` file."""
    return (
        mock_response_integrations
        / BUILT_INTEGRATION_DIR_NAME
        / mp.core.constants.MARKETPLACE_JSON_NAME
    )


@pytest.fixture
def mock_playbook_path(mock_content_hub: Path) -> Path:
    """Path to the mocked playbook folder."""
    return mock_content_hub / mp.core.constants.PLAYBOOKS_DIR_NAME


@pytest.fixture
def non_built_playbook_path(mock_playbook_path: Path) -> Path:
    """Path to mocked non-built playbook."""
    return mock_playbook_path / NON_BUILT_PLAYBOOK


@pytest.fixture
def non_built_block_path(mock_playbook_path: Path) -> Path:
    """Path to mocked non-built block."""
    return mock_playbook_path / MOCK_NON_BUILT_BLOCK


@pytest.fixture
def built_playbook_path(mock_playbook_path: Path) -> Path:
    """Path to the mocked built playbook"""
    return mock_playbook_path / BUILT_PLAYBOOK


@pytest.fixture
def built_block_path(mock_playbook_path: Path) -> Path:
    """Path to the mocked built block"""
    return mock_playbook_path / BUILT_BLOCK


@pytest.fixture
def playbooks_json_path(mock_playbook_path: Path) -> Path:
    """Path to the mocked playbooks.json file"""
    return mock_playbook_path / mp.core.constants.PLAYBOOKS_JSON_NAME
