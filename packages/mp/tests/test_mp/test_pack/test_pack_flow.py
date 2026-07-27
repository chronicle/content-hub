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

import json
from typing import TYPE_CHECKING
from unittest import mock

import toml

from mp.pack.flow.integrations.flow import IntegrationPacker, PackConfig, get_current_version

if TYPE_CHECKING:
    from pathlib import Path


@mock.patch("mp.pack.flow.integrations.flow.find_integration_src_path")
@mock.patch("mp.pack.flow.integrations.flow.get_git_repo_root")
@mock.patch("mp.pack.flow.integrations.flow.get_current_version")
@mock.patch("mp.pack.flow.integrations.flow.IntegrationPacker._checkout_version_from_git")
@mock.patch("mp.pack.flow.integrations.flow.IntegrationPacker._build_and_process_integration")
def test_pack_current_version(
    mock_build: mock.Mock,
    mock_checkout: mock.Mock,
    mock_get_version: mock.Mock,
    mock_repo_root: mock.Mock,
    mock_find_path: mock.Mock,
) -> None:
    mock_find_path.return_value = (mock.MagicMock(), "my_integration")
    mock_repo_root.return_value = mock.MagicMock()
    mock_get_version.return_value = "1.0"

    config = PackConfig(version="1.0")
    packer = IntegrationPacker("my_integration", config)
    packer.pack()

    mock_checkout.assert_not_called()
    mock_build.assert_called_once()


@mock.patch("mp.pack.flow.integrations.flow.find_integration_src_path")
@mock.patch("mp.pack.flow.integrations.flow.get_git_repo_root")
@mock.patch("mp.pack.flow.integrations.flow.get_current_version")
@mock.patch("mp.pack.flow.integrations.flow.IntegrationPacker._checkout_version_from_git")
@mock.patch("mp.pack.flow.integrations.flow.IntegrationPacker._build_and_process_integration")
@mock.patch("mp.pack.flow.integrations.flow.remove_git_worktree")
def test_pack_different_version(  # ruff:ignore[too-many-arguments, too-many-positional-arguments]
    mock_remove_worktree: mock.Mock,
    mock_build: mock.Mock,
    mock_checkout: mock.Mock,
    mock_get_version: mock.Mock,
    mock_repo_root: mock.Mock,
    mock_find_path: mock.Mock,
) -> None:
    mock_find_path.return_value = (mock.MagicMock(), "my_integration")
    mock_repo_root.return_value = mock.MagicMock()
    mock_get_version.return_value = "1.0"
    mock_checkout.return_value = mock.MagicMock()

    config = PackConfig(version="2.0")
    packer = IntegrationPacker("my_integration", config)
    packer.pack()

    mock_checkout.assert_called_once()
    mock_build.assert_called_once()
    mock_remove_worktree.assert_called_once()


def test_get_current_version_from_def(tmp_path: Path) -> None:
    def_file: Path = tmp_path / "Integration-MyIntegration.def"
    def_file.write_text(json.dumps({"Version": "2.0"}), encoding="utf-8")
    version: str = get_current_version(tmp_path)
    assert version == "2.0"


def test_get_current_version_from_pyproject(tmp_path: Path) -> None:
    pyproject_file: Path = tmp_path / "pyproject.toml"
    pyproject_file.write_text(toml.dumps({"project": {"version": "1.0"}}), encoding="utf-8")
    version: str = get_current_version(tmp_path)
    assert version == "1.0"
