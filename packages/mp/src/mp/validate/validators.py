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

import dataclasses
from typing import TYPE_CHECKING

import mp.core.file_utils
from mp.core import constants
from mp.core.unix import NonFatalCommandError

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Callable

    from mp.core.custom_types import ActionName, ConnectorName, JobName, YamlFileContent


@dataclasses.dataclass(slots=True, frozen=True)
class IntegrationValidator:
    """Perform logical validation on an integration from its path."""

    integration_path: pathlib.Path
    _integration_def_content: YamlFileContent = dataclasses.field(init=False)
    _component_defs_content: dict[str, list[YamlFileContent]] = dataclasses.field(
        init=False,
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "_integration_def_content", self._load_integration_def())
        object.__setattr__(self, "_component_defs_content", self._load_components_defs())

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

    def run_all_validations(self) -> None:
        """Run all validation checks against the integration."""
        self.raise_error_if_custom()

    def raise_error_if_custom(self) -> None:
        """Raise an error if the integration or any of its components are custom.

        Raises:
            NonFatalCommandError: if the integration or any of its components are custom.

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
            raise NonFatalCommandError(msg)


@dataclasses.dataclass(slots=True, frozen=True)
class IntegrationParityValidator:
    path: pathlib.Path

    def validate_integration_components_parity(self) -> None:
        """Validate the components of the integration.

        This method ensures that all critical parts of the integration,
        including actions, connectors, jobs, and widgets,
        adhere to the required validation rules.
        Meaning there is parity between scripts and metadata files 1:1

        """
        self._validate_actions()
        self._validate_connectors()
        self._validate_jobs()
        self._validate_widgets()

    def _validate_actions(self) -> None:
        actions: pathlib.Path = self.path / constants.ACTIONS_DIR
        if actions.exists():
            _validate_script_metadata_parity(actions, ".py", constants.DEF_FILE_SUFFIX)

    def _validate_connectors(self) -> None:
        connectors: pathlib.Path = self.path / constants.CONNECTORS_DIR
        if connectors.exists():
            _validate_script_metadata_parity(
                directory=connectors,
                script_suffix=".py",
                metadata_suffix=constants.DEF_FILE_SUFFIX,
            )

    def _validate_jobs(self) -> None:
        jobs: pathlib.Path = self.path / constants.JOBS_DIR
        if jobs.exists():
            _validate_script_metadata_parity(jobs, ".py", constants.DEF_FILE_SUFFIX)

    def _validate_widgets(self) -> None:
        widgets: pathlib.Path = self.path / constants.WIDGETS_DIR
        if widgets.exists():
            _validate_script_metadata_parity(
                directory=widgets,
                script_suffix=".html",
                metadata_suffix=constants.DEF_FILE_SUFFIX,
            )


def _validate_script_metadata_parity(
    directory: pathlib.Path,
    script_suffix: str,
    metadata_suffix: str,
) -> None:
    _validate_matching_files(directory, script_suffix, metadata_suffix)
    _validate_matching_files(directory, metadata_suffix, script_suffix)


def _validate_matching_files(
    directory: pathlib.Path,
    primary_suffix: str,
    secondary_suffix: str,
) -> None:
    for file in directory.rglob(f"*{primary_suffix}"):
        if file.name == constants.PACKAGE_FILE:
            continue

        expected_file: pathlib.Path = file.with_suffix(secondary_suffix)
        if not expected_file.exists():
            msg: str = (
                f"The {directory.name} directory has a file '{file.name}' without a"
                f"  matching '{secondary_suffix}' file"
            )
            raise RuntimeError(msg)
