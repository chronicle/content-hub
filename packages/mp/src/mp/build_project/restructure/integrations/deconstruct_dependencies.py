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
import re
from typing import TYPE_CHECKING

import rich

import mp.core.constants
from mp.core import config

if TYPE_CHECKING:
    from pathlib import Path


PY3_WHEEL_FILE_SUFFIX: str = "-py3-none-any.whl"
MIN_RELEVANT_TIP_COMMON_VERSION: int = 2
TIP_COMMON: str = "TIPCommon"
INTEGRATION_TESTING: str = "integration_testing"
WHEEL_PATTERN: str = r"^([a-zA-Z0-9_.\-]+?)-([0-9][.0-9a-zA-Z]*)"


def _resolve_version_dir(name: str, version: str) -> str:
    package_dir_name: str = mp.core.constants.LOCAL_PACKAGES_CONFIG[name]
    version_dir_name: str = f"{name}-{version}"
    return f"{package_dir_name}/{version_dir_name}"


def _should_add_integration_testing(name: str, version: str, integration_path: Path) -> bool:
    is_relevant_tip_common_version: bool = (
        name == TIP_COMMON and int(version[0]) >= MIN_RELEVANT_TIP_COMMON_VERSION
    )
    has_testing_dir: bool = (integration_path / mp.core.constants.TESTING_DIR).is_dir()
    return is_relevant_tip_common_version and has_testing_dir


def _resolve_local_dependency(
    local_packages_base_path: Path,
    name: str,
    version: str,
    integration_path: Path,
) -> tuple[list[str], list[str]]:
    """Resolve a single local dependency.

    Returns:
        A tuple of lists: (regular dependency paths, dev dependency paths).

    Raises:
        FileNotFoundError: If a local dependency's directory or wheel is not found.

    """
    local_deps_to_add: list[str] = []
    local_dev_deps_to_add: list[str] = []

    version_dir: Path = local_packages_base_path / _resolve_version_dir(name, version)
    if not version_dir.is_dir():
        msg: str = f"Could not find local dependency directory: {version_dir}"
        raise FileNotFoundError(msg)

    try:
        wheel_file: Path = next(version_dir.glob("*.whl"))
        local_deps_to_add.append(str(wheel_file))
        if _should_add_integration_testing(name, version, integration_path):
            integration_testing_wheel_file_name: str = (
                f"{_resolve_version_dir(INTEGRATION_TESTING, version)}{PY3_WHEEL_FILE_SUFFIX}"
            )
            integration_testing_wheel: Path = (
                local_packages_base_path / integration_testing_wheel_file_name
            )
            local_dev_deps_to_add.append(str(integration_testing_wheel))
    except StopIteration:
        msg: str = f"No wheel file found in {version_dir}"
        raise FileNotFoundError(msg) from None
    return local_deps_to_add, local_dev_deps_to_add


def _resolve_packages_names(integration_path: Path) -> set[str]:
    imported_modules: set[str] = set()
    core_modules_path: Path = integration_path / mp.core.constants.OUT_MANAGERS_SCRIPTS_DIR
    manager_modules: set[str] = {p.stem for p in core_modules_path.rglob("*.py")}
    for path in integration_path.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported_modules.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_modules.add(node.module.split(".")[0])
        except SyntaxError:
            rich.print(
                f"[yellow]Warning:[/] Could not parse {path}, skipping for dependency analysis."
            )

    return {
        m for m in imported_modules if m not in manager_modules.union(mp.core.constants.SDK_MODULES)
    }


def _resolve_dependencies(
    integration_path: Path, imported_modules: set[str]
) -> tuple[list[str], list[str]]:
    deps_to_add: list[str] = []
    dev_deps_to_add: list[str] = []
    dependencies_dir: Path = integration_path / mp.core.constants.OUT_DEPENDENCIES_DIR
    if not dependencies_dir.is_dir():
        return [], []
    local_packages_base_path: Path = config.get_local_packages_path()
    for wheel in dependencies_dir.glob("*.whl"):
        match = re.match(WHEEL_PATTERN, wheel.name)
        if not match:
            continue
        package_name: str = match.group(1).replace("_", "-")
        version: str = match.group(2)
        if package_name in imported_modules:
            if package_name in mp.core.constants.LOCAL_PACKAGES_CONFIG:
                try:
                    (
                        local_deps,
                        local_dev_deps,
                    ) = _resolve_local_dependency(
                        local_packages_base_path,
                        package_name,
                        version,
                        integration_path,
                    )
                    deps_to_add.extend(local_deps)
                    dev_deps_to_add.extend(local_dev_deps)
                except FileNotFoundError as e:
                    rich.print(
                        f"[yellow]Warning:[/] Could not resolve local dependency "
                        f"{package_name}: {e}"
                    )
            else:
                deps_to_add.append(f"{package_name}=={version}")
    return (
        deps_to_add,
        dev_deps_to_add,
    )


def get_dependencies(
    integration_path: Path,
) -> tuple[list[str], list[str]]:
    """Get the dependencies of the integration by parsing its Python files.

    Returns:
        A tuple of two lists: the first contains the regular dependencies, and the
        second contains the dev dependencies.

    """
    imported_modules_names: set[str] = _resolve_packages_names(integration_path)
    return _resolve_dependencies(integration_path, imported_modules_names)
