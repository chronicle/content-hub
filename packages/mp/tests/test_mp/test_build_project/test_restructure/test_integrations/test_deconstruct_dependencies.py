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
from typing import TYPE_CHECKING

import pytest

import mp.core.constants
from mp.build_project.restructure.integrations.deconstruct_dependencies import (
    _should_add_integration_testing,  # noqa: PLC2701
    get_dependencies,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_get_dependencies_with_local_and_remote(tmp_path: Path) -> None:
    """Test get_dependencies with a mix of local and remote packages."""
    # Create dummy python files with imports
    (tmp_path / "main.py").write_text("import requests\nimport TIPCommon")
    (tmp_path / "utils.py").write_text("from EnvironmentCommon import function")

    # Create dummy wheel files
    dependencies_dir = tmp_path / mp.core.constants.OUT_DEPENDENCIES_DIR
    dependencies_dir.mkdir()
    (dependencies_dir / "requests-2.25.1-py3-none-any.whl").touch()
    (dependencies_dir / "TIPCommon-2.0.2-py3-none-any.whl").touch()
    (dependencies_dir / "EnvironmentCommon-1.0.0-py3-none-any.whl").touch()

    # Mock local package resolution
    with unittest.mock.patch(
        "mp.build_project.restructure.integrations.deconstruct_dependencies._resolve_local_dependency"
    ) as mock_resolve:
        mock_resolve.side_effect = [
            (["path/to/TIPCommon.whl"], ["path/to/integration-testing.whl"]),
            (["path/to/enironmentvcommon.whl"], []),
        ]

        def mock_resolver(
            local_path: Path, name: str, version: str, integration_p: Path
        ) -> tuple[list[str], list[str]]:
            if name == "TIPCommon":
                return ["path/to/TIPCommon.whl"], ["path/to/integration-testing.whl"]
            if name == "EnvironmentCommon":
                return ["path/to/EnvironmentCommon.whl"], []
            return [], []

        mock_resolve.side_effect = mock_resolver

        deps, dev_deps = get_dependencies(tmp_path)

        assert "requests==2.25.1" in deps
        assert "path/to/TIPCommon.whl" in deps
        assert "path/to/EnvironmentCommon.whl" in deps
        assert "path/to/integration-testing.whl" in dev_deps


def test_get_dependencies_with_no_dependencies(tmp_path: Path) -> None:
    """Test get_dependencies when there are no dependencies."""
    (tmp_path / "main.py").write_text("print('hello')")
    deps, dev_deps = get_dependencies(tmp_path)
    assert not deps
    assert not dev_deps


def test_get_dependencies_ignores_sdk_and_core_modules(tmp_path: Path) -> None:
    """Test that get_dependencies ignores SDK and core modules."""
    # Create dummy python files with imports
    (tmp_path / "main.py").write_text("import SiemplifyAction\nimport core_module")

    # Create dummy core module file
    core_modules_dir = tmp_path / mp.core.constants.OUT_MANAGERS_SCRIPTS_DIR
    core_modules_dir.mkdir()
    (core_modules_dir / "core_module.py").touch()

    deps, dev_deps = get_dependencies(tmp_path)

    assert not deps
    assert not dev_deps


@pytest.mark.parametrize(
    ("name", "version", "has_testing_dir", "expected"),
    [
        ("TIPCommon", "2.0.2", True, True),
        ("TIPCommon", "2.0.2", False, False),
        ("TIPCommon", "1.0.10", True, False),
        ("EnvironmentCommon", "1.0.0", True, False),
    ],
)
def test_should_add_integration_testing(
    tmp_path: Path, name: str, version: str, has_testing_dir: bool, expected: bool
) -> None:
    """Test the logic for when to add the integration-testing wheel."""
    if has_testing_dir:
        (tmp_path / mp.core.constants.TESTING_DIR).mkdir()

    result = _should_add_integration_testing(name, version, tmp_path)
    assert result is expected
