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

import shutil
import unittest.mock
from typing import TYPE_CHECKING, Any

import pytest

import mp.build_project.integrations_repo
import mp.core.constants
import test_mp.common

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from mp.build_project.integrations_repo import IntegrationsRepo


def test_deconstruct_half_built_integration(
    tmp_path: Path,
    half_built_integration: Path,
    mock_get_marketplace_path: str,
    assert_deconstruct_integration: Callable[[Path], None],
) -> None:
    with unittest.mock.patch(mock_get_marketplace_path, return_value=tmp_path):
        assert_deconstruct_integration(half_built_integration)


def test_deconstruct_non_built_integration(
    tmp_path: Path,
    non_built_integration: Path,
    mock_get_marketplace_path: str,
    assert_deconstruct_integration: Callable[[Path], None],
) -> None:
    with unittest.mock.patch(mock_get_marketplace_path, return_value=tmp_path):
        assert_deconstruct_integration(non_built_integration)


def test_deconstruct_built_integration(
    tmp_path: Path,
    built_integration: Path,
    mock_get_marketplace_path: str,
    assert_deconstruct_integration: Callable[[Path], None],
) -> None:
    with unittest.mock.patch(mock_get_marketplace_path, return_value=tmp_path):
        assert_deconstruct_integration(built_integration)


def test_non_existing_integration_raises_file_not_found_error(
    tmp_path: Path,
    mock_get_marketplace_path: str,
    assert_deconstruct_integration: Callable[[Path], None],
) -> None:
    with (
        unittest.mock.patch(mock_get_marketplace_path, return_value=tmp_path),
        pytest.raises(FileNotFoundError, match=r"Invalid integration .*"),
    ):
        assert_deconstruct_integration(tmp_path / "fake_integration")


@pytest.fixture
def assert_deconstruct_integration(
    tmp_path: Path,
    non_built_integration: Path,
) -> Callable[[Path], None]:
    def wrapper(integration_path: Path) -> None:
        commercial: Path = tmp_path / non_built_integration.parent.name
        shutil.copytree(integration_path.parent, commercial)
        integration: Path = commercial / integration_path.name
        py_version: Path = integration / mp.core.constants.PYTHON_VERSION_FILE
        if integration.exists():
            requirements: Path = integration / mp.core.constants.REQUIREMENTS_FILE
            requirements.write_text("requests==2.32.4\n", encoding="utf-8")
            py_version.write_text("3.11", encoding="utf-8")

        marketplace: IntegrationsRepo = mp.build_project.integrations_repo.IntegrationsRepo(
            commercial
        )
        marketplace.deconstruct_integration(integration)

        out_integration: Path = marketplace.out_dir / integration.name
        actual_files: set[str] = {p.name for p in out_integration.rglob("*.*")}
        expected_files: set[str] = {p.name for p in non_built_integration.rglob("*.*")}
        assert actual_files == expected_files

        actual: dict[str, Any]
        expected: dict[str, Any]
        actual, expected = test_mp.common.get_toml_content(
            expected=non_built_integration / mp.core.constants.PROJECT_FILE,
            actual=out_integration / mp.core.constants.PROJECT_FILE,
        )
        assert actual == expected

        actual, expected = test_mp.common.get_yaml_content(
            expected=non_built_integration / mp.core.constants.RELEASE_NOTES_FILE,
            actual=out_integration / mp.core.constants.RELEASE_NOTES_FILE,
        )
        assert actual == expected

        actual, expected = test_mp.common.get_yaml_content(
            expected=non_built_integration / mp.core.constants.DEFINITION_FILE,
            actual=out_integration / mp.core.constants.DEFINITION_FILE,
        )
        assert actual == expected

        actual, expected = test_mp.common.get_yaml_content(
            expected=non_built_integration / mp.core.constants.MAPPING_RULES_FILE,
            actual=out_integration / mp.core.constants.MAPPING_RULES_FILE,
        )
        assert actual == expected

        actual, expected = test_mp.common.get_yaml_content(
            expected=non_built_integration / mp.core.constants.CUSTOM_FAMILIES_FILE,
            actual=out_integration / mp.core.constants.CUSTOM_FAMILIES_FILE,
        )
        assert actual == expected

    return wrapper
