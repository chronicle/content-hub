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

import unittest.mock
import zipfile
from typing import TYPE_CHECKING

import pytest

import mp.core.constants
from mp.build_project.restructure.integrations.deconstruct_dependencies import (
    Dependencies,
    DependencyDeconstructor,
    _should_add_integration_testing,  # noqa: PLC2701
)

if TYPE_CHECKING:
    from pathlib import Path


def _create_dummy_python_file(base_path: Path, content: str, filename: str = "main.py") -> None:
    (base_path / filename).write_text(content)


def _create_dependencies_dir(base_path: Path) -> Path:
    dependencies_dir = base_path / mp.core.constants.OUT_DEPENDENCIES_DIR
    dependencies_dir.mkdir()
    return dependencies_dir


def test_get_dependencies_with_local_and_remote(tmp_path: Path) -> None:
    """Test get_dependencies with a mix of local and remote packages."""
    _create_dummy_python_file(tmp_path, "import requests\nimport TIPCommon")
    _create_dummy_python_file(tmp_path, "from EnvironmentCommon import function", "utils.py")
    dependencies_dir = _create_dependencies_dir(tmp_path)
    (dependencies_dir / "requests-2.25.1-py3-none-any.whl").touch()
    (dependencies_dir / "TIPCommon-2.0.2-py3-none-any.whl").touch()
    (dependencies_dir / "EnvironmentCommon-1.0.0-py3-none-any.whl").touch()

    # Mock local package resolution
    with unittest.mock.patch(
        "mp.build_project.restructure.integrations.deconstruct_dependencies.DependencyDeconstructor._get_repo_package_dependencies"
    ) as mock_resolve:

        def mock_resolver(
            name: str,
            version: str,
        ) -> Dependencies:
            if name == "TIPCommon":
                return Dependencies(
                    dependencies=["path/to/TIPCommon.whl"],
                    dev_dependencies=["path/to/integration-testing.whl"],
                )
            if name == "EnvironmentCommon":
                return Dependencies(
                    dependencies=["path/to/EnvironmentCommon.whl"], dev_dependencies=[]
                )
            return Dependencies(dependencies=[], dev_dependencies=[])

        mock_resolve.side_effect = mock_resolver

        dependencies: Dependencies = DependencyDeconstructor(tmp_path).get_dependencies()

        assert "requests==2.25.1" in dependencies.dependencies
        assert "path/to/TIPCommon.whl" in dependencies.dependencies
        assert "path/to/EnvironmentCommon.whl" in dependencies.dependencies
        assert "path/to/integration-testing.whl" in dependencies.dev_dependencies


def test_get_dependencies_with_no_dependencies(tmp_path: Path) -> None:
    """Test get_dependencies when there are no dependencies."""
    _create_dummy_python_file(tmp_path, "print('hello')")
    _create_dependencies_dir(tmp_path)
    deps, dev_deps = DependencyDeconstructor(tmp_path).get_dependencies()
    assert not deps
    assert not dev_deps


def test_get_dependencies_ignores_sdk_and_core_modules(tmp_path: Path) -> None:
    """Test that get_dependencies ignores SDK and core modules."""
    _create_dummy_python_file(tmp_path, "import SiemplifyAction\nimport core_module")

    # Create dummy core module file
    core_modules_dir = tmp_path / mp.core.constants.OUT_MANAGERS_SCRIPTS_DIR
    core_modules_dir.mkdir()
    (core_modules_dir / "core_module.py").touch()

    deps, dev_deps = DependencyDeconstructor(tmp_path).get_dependencies()

    assert not deps
    assert not dev_deps


def test_get_dependencies_ignores_builtin_modules(tmp_path: Path) -> None:
    """Test that get_dependencies ignores builtin modules."""
    _create_dummy_python_file(tmp_path, "import sys\nimport os")
    _create_dependencies_dir(tmp_path)

    deps, dev_deps = DependencyDeconstructor(tmp_path).get_dependencies()

    assert not deps
    assert not dev_deps


def test_get_dependencies_includes_envcommon_when_tipcommon_exists(tmp_path: Path) -> None:
    """Test that all wheels in the dependencies dir are added, even if not imported."""
    _create_dummy_python_file(tmp_path, "import TIPCommon")
    dependencies_dir = _create_dependencies_dir(tmp_path)
    (dependencies_dir / "TIPCommon-2.0.2-py3-none-any.whl").touch()
    (dependencies_dir / "EnvironmentCommon-1.0.0-py3-none-any.whl").touch()

    with unittest.mock.patch(
        "mp.build_project.restructure.integrations.deconstruct_dependencies.DependencyDeconstructor._get_repo_package_dependencies"
    ) as mock_resolve:

        def mock_resolver(name: str, version: str) -> Dependencies:
            if name == "TIPCommon":
                return Dependencies(
                    dependencies=["path/to/TIPCommon.whl"],
                    dev_dependencies=["path/to/integration-testing.whl"],
                )
            if name == "EnvironmentCommon":
                return Dependencies(
                    dependencies=["path/to/EnvironmentCommon.whl"], dev_dependencies=[]
                )
            return Dependencies(dependencies=[], dev_dependencies=[])

        mock_resolve.side_effect = mock_resolver
        dependencies = DependencyDeconstructor(tmp_path).get_dependencies()
        assert "path/to/EnvironmentCommon.whl" in dependencies.dependencies


def test_get_dependencies_with_mismatched_import_and_package_name(tmp_path: Path) -> None:
    """Test dependency resolution when import name differs from package name
    (e.g., yaml vs PyYAML).
    """
    _create_dummy_python_file(tmp_path, "import yaml")
    dependencies_dir = _create_dependencies_dir(tmp_path)
    wheel_path = dependencies_dir / "PyYAML-6.0-cp39-cp39-manylinux_2_17_x86_64.whl"

    # Create a valid zip file (wheel) with a top_level.txt
    with zipfile.ZipFile(wheel_path, "w") as zf:
        dist_info_dir = "PyYAML-6.0.dist-info/"
        # The top_level.txt file tells pip what top-level modules are installed.
        zf.writestr(f"{dist_info_dir}top_level.txt", "yaml")

    # Mock local package resolution to return nothing for this package
    with unittest.mock.patch(
        "mp.build_project.restructure.integrations.deconstruct_dependencies.DependencyDeconstructor._get_repo_package_dependencies",
        return_value=Dependencies(dependencies=[], dev_dependencies=[]),
    ):
        dependencies = DependencyDeconstructor(tmp_path).get_dependencies()

        assert "PyYAML==6.0" in dependencies.dependencies


@pytest.mark.parametrize(
    ("name", "version", "expected"),
    [
        ("TIPCommon", "2.0.2", True),
        ("TIPCommon", "1.0.10", False),
    ],
)
def test_should_add_integration_testing(
    tmp_path: Path, name: str, version: str, expected: bool
) -> None:
    """Test the logic for when to add the integration-testing wheel."""

    result = _should_add_integration_testing(name, version)
    assert result is expected
