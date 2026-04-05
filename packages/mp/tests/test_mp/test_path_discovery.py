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

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

import pytest

from mp.describe.common.describe_all import get_all_integrations_paths
from mp.describe.common.utils import paths

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


@pytest.fixture
def mock_integration(tmp_path: pathlib.Path) -> pathlib.Path:
    integration_path = tmp_path / "mock_integration"
    integration_path.mkdir()
    (integration_path / "pyproject.toml").write_text("[project]\nname = 'Mock Integration'")
    return integration_path


def test_get_integration_path_by_direct_path(mock_integration: pathlib.Path) -> None:
    # Test that we can find an integration by its direct path
    path = paths.get_integration_path(str(mock_integration))
    assert pathlib.Path(str(path)) == mock_integration


def test_get_integration_path_by_relative_path(
    mock_integration: pathlib.Path, monkeypatch: MonkeyPatch
) -> None:
    # Test that we can find an integration by its relative path from CWD
    monkeypatch.chdir(mock_integration.parent)
    path = paths.get_integration_path("mock_integration")
    assert pathlib.Path(str(path)).resolve() == mock_integration.resolve()


def test_get_integration_path_custom_repo(tmp_path: pathlib.Path, monkeypatch: MonkeyPatch) -> None:
    # Test discovery in custom repo
    marketplace = tmp_path / "marketplace"
    content = marketplace / "content" / "response_integrations"
    custom = content / "custom"
    custom.mkdir(parents=True)

    integration = custom / "custom_int"
    integration.mkdir()
    (integration / "pyproject.toml").write_text("[project]\nname = 'Custom Int'")

    # Configure mp to use this marketplace
    monkeypatch.setattr("mp.core.config.get_marketplace_path", lambda: marketplace)

    path = paths.get_integration_path("custom_int")
    assert pathlib.Path(str(path)).resolve() == integration.resolve()


def test_get_all_integrations_paths_custom_repo(
    tmp_path: pathlib.Path, monkeypatch: MonkeyPatch
) -> None:
    # Test bulk discovery in custom repo
    marketplace = tmp_path / "marketplace"
    content = marketplace / "content" / "response_integrations"
    custom = content / "custom"
    custom.mkdir(parents=True)

    int1 = custom / "int1"
    int1.mkdir()
    (int1 / "pyproject.toml").write_text("[project]\nname = 'Int 1'")

    int2 = custom / "int2"
    int2.mkdir()
    (int2 / "pyproject.toml").write_text("[project]\nname = 'Int 2'")

    # Configure mp to use this marketplace
    monkeypatch.setattr("mp.core.config.get_marketplace_path", lambda: marketplace)

    all_paths = get_all_integrations_paths()
    assert len(all_paths) == 2
    assert int1.resolve() in [p.resolve() for p in all_paths]
    assert int2.resolve() in [p.resolve() for p in all_paths]
