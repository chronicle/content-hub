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
    from collections.abc import Iterable
    from pathlib import Path

    from mp.core.custom_types import YamlFileContent


class Configurations(NamedTuple):
    only_pre_build: bool


DEF_FILE_NAME_KEY: str = "name"


def get_marketplace_paths_from_names(
    names: Iterable[str],
    marketplace_paths: Iterable[Path],
) -> set[Path]:
    """Retrieve existing marketplace paths from a list of names.

    Args:
        names: An iterable of names, where each name can be a string
            representing a file/directory name of integration or group.
        marketplace_paths: The base `Path` objects representing the
            integrations directories of the marketplace.

    Returns:
        A `set` of `Path` objects representing the paths that
        were found to exist within the `marketplace_path`.

    """
    results: set[Path] = set()
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


def load_integration_def(integration_path: pathlib.Path) -> YamlFileContent:
    """Load the integration definition file content.

    Returns:
        the integration definition content.

    Raises:
        FatalValidationError: if the integration definition file can't be loaded.

    """
    try:
        integration_def = integration_path / constants.DEFINITION_FILE
        return file_utils.load_yaml_file(integration_def)
    except Exception as e:
        msg: str = f"Failed to load integration def file: {e}"
        raise FatalValidationError(msg) from e


def load_components_defs(
    integration_path: pathlib.Path, *components: str
) -> dict[str, list[YamlFileContent]]:
    """Load component's definition files, organized by component type.

    Returns:
        a dict mapping component type to a list of each component's definition content.

    Raises:
        FatalValidationError: if any component definition files cannot be loaded.

    """
    valid_components: set[str] = {
        constants.ACTIONS_DIR,
        constants.CONNECTORS_DIR,
        constants.JOBS_DIR,
    }
    filtered_components: set[str] = set(components).intersection(valid_components)

    try:
        component_defs: dict[str, list[YamlFileContent]] = {}
        for component_dir_name in filtered_components:
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
