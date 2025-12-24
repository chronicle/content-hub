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

import sys
import unittest.mock
from typing import TYPE_CHECKING

import pytest

import mp.core.constants
import mp.core.unix

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path
    from unittest.mock import MagicMock

DEV_DEPENDENCY_NAME: str = "beautifulsoup4"
REQUIREMENT_LINE: str = "black>=24.10.0"
TIPCOMMON_NAME: str = "tipcommon"
ENVCOMMON_NAME: str = "environmentcommon"
NEW_TIPCOMMON_VERSION: str = "2.0.2"
OLD_TIPCOMMON_VERSION: str = "1.0.10"
PACKAGE_PATH: str = "path/to/{0}.whl"
DEFAULT_DEV_DEPENDENCIES: list[str] = ["pytest", "pytest-json-report", "soar-sdk"]

TOML_TEMPLATE: str = f"""
[project]
name = "mock"
version = "1.0.0"
description = "Add your description here"
readme = "README.md"
authors = [
    {{ "name" = "me", "email" = "me@google.com" }}
]
requires-python = ">={sys.version_info.major}.{sys.version_info.minor}"
"""

TOML_CONTENT_WITH_DEV_DEPENDENCIES: str = (
    TOML_TEMPLATE
    + f"""
dependencies = ["{REQUIREMENT_LINE}"]

[dependency-groups]
dev = ["{DEV_DEPENDENCY_NAME}>=4.13.3"]
"""
)

TOML_CONTENT_WITHOUT_DEV_DEPENDENCIES: str = (
    TOML_TEMPLATE
    + f"""
dependencies = ["{REQUIREMENT_LINE}"]
"""
)


@pytest.mark.parametrize(
    ("flags", "expected"),
    [
        (
            {"f": True, "name": "TIPCommon", "files": ["1", "2"]},
            ["-f", "--name", "TIPCommon", "--files", "1", "2"],
        ),
        (
            {"a": True, "b": True},
            ["-a", "-b"],
        ),
        (
            {"verbose": True},
            ["--verbose"],
        ),
        (
            {"recursive": True, "dry_run": True},
            ["--recursive", "--dry-run"],
        ),
        (
            {},
            [],
        ),
        (
            {"flag": "value"},
            ["--flag", "value"],
        ),
        (
            {"r": True},
            ["-r"],
        ),
        (
            {"r": False},
            [],
        ),
        (
            {"recursive": False},
            [],
        ),
        (
            {"dryrun": True},
            ["--dryrun"],
        ),
    ],
)
def test_get_flags_to_command(flags: Mapping[str, str | bool], expected: list[str]) -> None:
    assert mp.core.unix.get_flags_to_command(**flags) == expected


def test_compile_integration_dependencies(tmp_path: Path) -> None:
    pyproject_toml_path: Path = tmp_path / mp.core.constants.PROJECT_FILE
    pyproject_toml_path.write_text(TOML_CONTENT_WITH_DEV_DEPENDENCIES, encoding="utf-8")
    requirements_path: Path = tmp_path / mp.core.constants.REQUIREMENTS_FILE
    assert not requirements_path.exists()

    mp.core.unix.compile_core_integration_dependencies(
        pyproject_toml_path.parent,
        requirements_path,
    )
    requirements: str = requirements_path.read_text(encoding="utf-8")

    assert requirements
    assert DEV_DEPENDENCY_NAME not in requirements


def test_compile_core_integration_dependencies_with_no_dev_does_not_fail(
    tmp_path: Path,
) -> None:
    pyproject_path: Path = tmp_path / mp.core.constants.PROJECT_FILE
    pyproject_path.write_text(
        TOML_CONTENT_WITHOUT_DEV_DEPENDENCIES,
        encoding="utf-8",
    )
    requirements_path: Path = tmp_path / mp.core.constants.REQUIREMENTS_FILE
    assert not requirements_path.exists()

    mp.core.unix.compile_core_integration_dependencies(
        pyproject_path.parent,
        requirements_path,
    )
    requirements: str = requirements_path.read_text(encoding="utf-8")

    assert requirements
    assert DEV_DEPENDENCY_NAME not in requirements


def test_download_wheels_from_requirements(tmp_path: Path) -> None:
    pyproject_toml: Path = tmp_path / mp.core.constants.PROJECT_FILE
    pyproject_toml.write_text(TOML_CONTENT_WITH_DEV_DEPENDENCIES, encoding="utf-8")

    requirements: Path = tmp_path / mp.core.constants.REQUIREMENTS_FILE
    mp.core.unix.compile_core_integration_dependencies(
        pyproject_toml.parent,
        requirements,
    )

    dependencies: Path = tmp_path / "dependencies"
    dependencies.mkdir()
    assert not list(dependencies.iterdir())

    mp.core.unix.download_wheels_from_requirements(tmp_path, requirements, dependencies)
    wheels: list[str] = [str(p) for p in dependencies.iterdir()]

    assert wheels
    assert DEV_DEPENDENCY_NAME not in wheels


@pytest.mark.parametrize(
    ("name", "version", "has_testing_dir", "expected"),
    [
        (TIPCOMMON_NAME, NEW_TIPCOMMON_VERSION, True, True),
        (TIPCOMMON_NAME, NEW_TIPCOMMON_VERSION, False, False),
        (TIPCOMMON_NAME, OLD_TIPCOMMON_VERSION, True, False),
        (ENVCOMMON_NAME, "1.0.0", True, False),
    ],
)
def test_should_add_integration_testing(
    tmp_path: Path, name: str, version: str, has_testing_dir: bool, expected: bool
) -> None:
    integration_path = tmp_path
    if has_testing_dir:
        (integration_path / mp.core.constants.TESTING_DIR).mkdir()

    result = mp.core.unix._should_add_integration_testing(name, version, integration_path)  # noqa: SLF001
    assert result is expected


def test_add_dependencies_to_toml(
    tmp_path: Path,
    mock_subprocess_run: MagicMock,
) -> None:
    """Test add_dependencies_to_toml with mocked dependencies."""
    requirements: Path = tmp_path / mp.core.constants.REQUIREMENTS_FILE

    resolved_deps = [REQUIREMENT_LINE]
    resolved_dev_deps = [
        *DEFAULT_DEV_DEPENDENCIES,
        PACKAGE_PATH.format(TIPCOMMON_NAME),
        PACKAGE_PATH.format(ENVCOMMON_NAME),
    ]

    with unittest.mock.patch(
        "mp.core.unix._resolve_dependencies",
        return_value=(resolved_deps, resolved_dev_deps),
    ):
        mp.core.unix.add_dependencies_to_toml(tmp_path, requirements)

        assert mock_subprocess_run.call_count == 3

        calls = mock_subprocess_run.call_args_list

        # Regular dependencies
        regular_deps_call_args = calls[0].args[0]
        assert REQUIREMENT_LINE in regular_deps_call_args
        assert "--group" not in regular_deps_call_args
        assert "--default-index" in regular_deps_call_args

        # VCS dev dependencies
        vcs_dev_deps_call_args = calls[1].args[0]
        assert "--group" in vcs_dev_deps_call_args
        assert "dev" in vcs_dev_deps_call_args
        assert any("git+" in arg for arg in vcs_dev_deps_call_args)

        # Other dev dependencies
        dev_deps_call_args = calls[2].args[0]
        assert "--group" in dev_deps_call_args
        assert "dev" in dev_deps_call_args
        assert set(resolved_dev_deps).issubset(dev_deps_call_args)


def test_init_python_project(tmp_path: Path) -> None:
    pyproject_toml: Path = tmp_path / mp.core.constants.PROJECT_FILE
    assert not pyproject_toml.exists()

    mp.core.unix.init_python_project(tmp_path)
    assert pyproject_toml.exists()

    with pytest.raises(mp.core.unix.FatalCommandError):
        mp.core.unix.init_python_project(tmp_path)


def test_init_python_project_if_not_exists(
    mock_get_marketplace_path: str,
    tmp_path: Path,
) -> None:
    with unittest.mock.patch(mock_get_marketplace_path, return_value=tmp_path):
        pyproject_toml: Path = tmp_path / mp.core.constants.PROJECT_FILE
        assert not pyproject_toml.exists()

        mp.core.unix.init_python_project_if_not_exists(tmp_path)
        assert pyproject_toml.exists()

        mp.core.unix.init_python_project_if_not_exists(tmp_path)
        assert pyproject_toml.exists()
