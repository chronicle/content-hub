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

import dataclasses
import tomllib
from typing import TYPE_CHECKING, Any

from mp.core.unix import NonFatalCommandError
from mp.validate.utils import get_project_dependency_name

if TYPE_CHECKING:
    from pathlib import Path


@dataclasses.dataclass(slots=True, frozen=True)
class RequiredDevDependenciesValidation:
    name: str = "Required Dev Dependencies"

    @staticmethod
    def run(integration_path: Path) -> None:
        """Run the validation against the specified project.

        Args:
            integration_path: The root path of the project to validate.

        Raises:
            NonFatalCommandError: If the `pyproject.toml` file is not found,
                cannot be parsed, or is missing required dependencies.

        """
        error_msg: str
        pyproject_path: Path = integration_path / "pyproject.toml"

        with pyproject_path.open("rb") as f:
            pyproject_toml: dict[str, Any] = tomllib.load(f)

        required_dependencies: set[str] = {"soar-sdk", "pytest", "pytest-json-report"}

        try:
            dev_dependencies_section: list[str] = pyproject_toml["dependency-groups"]["dev"]
        except KeyError:
            error_msg = "Could not find [dev-dependencies]\ndev = [...] section in pyproject.toml."
            raise NonFatalCommandError(error_msg) from KeyError(error_msg)

        actual_dependencies: set = {
            get_project_dependency_name(dep) for dep in dev_dependencies_section
        }

        missing_dependencies: set[str] = required_dependencies.difference(actual_dependencies)

        if not missing_dependencies:
            return

        missing_deps: str = ", ".join(sorted(missing_dependencies))
        error_msg: str = (
            f"Missing required development dependencies in pyproject.toml: {missing_deps}"
        )
        raise NonFatalCommandError(error_msg) from KeyError(error_msg)
