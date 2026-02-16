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
import zipfile
from contextlib import suppress
from pathlib import Path
from typing import NamedTuple

import rich
from packaging.version import Version

import mp.core.constants
from mp.core import config


class Dependencies(NamedTuple):
    """A tuple representing dependencies."""

    dependencies: list[str]
    dev_dependencies: list[str]


class DependencyResolutionResult(NamedTuple):
    """A tuple representing the resolved dependencies, and placeholders for missing local ones."""

    dependencies: Dependencies
    placeholders: Dependencies


class ProcessedPackage(NamedTuple):
    """Represents the outcome of processing a single package file."""

    matched_imports: set[str]
    dependencies: Dependencies
    placeholders: Dependencies
    env_common_to_remove: bool = False


MIN_TIP_COMMON_VERSION_DEPENDS_ON_ENVCOMMON: Version = Version("1.0.14")
MIN_RELEVANT_TIP_COMMON_VERSION_FOR_INTEGRATION_TESTING: Version = Version("2.0.0")
TIP_COMMON: str = "TIPCommon"
ENV_COMMON: str = "EnvironmentCommon"
INTEGRATION_TESTING: str = "integration_testing"
PACKAGE_FILE_PATTERN: str = r"^(?P<name>[^-]+)-(?P<version>[^-]+)-.*\.whl$"
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

    def get_dependencies(self) -> DependencyResolutionResult:
        """Get the dependencies of the integration.

        Returns:
            A DependencyResolutionResult object containing local and PyPI dependencies.

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

    def _resolve_dependencies(self, required_modules: set[str]) -> DependencyResolutionResult:
        deps_to_add: list[str] = []
        dev_deps_to_add: list[str] = []
        placeholder_deps, placeholder_dev_deps = [], []

        env_common_to_remove = False
        if TIP_COMMON in required_modules:
            required_modules.add(ENV_COMMON)

        dependencies_dir: Path = self.integration_path / mp.core.constants.OUT_DEPENDENCIES_DIR
        found_packages: set[str] = set()

        if dependencies_dir.is_dir():
            package_files = itertools.chain.from_iterable(
                dependencies_dir.glob(ext) for ext in PACAKGE_SUFFIXES
            )
            for package in package_files:
                result = self._process_package_file(package, required_modules)
                if not result:
                    continue

                found_packages.update(result.matched_imports)
                deps_to_add.extend(result.dependencies.dependencies)
                dev_deps_to_add.extend(result.dependencies.dev_dependencies)
                placeholder_deps.extend(result.placeholders.dependencies)
                if result.env_common_to_remove:
                    env_common_to_remove = True

        missing_packages: set[str] = required_modules.difference(found_packages)
        for missing_package in missing_packages:
            package_to_add = missing_package
            if package_to_add in mp.core.constants.SDK_DEPENDENCIES_INSTALL_NAMES:
                package_to_add = mp.core.constants.SDK_DEPENDENCIES_INSTALL_NAMES[package_to_add]
            deps_to_add.append(package_to_add)

        if env_common_to_remove:
            deps_to_add = [dep for dep in deps_to_add if not Path(dep).name.startswith(ENV_COMMON)]

        return DependencyResolutionResult(
            dependencies=Dependencies(deps_to_add, dev_deps_to_add),
            placeholders=Dependencies(placeholder_deps, placeholder_dev_deps),
        )

    def _process_package_file(
        self,
        package_path: Path,
        required_modules: set[str],
    ) -> ProcessedPackage | None:
        match = re.match(PACKAGE_FILE_PATTERN, package_path.name)
        if not match:
            return None

        package_install_name: str = match.group("name")
        version: str = match.group("version").replace("_", "-")

        provided_imports = _get_provided_imports(package_path).union({package_install_name})
        if package_install_name in mp.core.constants.SDK_DEPENDENCIES_MIN_VERSIONS:
            min_version = mp.core.constants.SDK_DEPENDENCIES_MIN_VERSIONS[package_install_name]
            if Version(version) < Version(min_version):
                version = min_version

        matched_imports = required_modules.intersection(provided_imports)

        if not matched_imports:
            return None

        deps_to_add, dev_deps_to_add = [], []
        placeholder_deps, placeholder_dev_deps = [], []
        env_common_to_remove = False

        if package_install_name in mp.core.constants.REPO_PACKAGES_CONFIG:
            if (
                package_install_name == TIP_COMMON
                and Version(version) < MIN_TIP_COMMON_VERSION_DEPENDS_ON_ENVCOMMON
                and ENV_COMMON in required_modules
            ):
                env_common_to_remove = True

            try:
                repo_packages: Dependencies = self._get_repo_package_dependencies(
                    package_install_name, version
                )
                deps_to_add.extend(repo_packages.dependencies)
                dev_deps_to_add.extend(repo_packages.dev_dependencies)
            except FileNotFoundError as e:
                # This dependency will be added as a placeholder comment
                placeholder_deps.append(f"{package_install_name}=={version}")
                rich.print(
                    f"[yellow]Warning:[/] Could not resolve local dependency "
                    f"{package_install_name}: {e}"
                )
        else:
            deps_to_add.append(f"{package_install_name}=={version}")
        return ProcessedPackage(
            matched_imports=matched_imports,
            dependencies=Dependencies(deps_to_add, dev_deps_to_add),
            placeholders=Dependencies(placeholder_deps, placeholder_dev_deps),
            env_common_to_remove=env_common_to_remove,
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
        wheels_dir: Path = self.local_packages_base_path / _get_package_wheels_dir(name)
        if not wheels_dir.is_dir():
            msg: str = f"Could not find local dependency directory: {wheels_dir}"
            raise FileNotFoundError(msg)

        package_file: Path = _find_package_file(wheels_dir, f"{name}-{version}")
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
                it_package_file: Path = _find_package_file(
                    integration_testing_version_dir, f"{INTEGRATION_TESTING}-{version}"
                )
                local_dev_deps_to_add.append(str(it_package_file))

        return Dependencies(local_deps_to_add, local_dev_deps_to_add)


def _find_package_file(package_dir: Path, wheel_name_prefix: str) -> Path:
    """Find a wheel or source distribution file in a directory.

    Returns:
        The path to the package file.

    Raises:
        FileNotFoundError: If no wheel or source distribution is found.

    """
    for extension in PACAKGE_SUFFIXES:
        for file in package_dir.glob(f"{wheel_name_prefix}{extension}"):
            return file

    msg: str = f"No wheel or source distribution found in {package_dir}"
    raise FileNotFoundError(msg)


def _get_package_wheels_dir(name: str) -> Path:
    package_dir_name: str = mp.core.constants.REPO_PACKAGES_CONFIG[name]
    return Path(package_dir_name) / "whls"


def _should_add_integration_testing(name: str, version: str) -> bool:
    return (
        name == TIP_COMMON
        and Version(version) >= MIN_RELEVANT_TIP_COMMON_VERSION_FOR_INTEGRATION_TESTING
    )


def _get_provided_imports(wheel_path: Path) -> set[str]:
    """Open a .whl file and read top_level.txt to find provided module names.

    Args:
        wheel_path: The path to the wheel file. Can also be a source distribution.

    Returns:
        A set of import names provided by the wheel, or an empty set if it cannot be read.

    """
    with (
        suppress(zipfile.BadZipFile, FileNotFoundError, IsADirectoryError),
        zipfile.ZipFile(wheel_path, "r") as z,
    ):
        for file_info in z.infolist():
            if file_info.filename.endswith(".dist-info/top_level.txt"):
                with z.open(file_info) as top_level_file:
                    content = top_level_file.read().decode("utf-8").strip()
                    return set(content.split())
    return set()
