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

import asyncio
import sys
import tomllib
import unittest.mock
from typing import TYPE_CHECKING

import pytest

import mp.core.constants
import mp.core.unix

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

DEV_DEPENDENCY_NAME: str = "beautifulsoup4"
REQUIREMENT_LINE: str = "black>=24.10.0"
TOML_CONTENT_WITH_DEV_DEPENDENCIES: str = f"""
[project]
name = "mock"
version = "1.0.0"
description = "Add your description here"
readme = "README.md"
authors = [
    {{ name = "me", email = "me@google.com" }}
]
requires-python = ">={sys.version_info.major}.{sys.version_info.minor}"
dependencies = ["{REQUIREMENT_LINE}"]

[dependency-groups]
dev = ["{DEV_DEPENDENCY_NAME}>=4.13.3"]
"""
TOML_CONTENT_WITHOUT_DEV_DEPENDENCIES: str = f"""
[project]
name = "mock"
version = "1.0.0"
description = "Add your description here"
readme = "README.md"
authors = [
    {{ name = "me", email = "me@google.com" }}
]
requires-python = ">={sys.version_info.major}.{sys.version_info.minor}"
dependencies = ["{REQUIREMENT_LINE}"]
"""
TOML_CONTENT_WITHOUT_DEPENDENCIES: str = f"""
[project]
name = "mock"
version = "1.0.0"
description = "Add your description here"
readme = "README.md"
authors = [
    {{ name = "me", email = "me@google.com" }}
]
requires-python = ">={sys.version_info.major}.{sys.version_info.minor}"
dependencies = []
"""


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

    asyncio.run(
        mp.core.unix.download_wheels_from_requirements(tmp_path, requirements, dependencies)
    )
    wheels: list[str] = [str(p) for p in dependencies.iterdir()]

    assert wheels
    assert DEV_DEPENDENCY_NAME not in wheels


def test_add_dependencies_to_toml(tmp_path: Path) -> None:
    pyproject_toml: Path = tmp_path / mp.core.constants.PROJECT_FILE
    pyproject_toml.write_text(TOML_CONTENT_WITHOUT_DEPENDENCIES, encoding="utf-8")
    requirements: Path = tmp_path / mp.core.constants.REQUIREMENTS_FILE
    requirements.write_text(REQUIREMENT_LINE, encoding="utf-8")

    mp.core.unix.add_dependencies_to_toml(tmp_path, requirements)
    toml_content: str = pyproject_toml.read_text(encoding="utf-8")

    assert tomllib.loads(toml_content) == tomllib.loads(
        TOML_CONTENT_WITHOUT_DEV_DEPENDENCIES,
    )


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
