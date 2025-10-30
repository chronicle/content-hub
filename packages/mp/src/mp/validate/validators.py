"""Module for common, reusable validation classes."""

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

import mp.core.file_utils
from mp.core import constants
from mp.core.exceptions import FatalValidationError, NonFatalValidationError

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Callable

    from mp.core.custom_types import ActionName, ConnectorName, JobName, YamlFileContent


class IntegrationValidator:
    """Perform logical validation on an integration from its path."""

    def __init__(self, integration_path: pathlib.Path) -> None:
        """Initialize the validator and load definition files.

        Args:
            integration_path: The path to the integration directory.

        Raises:
            FatalValidationError: If failed to load files

        """
        self.integration_path: pathlib.Path = integration_path
        try:
            self._integration_def_content: YamlFileContent = self._load_integration_def()
            self._component_defs_content: dict[str, list[YamlFileContent]] = (
                self._load_components_defs()
            )
        except Exception as e:
            msg: str = f"Failed to initialize IntegrationValidator: {e}"
            raise FatalValidationError(msg) from e

    def _load_integration_def(self) -> YamlFileContent:
        """Load the integration definition file content.

        Returns:
            the integration definition content.

        """
        integration_def_path = self.integration_path / constants.DEFINITION_FILE
        return mp.core.file_utils.load_yaml_file(integration_def_path)

    def _load_components_defs(self) -> dict[str, list[YamlFileContent]]:
        """Load all component's definition files, organized by component type.

        Returns:
            a dict mapping component type to a list of each component's definition content.

        """
        component_defs: dict[str, list[YamlFileContent]] = {}
        for component_dir_name in [
            constants.ACTIONS_DIR,
            constants.CONNECTORS_DIR,
            constants.JOBS_DIR,
        ]:
            component_dir: pathlib.Path = self.integration_path / component_dir_name
            if component_dir.is_dir():
                component_defs[component_dir_name] = [
                    mp.core.file_utils.load_yaml_file(p)
                    for p in component_dir.glob(f"*{constants.DEF_FILE_SUFFIX}")
                ]
        return component_defs

    def _get_filtered_component_names(
        self,
        component_dir_name: str,
        filter_fn: Callable[[YamlFileContent], bool],
    ) -> list[str]:
        """Get component names from a component directory that match a filter function.

        Returns:
            a list of the filtered component names.

        """
        component_def: list[YamlFileContent] = self._component_defs_content.get(
            component_dir_name, []
        )
        return [d.get("name") for d in component_def if filter_fn(d)]

    @staticmethod
    def _is_custom(yaml_content: YamlFileContent) -> bool:
        """Filter function to check if a component is custom.

        Returns:
            True if the component is custom.

        """
        return yaml_content.get("is_custom", False)

    def raise_error_if_custom(self) -> None:
        """Raise an error if the integration or any of its components are custom.

        Raises:
            NonFatalValidationError: if the integration or any of its components are custom.

        """
        is_integration_custom: bool = self._is_custom(self._integration_def_content)

        custom_actions: list[ActionName] = self._get_filtered_component_names(
            constants.ACTIONS_DIR, self._is_custom
        )
        custom_connectors: list[ConnectorName] = self._get_filtered_component_names(
            constants.CONNECTORS_DIR, self._is_custom
        )
        custom_jobs: list[JobName] = self._get_filtered_component_names(
            constants.JOBS_DIR, self._is_custom
        )

        if is_integration_custom or custom_actions or custom_connectors or custom_jobs:
            msg = (
                f"Integration '{self.integration_path.name}' contains custom components:"
                f"\n  - Is integration custom: {is_integration_custom}"
                f"\n  - Custom actions: {', '.join(custom_actions) or 'None'}"
                f"\n  - Custom connectors: {', '.join(custom_connectors) or 'None'}"
                f"\n  - Custom jobs: {', '.join(custom_jobs) or 'None'}"
            )
            raise NonFatalValidationError(msg)
