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

from typing import TYPE_CHECKING

from pydantic import dataclasses

from mp.core import constants
from mp.core.exceptions import NonFatalValidationError
from mp.core.utils import filter_and_map_yaml_files
from mp.validate.utils import (
    extract_name,
    load_components_defs,
    load_integration_def,
)

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.custom_types import ActionName, ConnectorName, JobName, YamlFileContent


@dataclasses.dataclass(slots=True, frozen=True)
class NoCustomComponentsInIntegrationValidation:
    name: str = "Custom Components Validation"

    @staticmethod
    def run(validation_path: Path) -> None:
        """Check if the integration or its components are marked as custom.

        Args:
            validation_path: The path of the integration to validate.

        Raises:
            NonFatalValidationError: If the integration or its components are marked as custom.

        """
        integration_def: YamlFileContent = load_integration_def(validation_path)
        components: list[str] = [
            constants.ACTIONS_DIR,
            constants.JOBS_DIR,
            constants.CONNECTORS_DIR,
        ]
        component_defs: dict[str, list[YamlFileContent]] = load_components_defs(
            validation_path, *components
        )

        is_integration_custom: bool = _is_custom(integration_def)

        custom_actions: list[ActionName] = filter_and_map_yaml_files(
            component_defs.get(constants.ACTIONS_DIR, []), _is_custom, extract_name
        )
        custom_connectors: list[ConnectorName] = filter_and_map_yaml_files(
            component_defs.get(constants.CONNECTORS_DIR, []), _is_custom, extract_name
        )
        custom_jobs: list[JobName] = filter_and_map_yaml_files(
            component_defs.get(constants.JOBS_DIR, []), _is_custom, extract_name
        )

        if is_integration_custom or custom_actions or custom_connectors or custom_jobs:
            msg = (
                f"Integration '{validation_path.name}' contains custom components:"
                f"\n  - Is integration custom: {is_integration_custom}"
                f"\n  - Custom actions: {', '.join(custom_actions) or 'None'}"
                f"\n  - Custom connectors: {', '.join(custom_connectors) or 'None'}"
                f"\n  - Custom jobs: {', '.join(custom_jobs) or 'None'}"
            )
            raise NonFatalValidationError(msg)


def _is_custom(yaml_content: YamlFileContent) -> bool:
    """Filter function to check if a component is custom.

    Returns:
        True if the component is custom.

    """
    return yaml_content.get("is_custom", False)
