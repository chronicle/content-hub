"""Core logic for building and deconstructing integration marketplaces.

This module defines the `Marketplace` class, which provides the functionality
to build and deconstruct integrations and groups of integrations within a
marketplace directory. It orchestrates the process of reading integration
definitions, restructuring their components, and generating the final
marketplace JSON file. It also handles the reverse process of deconstructing
built integrations back into their source structure.
"""

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

import multiprocessing
import shutil
from typing import TYPE_CHECKING

import rich

import mp.core.config
import mp.core.constants
import mp.core.file_utils
import mp.core.utils
from mp.core.data_models.integrations.integration import (
    BuiltFullDetails,
    BuiltIntegration,
    Integration,
)

from .post_build.integrations.full_details_json import write_full_details
from .post_build.integrations.marketplace_json import write_marketplace_json
from .restructure.integrations.deconstruct import DeconstructIntegration
from .restructure.integrations.integration import restructure_integration

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path

    from mp.core.custom_types import Products


class IntegrationsRepo:
    def __init__(self, integrations_dir: Path) -> None:
        """Class constructor.

        Args:
            integrations_dir: The path to a Content-Hub integrations folders
                and groups exist

        """
        self.name: str = integrations_dir.name
        self.paths: list[Path] = mp.core.file_utils.get_all_integrations_paths(self.name)

        for dir_name in self.paths:
            dir_name.mkdir(exist_ok=True, parents=True)

        self.out_dir: Path = mp.core.file_utils.create_or_get_out_integrations_dir() / self.name
        self.out_dir.mkdir(exist_ok=True)

    def write_marketplace_json(self) -> None:
        """Write the marketplace JSON file to the marketplace's out path."""
        write_marketplace_json(self.out_dir)

    def build(self) -> None:
        """Build all integrations and groups in the marketplace."""
        products: Products[set[Path]] = mp.core.file_utils.get_integrations_and_groups_from_paths(
            *self.paths
        )
        self.build_groups(products.groups)
        self.build_integrations(products.integrations)

    def build_groups(self, group_paths: Iterable[Path]) -> None:
        """Build all groups provided by `group_paths`.

        Args:
            group_paths: The paths of integrations to build

        """
        processes: int = mp.core.config.get_processes_number()
        with multiprocessing.Pool(processes=processes) as pool:
            pool.map(self.build_group, group_paths)

    def build_group(self, group_dir: Path) -> None:
        """Build a single group provided by `group_path`.

        Args:
            group_dir: The paths of the integration to build

        Raises:
            FileNotFoundError: when `group_dir` does not exist

        """
        if not group_dir.exists():
            msg: str = f"Invalid integration {group_dir}"
            raise FileNotFoundError(msg)

        self.build_integrations(group_dir.iterdir())

    def build_integrations(self, integration_paths: Iterable[Path]) -> None:
        """Build all integrations provided by `integration_paths`.

        Args:
            integration_paths: The paths of integrations to build

        """
        paths: Iterator[Path] = (
            p for p in integration_paths if p.exists() and mp.core.file_utils.is_integration(p)
        )
        processes: int = mp.core.config.get_processes_number()
        with multiprocessing.Pool(processes=processes) as pool:
            pool.map(self.build_integration, paths)

    def build_integration(self, integration_path: Path) -> None:
        """Build a single integration provided by `integration_path`.

        Args:
            integration_path: The paths of the integration to build

        Raises:
            FileNotFoundError: when `integration_path` does not exist

        """
        if not integration_path.exists():
            msg: str = f"Invalid integration {integration_path}"
            raise FileNotFoundError(msg)

        integration: Integration = self._get_integration_to_build(integration_path)
        self._build_integration(integration, integration_path)
        self._remove_project_files_from_built_out_path(integration.identifier)

    def _get_integration_to_build(self, integration_path: Path) -> Integration:
        if not mp.core.file_utils.is_non_built_integration(integration_path):
            rich.print(f"Integration {integration_path.name} is built")
            self._prepare_built_integration_for_build(integration_path)
            return Integration.from_built_path(integration_path)

        rich.print(f"Integration {integration_path.name} is not built")
        integration: Integration = Integration.from_non_built_path(integration_path)
        mp.core.file_utils.recreate_dir(self.out_dir / integration.identifier)
        return integration

    def _prepare_built_integration_for_build(self, integration_path: Path) -> None:
        integration_out_path: Path = self.out_dir / integration_path.name
        mp.core.file_utils.recreate_dir(integration_out_path)
        shutil.copytree(integration_path, integration_out_path, dirs_exist_ok=True)

    def _build_integration(
        self,
        integration: Integration,
        integration_path: Path,
    ) -> None:
        rich.print(f"---------- Building {integration_path.stem} ----------")
        integration_out_path: Path = self.out_dir / integration.identifier
        integration_out_path.mkdir(exist_ok=True)

        built: BuiltIntegration = integration.to_built()
        restructure_integration(built, integration_path, integration_out_path)
        _copy_python_version_file(integration_path, integration_out_path)

        full_details: BuiltFullDetails = integration.to_built_full_details()
        write_full_details(full_details, integration_out_path)

    def _remove_project_files_from_built_out_path(self, integration_id: str) -> None:
        rich.print("Removing unneeded files from out path")
        self._remove_project_files_from_out_path(integration_id)
        integration: Path = self.out_dir / integration_id
        mp.core.file_utils.remove_paths_if_exists(
            integration / mp.core.constants.TESTS_DIR,
            integration / mp.core.constants.PROJECT_FILE,
            integration / mp.core.constants.LOCK_FILE,
            integration / mp.core.constants.OUT_ACTION_SCRIPTS_DIR / mp.core.constants.PACKAGE_FILE,
            integration
            / mp.core.constants.OUT_CONNECTOR_SCRIPTS_DIR
            / mp.core.constants.PACKAGE_FILE,
            integration / mp.core.constants.OUT_JOB_SCRIPTS_DIR / mp.core.constants.PACKAGE_FILE,
            integration
            / mp.core.constants.OUT_MANAGERS_SCRIPTS_DIR
            / mp.core.constants.PACKAGE_FILE,
        )
        mp.core.file_utils.remove_rglobs_if_exists(
            *mp.core.constants.EXCLUDED_GLOBS,
            root=integration,
        )

    def deconstruct_integrations(self, integration_paths: Iterable[Path]) -> None:
        """Deconstruct all integrations provided by `integration_paths`.

        Args:
            integration_paths: The paths of integrations to deconstruct

        """
        paths: Iterator[Path] = (
            p for p in integration_paths if p.exists() and mp.core.file_utils.is_integration(p)
        )
        processes: int = mp.core.config.get_processes_number()
        with multiprocessing.Pool(processes=processes) as pool:
            pool.map(self.deconstruct_integration, paths)

    def deconstruct_integration(self, integration_path: Path) -> None:
        """Deconstruct a single integration provided by `integration_path`.

        Args:
            integration_path: The paths of the integration to deconstruct

        Raises:
            FileNotFoundError: when `integration_path` does not exist

        """
        if not integration_path.exists():
            msg: str = f"Invalid integration {integration_path}"
            raise FileNotFoundError(msg)

        out_name: str = mp.core.utils.str_to_snake_case(integration_path.name)
        integration_out_path: Path = self.out_dir / out_name
        integration_out_path.mkdir(exist_ok=True)
        self._deconstruct_integration(integration_path, integration_out_path)
        self._remove_project_files_from_out_path(out_name)

    def _deconstruct_integration(self, integration_path: Path, integration_out_path: Path) -> None:
        rich.print(f"---------- Deconstructing {integration_path.stem} ----------")
        if mp.core.file_utils.is_non_built_integration(integration_path):
            rich.print(f"Integration {integration_path.name} is deconstructed")
            mp.core.file_utils.recreate_dir(integration_out_path)
            shutil.copytree(integration_path, integration_out_path, dirs_exist_ok=True)
            Integration.from_non_built_path(integration_path)
            return

        rich.print(f"Integration {integration_path.name} is built")
        integration: Integration = Integration.from_built_path(integration_path)
        di: DeconstructIntegration = DeconstructIntegration(
            path=integration_path,
            out_path=integration_out_path,
            integration=integration,
        )
        di.deconstruct_integration_files()
        self._init_integration_project(di)

    def _init_integration_project(self, di: DeconstructIntegration) -> None:
        integration_out_path: Path = self.out_dir / mp.core.utils.str_to_snake_case(di.path.name)
        proj: Path = di.path / mp.core.constants.PROJECT_FILE
        if proj.exists():
            rich.print(f"Updating {mp.core.constants.PROJECT_FILE}")
            shutil.copyfile(proj, integration_out_path / mp.core.constants.PROJECT_FILE)
            di.update_pyproject()

        else:
            di.initiate_project()

    def _remove_project_files_from_out_path(self, integration_name: str) -> None:
        integration: Path = self.out_dir / integration_name
        mp.core.file_utils.remove_paths_if_exists(
            integration / mp.core.constants.REQUIREMENTS_FILE,
            integration / mp.core.constants.README_FILE,
            integration / mp.core.constants.INTEGRATION_VENV,
        )


def _copy_python_version_file(integration_path: Path, integration_out_path: Path) -> None:
    """Copy the .python-version file to the out path."""
    python_version_file: Path = integration_path / mp.core.constants.PYTHON_VERSION_FILE
    if python_version_file.exists():
        shutil.copy(python_version_file, integration_out_path)
