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
import tomllib
import unittest.mock
from typing import TYPE_CHECKING, Any

import pytest

import mp.core.constants
import mp.core.unix

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

DEV_DEPENDENCY_NAME: str = "beautifulsoup4"
REQUIREMENT_LINE: str = "black>=24.10.0"
TIPCOMMON_NAME: str = "tipcommon"
ENVCOMMON_NAME: str = "environmentcommon"
INTEGRATION_TESTING_NAME: str = "integration-testing"
NEW_TIPCOMMON_VERSION: str = "2.0.2"
NEW_TIPCOMMON_LINE: str = f"{TIPCOMMON_NAME}=={NEW_TIPCOMMON_VERSION}"
OLD_TIPCOMMON_LINE: str = f"{TIPCOMMON_NAME}==1.0.10"
ENVCOMMON_LINE: str = f"{ENVCOMMON_NAME}==1.0.0"
INTEGRATION_TESTING_LINE: str = f"{INTEGRATION_TESTING_NAME}=={NEW_TIPCOMMON_VERSION}"
DEFAULT_INDEX_SECTION: list[dict[str, Any]] = [{"default": True, "url": "https://pypi.org/simple"}]
DEFAULT_DEV_DEPENDENCIES: list[str] = ["pytest", "pytest-json-report", "soar-sdk"]
DEFAULT_SOURCE_SECTION: dict[str, Any] = {
    "soar-sdk": {"git": "https://github.com/chronicle/soar-sdk.git"}
}
LOCAL_DEPS_NAMES: set[str] = {ENVCOMMON_NAME, TIPCOMMON_NAME}

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

TOML_CONTENT_WITH_LOCAL_DEPS: str = (
    TOML_TEMPLATE
    + f"""
dependencies = ['{ENVCOMMON_NAME}', '{TIPCOMMON_NAME}']
"""
)

TOML_CONTENT_WITHOUT_DEV_DEPENDENCIES: str = (
    TOML_TEMPLATE
    + f"""
dependencies = ["{REQUIREMENT_LINE}"]
"""
)

TOML_CONTENT_WITHOUT_DEPENDENCIES: str = (
    TOML_TEMPLATE
    + """
dependencies = []
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


def test_add_dependencies_to_toml(tmp_path: Path) -> None:
    pyproject_toml: Path = tmp_path / mp.core.constants.PROJECT_FILE
    pyproject_toml.write_text(TOML_CONTENT_WITHOUT_DEPENDENCIES, encoding="utf-8")
    requirements: Path = tmp_path / mp.core.constants.REQUIREMENTS_FILE
    requirements.write_text(REQUIREMENT_LINE, encoding="utf-8")

    mp.core.unix.add_dependencies_to_toml(tmp_path, requirements)
    toml_content: dict[str, Any] = tomllib.loads(pyproject_toml.read_text(encoding="utf-8"))

    toml_expected_content: dict[str, Any] = tomllib.loads(TOML_CONTENT_WITH_DEV_DEPENDENCIES)
    assert toml_content["project"] == toml_expected_content["project"]
    assert toml_content["tool"]["uv"]["index"] == DEFAULT_INDEX_SECTION
    for basic_dev_dep in DEFAULT_DEV_DEPENDENCIES:
        assert any(
            dep.startswith(basic_dev_dep) for dep in toml_content["dependency-groups"]["dev"]
        )


def test_add_dependencies_to_toml_with_integration_testing_required(tmp_path: Path) -> None:
    (tmp_path / mp.core.constants.TESTING_DIR).mkdir()
    pyproject_toml: Path = tmp_path / mp.core.constants.PROJECT_FILE
    pyproject_toml.write_text(TOML_CONTENT_WITHOUT_DEPENDENCIES, encoding="utf-8")
    requirements: Path = tmp_path / mp.core.constants.REQUIREMENTS_FILE
    requirements.write_text(f"{NEW_TIPCOMMON_LINE}\n{ENVCOMMON_LINE}", encoding="utf-8")

    mp.core.unix.add_dependencies_to_toml(tmp_path, requirements)
    toml_content: dict[str, Any] = tomllib.loads(pyproject_toml.read_text(encoding="utf-8"))

    toml_expected_content: dict[str, Any] = tomllib.loads(TOML_CONTENT_WITH_LOCAL_DEPS)
    assert toml_content["project"] == toml_expected_content["project"]
    assert toml_content["tool"]["uv"]["index"] == DEFAULT_INDEX_SECTION
    dev_deps: list[str] = [*DEFAULT_DEV_DEPENDENCIES, INTEGRATION_TESTING_NAME]
    for basic_dev_dep in dev_deps:
        assert any(
            dep.startswith(basic_dev_dep) for dep in toml_content["dependency-groups"]["dev"]
        )
    local_deps_with_integration_testing = LOCAL_DEPS_NAMES.union({INTEGRATION_TESTING_NAME})
    assert local_deps_with_integration_testing.issubset(
        toml_content["tool"]["uv"]["sources"].keys()
    )


def test_add_dependencies_to_toml_no_integration_testing_required(tmp_path: Path) -> None:
    pyproject_toml: Path = tmp_path / mp.core.constants.PROJECT_FILE
    pyproject_toml.write_text(TOML_CONTENT_WITHOUT_DEPENDENCIES, encoding="utf-8")
    requirements: Path = tmp_path / mp.core.constants.REQUIREMENTS_FILE
    requirements.write_text(f"{NEW_TIPCOMMON_LINE}\n{ENVCOMMON_LINE}", encoding="utf-8")

    mp.core.unix.add_dependencies_to_toml(tmp_path, requirements)
    toml_content: dict[str, Any] = tomllib.loads(pyproject_toml.read_text(encoding="utf-8"))

    toml_expected_content: dict[str, Any] = tomllib.loads(TOML_CONTENT_WITH_LOCAL_DEPS)
    assert toml_content["project"] == toml_expected_content["project"]
    assert toml_content["tool"]["uv"]["index"] == DEFAULT_INDEX_SECTION
    for basic_dev_dep in DEFAULT_DEV_DEPENDENCIES:
        assert any(
            dep.startswith(basic_dev_dep) for dep in toml_content["dependency-groups"]["dev"]
        )
    assert LOCAL_DEPS_NAMES.issubset(toml_content["tool"]["uv"]["sources"].keys())


def test_add_dependencies_to_toml_with_old_tipcommon(tmp_path: Path) -> None:
    (tmp_path / mp.core.constants.TESTING_DIR).mkdir()
    pyproject_toml: Path = tmp_path / mp.core.constants.PROJECT_FILE
    pyproject_toml.write_text(TOML_CONTENT_WITHOUT_DEPENDENCIES, encoding="utf-8")
    requirements: Path = tmp_path / mp.core.constants.REQUIREMENTS_FILE
    requirements.write_text(f"{OLD_TIPCOMMON_LINE}\n{ENVCOMMON_LINE}", encoding="utf-8")

    mp.core.unix.add_dependencies_to_toml(tmp_path, requirements)
    toml_content: dict[str, Any] = tomllib.loads(pyproject_toml.read_text(encoding="utf-8"))

    toml_expected_content: dict[str, Any] = tomllib.loads(TOML_CONTENT_WITH_LOCAL_DEPS)
    assert toml_content["project"] == toml_expected_content["project"]
    assert toml_content["tool"]["uv"]["index"] == DEFAULT_INDEX_SECTION
    for basic_dev_dep in DEFAULT_DEV_DEPENDENCIES:
        assert any(
            dep.startswith(basic_dev_dep) for dep in toml_content["dependency-groups"]["dev"]
        )
    assert LOCAL_DEPS_NAMES.issubset(toml_content["tool"]["uv"]["sources"].keys())


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
