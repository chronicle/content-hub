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

import dataclasses
import tomllib
from typing import TYPE_CHECKING

import yaml

from mp.core import constants
from mp.core.exceptions import NonFatalValidationError

if TYPE_CHECKING:
    from pathlib import Path


@dataclasses.dataclass(slots=True, frozen=True)
class IntegrationDescriptionValidation:
    """Validate description fields for integrations and their action parameters."""

    name: str = "Integration Description Validation"

    @staticmethod
    def run(path: Path) -> None:
        """Run validation for integration and action parameter descriptions.

        Args:
            path: The path of the integration to validate.

        Raises:
            NonFatalValidationError: If any description is missing or empty.

        """
        errors: list[str] = []

        pyproject_path = path / constants.PROJECT_FILE
        if pyproject_path.exists():
            data = None
            try:
                with pyproject_path.open("rb") as f:
                    data = tomllib.load(f)
            except (tomllib.TOMLDecodeError, OSError):
                # Skip if we can't parse it, let other validations handle it
                pass

            if data is not None:
                project = data.get("project")
                if not isinstance(project, dict):
                    errors.append(f"Integration is missing the 'project' section in {constants.PROJECT_FILE}.")
                elif "description" not in project:
                    errors.append(f"Integration is missing the 'description' field in {constants.PROJECT_FILE}.")
                else:
                    description = project.get("description")
                    if not isinstance(description, str) or not description.strip():
                        errors.append(f"Integration has an empty 'description' field in {constants.PROJECT_FILE}.")

        # 2. Check Action Parameter Descriptions
        actions_dir = path / constants.ACTIONS_DIR
        if actions_dir.exists() and actions_dir.is_dir():
            for action_file in actions_dir.rglob(f"*{constants.YAML_SUFFIX}"):
                _validate_action_file(action_file, errors)

        if errors:
            raise NonFatalValidationError("\n".join(errors))


def _validate_action_file(action_file: Path, errors: list[str]) -> None:
    """Validate parameters in a single action YAML file.

    Args:
        action_file: Path to the action YAML file.
        errors: List to accumulate error messages.

    """
    try:
        action_data = yaml.safe_load(action_file.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        # Skip if we can't parse or read it, let other checks handle it
        return

    if not action_data or not isinstance(action_data, dict):
        return

    parameters = action_data.get("parameters")
    if not isinstance(parameters, list) or not parameters:
        return

    for param in parameters:
        if not isinstance(param, dict):
            continue
        param_name = param.get("name", "Unknown")
        if "description" not in param:
            errors.append(f"Action '{action_file.stem}' parameter '{param_name}' is missing 'description' field.")
        else:
            param_desc = param.get("description")
            if not isinstance(param_desc, str) or not param_desc.strip():
                errors.append(f"Action '{action_file.stem}' parameter '{param_name}' has an empty 'description' field.")
