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
from typing import Any

import pytest
import toml

from mp.core.unix import NonFatalCommandError
from mp.validate.pre_build_validation.integrations.required_dependencies_validation import (
    RequiredDevDependenciesValidation,
)


def test_required_dependencies_present_success(temp_integration: Path) -> None:
    pyproject_content = {
        "dependency-groups": {
            "dev": ["soar-sdk>=1.0.0", "pytest>=7.0.0", "pytest-json-report==1.2.3"]
        }
    }
    _create_pyproject_toml(temp_integration, pyproject_content)
    RequiredDevDependenciesValidation.run(integration_path=temp_integration)


def test_required_dependencies_with_extra_success(temp_integration: Path) -> None:
    pyproject_content = {
        "dependency-groups": {
            "dev": ["soar-sdk", "pytest", "pytest-json-report", "black", "flake8"]
        }
    }
    _create_pyproject_toml(temp_integration, pyproject_content)
    RequiredDevDependenciesValidation.run(integration_path=temp_integration)


def test_missing_one_required_dependency_fail(temp_integration: Path) -> None:
    pyproject_content = {"dependency-groups": {"dev": ["soar-sdk", "pytest"]}}
    _create_pyproject_toml(temp_integration, pyproject_content)
    error_msg: str = (
        "Missing required development dependencies in pyproject.toml: pytest-json-report"
    )
    with pytest.raises(NonFatalCommandError, match=error_msg):
        RequiredDevDependenciesValidation.run(integration_path=temp_integration)


def test_missing_multiple_required_dependencies_fail(temp_integration: Path) -> None:
    pyproject_content = {"dependency-groups": {"dev": ["soar-sdk"]}}
    _create_pyproject_toml(temp_integration, pyproject_content)
    error_msg: str = (
        "Missing required development dependencies in pyproject.toml: pytest, pytest-json-report"
    )
    with pytest.raises(NonFatalCommandError, match=error_msg):
        RequiredDevDependenciesValidation.run(integration_path=temp_integration)


def test_missing_dev_dependencies_section_fail(temp_integration: Path) -> None:
    pyproject_content = {"dependency-groups": {}}
    _create_pyproject_toml(temp_integration, pyproject_content)
    error_msg: str = "Could not find \\[dev-dependencies]\ndev = \\[...] section in pyproject.toml."
    with pytest.raises(NonFatalCommandError, match=error_msg):
        RequiredDevDependenciesValidation.run(integration_path=temp_integration)


def _create_pyproject_toml(integration_path: Path, content: dict[str, Any]) -> None:
    pyproject_path = integration_path / "pyproject.toml"
    with Path.open(pyproject_path, "w") as f:
        f.write(toml.dumps(content))
