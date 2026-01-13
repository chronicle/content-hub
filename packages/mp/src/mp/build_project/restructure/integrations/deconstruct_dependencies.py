"""Module for handling dependencies during integration deconstruction.

This module contains functions for identifying and resolving dependencies
from a built integration's files, preparing them to be added to the
deconstructed project's configuration.
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

import ast
import itertools
import re
import sys
from pathlib import Path
from typing import NamedTuple

import rich

import mp.core.constants
from mp.core import config


class Dependencies(NamedTuple):
    """A tuple representing dependencies."""

    dependencies: list[str]
    dev_dependencies: list[str]


MIN_RELEVANT_TIP_COMMON_VERSION: int = 2
TIP_COMMON: str = "TIPCommon"
ENV_COMMON: str = "EnvironmentCommon"
INTEGRATION_TESTING: str = "integration_testing"
# PEP 440 compliant regex for parsing package versions from filenames.
PACKAGE_FILE_PATTERN: str = (
    r"^([a-zA-Z0-9_.\-]+?)-("
    r"v?(?:[0-9]+!)?[0-9]+(?:\.[0-9]+)*"
    r"(?:[-._]?(?:a|b|c|rc|alpha|beta|pre|preview)[-._]?[0-9]*)?"
    r"(?:-[0-9]+|[-._]?(?:post|rev|r)[-._]?[0-9]*)?"
    r"(?:[-._]?dev[-._]?[0-9]*)?"
    r"(?:\+[a-z0-9]+(?:[-._][a-z0-9]+)*)?"
    r")"
)
PACAKGE_SUFFIXES: tuple[str, str] = ("*.whl", "*.tar.gz")


class DependencyDeconstructor:
    """Deconstructs dependencies for an integration."""

    def __init__(self, integration_path: Path) -> None:
        """Initialize the deconstructor.

        Args:
            integration_path: The path to the integration.

        """
        self.integration_path = integration_path
        self.local_packages_base_path = config.get_local_packages_path()

    def get_dependencies(self) -> Dependencies:
        """Get the dependencies of the integration.

        Returns:
            A Dependencies object.

        """
        imported_modules_names: set[str] = self._get_package_names_from_python_code()
        return self._resolve_dependencies(imported_modules_names)

    def _get_package_names_from_python_code(self) -> set[str]:
        imported_modules: set[str] = set()
        core_modules_path: Path = self.integration_path / mp.core.constants.OUT_MANAGERS_SCRIPTS_DIR
        manager_modules: set[str] = {p.stem for p in core_modules_path.glob("*.py")}
        for path in self.integration_path.rglob("*.py"):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    match node:
                        case ast.Import(names=names):
                            imported_modules.update(alias.name.split(".")[0] for alias in names)

                        case ast.ImportFrom(module=module) if module:
                            imported_modules.add(module.split(".")[0])

            except SyntaxError:
                rich.print(
                    f"[yellow]Warning:[/] Could not parse {path}, skipping for dependency analysis."
                )

        return {
            m
            for m in imported_modules
            if m
            not in manager_modules.union(mp.core.constants.SDK_MODULES, sys.stdlib_module_names)
        }

    def _resolve_dependencies(self, required_modules: set[str]) -> Dependencies:
        deps_to_add: list[str] = []
        dev_deps_to_add: list[str] = []
        if TIP_COMMON in required_modules:
            required_modules.add(ENV_COMMON)

        dependencies_dir: Path = self.integration_path / mp.core.constants.OUT_DEPENDENCIES_DIR
        found_packages: set[str] = set()

        if dependencies_dir.is_dir():
            package_files = itertools.chain.from_iterable(
                dependencies_dir.glob(ext) for ext in PACAKGE_SUFFIXES
            )
            for package in package_files:
                match = re.match(PACKAGE_FILE_PATTERN, package.name)
                if not match:
                    continue
                package_name: str = match.group(1).replace("_", "-")
                if package_name not in required_modules:
                    continue

                found_packages.add(package_name)
                version: str = match.group(2)
                if package_name in mp.core.constants.REPO_PACKAGES_CONFIG:
                    try:
                        repo_packages: Dependencies = self._get_repo_package_dependencies(
                            package_name, version
                        )
                        deps_to_add.extend(repo_packages.dependencies)
                        dev_deps_to_add.extend(repo_packages.dev_dependencies)
                    except FileNotFoundError as e:
                        rich.print(
                            f"[yellow]Warning:[/] Could not resolve local dependency "
                            f"{package_name}: {e}"
                        )
                else:
                    deps_to_add.append(f"{package_name}=={version}")

        missing_packages: set[str] = required_modules.difference(found_packages)
        deps_to_add.extend(missing_packages)

        return Dependencies(
            deps_to_add,
            dev_deps_to_add,
        )

    def _get_repo_package_dependencies(
        self,
        name: str,
        version: str,
    ) -> Dependencies:
        """Resolve a single local dependency.

        Returns:
            A Dependencies object.

        Raises:
            FileNotFoundError: If a local dependency's directory or wheel is not found.

        """
        version_dir: Path = self.local_packages_base_path / _resolve_version_dir(name, version)
        if not version_dir.is_dir():
            msg: str = f"Could not find local dependency directory: {version_dir}"
            raise FileNotFoundError(msg)

        package_file: Path = _find_package_file(version_dir)
        local_deps_to_add: list[str] = [str(package_file)]
        local_dev_deps_to_add: list[str] = []

        if _should_add_integration_testing(name, version):
            integration_testing_version_dir: Path = (
                self.local_packages_base_path
                / mp.core.constants.REPO_PACKAGES_CONFIG[INTEGRATION_TESTING]
            )
            if not integration_testing_version_dir.is_dir():
                rich.print(
                    f"[yellow]Warning:[/] integration_testing directory not found at "
                    f"{integration_testing_version_dir}"
                )
            else:
                try:
                    it_package_file: Path = _find_package_file(
                        integration_testing_version_dir, f"{INTEGRATION_TESTING}-{version}"
                    )
                    local_dev_deps_to_add.append(str(it_package_file))
                except FileNotFoundError as e:
                    rich.print(f"[yellow]Warning:[/] {e}")

        return Dependencies(local_deps_to_add, local_dev_deps_to_add)


def _find_package_file(package_dir: Path, version_prefix: str = "") -> Path:
    """Find a wheel or source distribution file in a directory.

    Returns:
        The path to the package file.

    Raises:
        FileNotFoundError: If no wheel or source distribution is found.

    """
    for extension in PACAKGE_SUFFIXES:
        for file in package_dir.glob(f"{version_prefix}{extension}"):
            return file

    msg: str = f"No wheel or source distribution found in {package_dir}"
    raise FileNotFoundError(msg)


def _resolve_version_dir(name: str, version: str) -> Path:
    package_dir_name: str = mp.core.constants.REPO_PACKAGES_CONFIG[name]
    version_dir_name: str = f"{name}-{version}"
    return Path(package_dir_name) / version_dir_name


def _should_add_integration_testing(name: str, version: str) -> bool:
    return (
        name == TIP_COMMON
        and int(version.lstrip("v").split(".")[0]) >= MIN_RELEVANT_TIP_COMMON_VERSION
    )
