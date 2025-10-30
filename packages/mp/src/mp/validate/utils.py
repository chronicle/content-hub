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

import re
from typing import TYPE_CHECKING, NamedTuple

from mp.core import constants, file_utils
from mp.core.exceptions import FatalValidationError

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Callable, Iterable

    from mp.core.custom_types import YamlFileContent


class Configurations(NamedTuple):
    only_pre_build: bool


def get_marketplace_paths_from_names(
    names: Iterable[str],
    marketplace_paths: Iterable[pathlib.Path],
) -> set[pathlib.Path]:
    """Retrieve existing marketplace paths from a list of names.

    Args:
        names: An iterable of names, where each name can be a string
            representing a file/directory name of integration or group.
        marketplace_paths: The base `pathlib.Path` objects representing the
            integrations directories of the marketplace.

    Returns:
        A `set` of `pathlib.Path` objects representing the paths that
        were found to exist within the `marketplace_path`.

    """
    results: set[pathlib.Path] = set()
    for path in marketplace_paths:
        for n in names:
            if (p := path / n).exists():
                results.add(p)
    return results


def get_project_dependency_name(dependency_name: str) -> str:
    """Extract the dependency name from a version specifier string.

    Args:
        dependency_name: The full dependency string, which may include
            version constraints like 'requests>=2.25.1'.

    Returns:
        The clean dependency name without any version specifiers.

    """
    return re.split(r"[<>=]", dependency_name)[0]


def get_filtered_component_names(
    component_def: list[YamlFileContent],
    filter_fn: Callable[[YamlFileContent], bool],
) -> list[str]:
    """Get component names from a component directory that match a filter function.

    Returns:
        a list of the filtered component names.

    """
    return [d.get("name") for d in component_def if filter_fn(d)]


def load_integration_def(integration_path: pathlib.Path) -> YamlFileContent:
    """Load the integration definition file content.

    Returns:
        the integration definition content.

    Raises:
        FatalValidationError: if the integration definition file can't be loaded.

    """
    try:
        integration_def_path = integration_path / constants.DEFINITION_FILE
        return file_utils.load_yaml_file(integration_def_path)
    except Exception as e:
        msg: str = f"Failed to load integration def file: {e}"
        raise FatalValidationError(msg) from e


def load_components_defs(integration_path: pathlib.Path) -> dict[str, list[YamlFileContent]]:
    """Load all component's definition files, organized by component type.

    Returns:
        a dict mapping component type to a list of each component's definition content.

    Raises:
        FatalValidationError: if any component definition files cannot be loaded.

    """
    try:
        component_defs: dict[str, list[YamlFileContent]] = {}
        for component_dir_name in [
            constants.ACTIONS_DIR,
            constants.CONNECTORS_DIR,
            constants.JOBS_DIR,
        ]:
            component_dir: pathlib.Path = integration_path / component_dir_name
            if component_dir.is_dir():
                component_defs[component_dir_name] = [
                    file_utils.load_yaml_file(p)
                    for p in component_dir.glob(f"*{constants.DEF_FILE_SUFFIX}")
                ]
    except Exception as e:
        msg: str = f"Failed to load components def files: {e}"
        raise FatalValidationError(msg) from e
    else:
        return component_defs
