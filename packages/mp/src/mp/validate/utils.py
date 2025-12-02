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
from mp.core.data_models.integrations.script.parameter import ScriptParamType
from mp.core.exceptions import FatalValidationError

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from mp.core.custom_types import ActionName, ConnectorName, JobName, YamlFileContent


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


def load_integration_def(integration_path: Path) -> YamlFileContent:
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
    integration_path: Path, *components: str
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
            component_dir: Path = integration_path / component_dir_name
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


def extract_name(yaml_content: YamlFileContent) -> ActionName | JobName | ConnectorName:
    """Extract the component's name from it's YAML file.

    Returns:
        the component's name, or `None` if it cannot be extracted.

    """
    return yaml_content.get(DEF_FILE_NAME_KEY)


def validate_ssl_parameter_from_yaml(yaml_content: YamlFileContent) -> str | None:
    """Filter function to check if a component has a valid SSL parameter or is in excluded list.

    Returns:
        An error message if the component's ssl parameter is not valid, else None.

    """
    return _validate_ssl_parameter(yaml_content["name"], yaml_content.get("parameters", []))


def _validate_ssl_parameter(
    script_name: str,
    parameters: list[YamlFileContent],
) -> str | None:
    """Validate the Verify SSL parameter.

    Validates the presence and correctness of a 'Verify SSL' parameter in the provided
    integration or connector's parameters. Ensures that the parameter exists, is of the
    correct type, and has the correct default value unless the script is explicitly
    excluded from verification.

    Args:
        script_name: The name of the integration or connector script.
        parameters: collection of parameters associated with the component.

    Returns:
        An error message if the parameter is invalid, else None.

    """
    if script_name in constants.EXCLUDED_NAMES_WITHOUT_VERIFY_SSL:
        return None

    ssl_param: YamlFileContent = next(
        (p for p in parameters if p["name"] in constants.VALID_SSL_PARAM_NAMES),
        None,
    )
    if ssl_param is None:
        return f"{script_name} is missing a 'Verify SSL' parameter"

    if ssl_param["type"] != ScriptParamType.BOOLEAN.to_string():
        return f"The 'verify ssl' parameter in {script_name} must be of type 'boolean'"

    if script_name in constants.EXCLUDED_NAMES_WHERE_SSL_DEFAULT_IS_NOT_TRUE:
        return None

    if not ssl_param["default_value"]:
        return (
            f"The default value of the 'Verify SSL' param in {script_name} must be a boolean true"
        )

    return None
