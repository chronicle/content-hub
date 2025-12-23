"""Module containing utility functions for interacting with the file system.

Used for things such as path manipulation and file content operations.
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

import base64
import dataclasses
import json
from typing import TYPE_CHECKING, Any

import yaml

import mp.core.constants
import mp.core.file_utils.common.utils
from mp.core import constants
from mp.core.custom_types import JsonString, ManagerName, Products
from mp.core.validators import validate_png_content, validate_svg_content

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from pathlib import Path

    from mp.core.custom_types import RepositoryType


def get_integrations_path(integrations_classification: RepositoryType) -> Path:
    """Get a marketplace integrations' path.

    Args:
        integrations_classification: the name of the marketplace

    Returns:
        The marketplace's integrations' directory path

    """
    return create_or_get_integrations_path() / integrations_classification.value


def create_or_get_integrations_path() -> Path:
    """Get the content/integrations path.

    Returns:
        The content/integrations directory path

    """
    return mp.core.file_utils.common.utils.create_dir_if_not_exists(
        mp.core.file_utils.common.utils.create_or_get_content_dir()
        / constants.INTEGRATIONS_DIR_NAME
    )


def get_all_integrations_paths(integrations_classification: str) -> list[Path]:
    """Get all marketplace integrations sub-dirs paths.

    Args:
        integrations_classification: the name of the marketplace

    Returns:
        The marketplace's integrations' directories paths

    """
    marketplace_dir_names: tuple[str, ...] = constants.INTEGRATIONS_DIRS_NAMES_DICT[
        integrations_classification
    ]
    return [create_or_get_integrations_path() / dir_name for dir_name in marketplace_dir_names]


def create_or_get_integrations_dir() -> Path:
    """Get the content path.

    If the directory doesn't exist, it creates it

    Returns:
        The root/content/integrations directory path

    """
    return mp.core.file_utils.common.utils.create_dir_if_not_exists(
        mp.core.file_utils.common.utils.create_or_get_content_dir()
        / constants.INTEGRATIONS_DIR_NAME
    )


def create_or_get_out_integrations_dir() -> Path:
    """Get the out/content/integrations/ path.

    If the directory doesn't exist, it creates it

    Returns:
        The out/content/integrations directory path

    """
    return mp.core.file_utils.common.utils.create_dir_if_not_exists(
        mp.core.file_utils.common.utils.create_or_get_out_contents_dir()
        / constants.OUT_INTEGRATIONS_DIR_NAME
    )


def discover_core_modules(path: Path) -> list[ManagerName]:
    """Discover core/manager modules in an integration.

    Args:
        path: The path to the integration

    Returns:
        A list of all manager file names

    """
    if is_built(path) or is_half_built(path):
        return sorted(
            [
                p.stem
                for p in (path / constants.OUT_MANAGERS_SCRIPTS_DIR).rglob("*.py")
                if p.is_file() and p.stem not in {"__init__", "__main__"}
            ],
        )

    return sorted(
        [
            p.stem
            for p in (path / constants.CORE_SCRIPTS_DIR).rglob("*.py")
            if p.is_file() and p.stem not in {"__init__", "__main__"}
        ],
    )


def get_integrations_and_groups_from_paths(*paths: Path) -> Products[set[Path]]:
    """Get all integrations and integration groups paths from the provided paths.

    Args:
        *paths: The paths to search integrations and groups in

    Returns:
        A `Products` object that contains sets of all the integrations and groups paths
        that were found

    """
    integrations: set[Path] = set()
    groups: set[Path] = set()
    for path in paths:
        if not path.exists():
            continue

        for dir_ in path.iterdir():
            if is_group(dir_):
                groups.add(dir_)

            elif is_integration(dir_):
                integrations.add(dir_)

    return Products(integrations=integrations, groups=groups)


def is_python_file(path: Path) -> bool:
    """Check whether a path is a python file.

    Returns:
        Whether the provided file is of a python file

    """
    return path.exists() and path.is_file() and path.suffix == ".py"


def is_integration(path: Path, *, group: str = "") -> bool:
    """Check whether a path is an integration.

    Returns:
        Whether the provided path is an integration

    """
    parents: set[str] = {p.name for p in (path, *path.parents)}
    valid_base_dirs: set[str] = set(mp.core.constants.INTEGRATIONS_TYPES)

    if group:
        valid_base_dirs.add(group)

    return bool(parents.intersection(valid_base_dirs) and _is_integration(path))


def _is_integration(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False

    validator: IntegrationParityValidator = IntegrationParityValidator(path)
    validator.validate_integration_components_parity()

    pyproject_toml: Path = path / constants.PROJECT_FILE
    def_: Path = path / constants.INTEGRATION_DEF_FILE.format(path.name)
    return pyproject_toml.exists() or def_.exists()


def is_group(path: Path) -> bool:
    """Check whether a path is an integration group.

    Returns:
        Whether the provided path is an integration group

    """
    parents: set[str] = {p.name for p in (path, *path.parents)}
    return bool(parents.intersection(constants.INTEGRATIONS_TYPES) and _is_group(path))


def _is_group(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False

    return not is_integration(path) and all(
        is_integration(p, group=path.name) for p in path.iterdir() if p.is_dir()
    )


def replace_file_content(file: Path, replace_fn: Callable[[str], str]) -> None:
    """Replace a file's entire content.

    Args:
        file: The file to replace its content
        replace_fn: A function that takes in the current file's content and returns
            the new content that will be written into the file

    """
    file_content: str = file.read_text(encoding="utf-8")
    file_content = replace_fn(file_content)
    file.write_text(file_content, encoding="utf-8")


def is_built(integration: Path) -> bool:
    """Check whether an integration is built.

    Returns:
        Whether the integration is in a built format

    """
    pyproject: Path = integration / constants.PROJECT_FILE
    def_file: Path = integration / constants.INTEGRATION_DEF_FILE.format(integration.name)
    definition_file: Path = integration / constants.DEFINITION_FILE
    return not pyproject.exists() and def_file.exists() and not definition_file.exists()


def is_half_built(integration: Path) -> bool:
    """Check whether an integration is half-built.

    Returns:
        Whether the integration is in a half-built format

    """
    pyproject: Path = integration / constants.PROJECT_FILE
    def_file: Path = integration / constants.INTEGRATION_DEF_FILE.format(integration.name)
    return pyproject.exists() and def_file.exists()


def is_non_built_integration(integration: Path) -> bool:
    """Check whether an integration is non-built.

    Returns:
        Whether the integration is in a non-built format

    """
    pyproject: Path = integration / constants.PROJECT_FILE
    def_file: Path = integration / constants.INTEGRATION_DEF_FILE.format(integration.name)
    definition_file: Path = integration / constants.DEFINITION_FILE
    return pyproject.exists() and definition_file.exists() and not def_file.exists()


def write_yaml_to_file(content: Mapping[str, Any] | Sequence[Any], path: Path) -> None:
    """Write content into a YAML file.

    Args:
        content: the content to write
        path: the path of the YAML file

    """
    dumped: str = yaml.safe_dump(
        data=content,
        indent=4,
        width=80,
        sort_keys=False,
        allow_unicode=True,
    )
    path.write_text(dumped, encoding="utf-8")


@dataclasses.dataclass(slots=True, frozen=True)
class IntegrationParityValidator:
    path: Path

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
        actions: Path = self.path / constants.ACTIONS_DIR
        if actions.exists():
            _validate_script_metadata_parity(actions, ".py", constants.DEF_FILE_SUFFIX)

    def _validate_connectors(self) -> None:
        connectors: Path = self.path / constants.CONNECTORS_DIR
        if connectors.exists():
            _validate_script_metadata_parity(
                directory=connectors,
                script_suffix=".py",
                metadata_suffix=constants.DEF_FILE_SUFFIX,
            )

    def _validate_jobs(self) -> None:
        jobs: Path = self.path / constants.JOBS_DIR
        if jobs.exists():
            _validate_script_metadata_parity(jobs, ".py", constants.DEF_FILE_SUFFIX)

    def _validate_widgets(self) -> None:
        widgets: Path = self.path / constants.WIDGETS_DIR
        if widgets.exists():
            _validate_script_metadata_parity(
                directory=widgets,
                script_suffix=".html",
                metadata_suffix=constants.DEF_FILE_SUFFIX,
            )


def _validate_script_metadata_parity(
    directory: Path,
    script_suffix: str,
    metadata_suffix: str,
) -> None:
    _validate_matching_files(directory, script_suffix, metadata_suffix)
    _validate_matching_files(directory, metadata_suffix, script_suffix)


def _validate_matching_files(directory: Path, primary_suffix: str, secondary_suffix: str) -> None:
    for file in directory.rglob(f"*{primary_suffix}"):
        if file.name == constants.PACKAGE_FILE:
            continue

        expected_file: Path = file.with_suffix(secondary_suffix)
        if not expected_file.exists():
            msg: str = (
                f"The {directory.name} directory has a file '{file.name}' without a"
                f"  matching '{secondary_suffix}' file"
            )
            raise RuntimeError(msg)


def is_commercial_integration(path: Path) -> bool:
    """Check if the given integration path corresponds to a commercial integration.

    This function evaluates whether the provided integration path belongs to the
    directory designated for commercial integrations.

    Args:
        path: The path to the integration directory.

    Returns:
        bool: True if the integration belongs to the commercial directory, False
            otherwise.

    """
    return (
        is_integration(path)
        and path.parent.name
        in constants.INTEGRATIONS_DIRS_NAMES_DICT[constants.COMMERCIAL_DIR_NAME]
    )


def base64_to_png_file(image_data: bytes, output_path: Path) -> None:
    """Save image bytes to a PNG file.

    Args:
        image_data: The raw byte content of the image.
        output_path: The path to save the PNG file to.

    """
    output_path.write_bytes(image_data)


def text_to_svg_file(svg_text: str, output_path: Path) -> None:
    """Save a string of SVG content to a .svg file.

    Args:
        svg_text: The string content of the SVG.
        output_path: The path to save the SVG file to.

    Raises:
        OSError: If the file cannot be written.

    """
    try:
        output_path.write_text(svg_text, encoding="utf-8")
    except OSError as e:
        msg = f"Failed to write SVG file to {output_path}"
        raise OSError(msg) from e


def svg_path_to_text(file_path: Path) -> str | None:
    """Read and validate an SVG file from a path.

    Args:
        file_path: The path to the SVG file.

    Returns:
        The text content of the SVG file if exists.

    """
    if file_path.exists():
        return validate_svg_content(file_path)
    return None


def png_path_to_bytes(file_path: Path) -> str | None:
    """Read and validate a PNG file from a path.

    Args:
        file_path: The path to the PNG file.

    Returns:
        The decoded byte content of the PNG file if exists.

    """
    if file_path.exists():
        return base64.b64encode(validate_png_content(file_path)).decode()
    return None


def read_and_validate_json_file(json_path: Path) -> JsonString:
    """Read the text content of a file and validates that it's valid JSON.

    Raises:
        ValueError: If the file doesn't exist or is an invalid JSON.

    Returns:
        The decoded text content of the JSON file if exists.

    """
    try:
        content: JsonString = json_path.read_text(encoding="utf-8")
        json.loads(content)
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON content in file: {json_path}"
        raise ValueError(msg) from e
    except FileNotFoundError as e:
        msg = f"File {json_path} does not exist"
        raise ValueError(msg) from e
    else:
        return content


def write_str_to_json_file(json_path: Path, json_content: JsonString) -> None:
    """Write a JSON string to a file."""
    with json_path.open("w", encoding="utf-8") as f_json:
        json.dump(json_content, f_json, indent=4)


def load_yaml_file(path: Path) -> dict[str, Any]:
    """Read a file and loads its content as YAML.

    Raises:
        ValueError: If the file doesn't exist or is an invalid YAML.

    Returns:
        The decoded YAML content of the YAML file if it exists.

    """
    try:
        content = path.read_text(encoding="utf-8")
        return yaml.safe_load(content)
    except yaml.YAMLError as e:
        msg = f"Failed to load or parse YAML from file: {path}"
        raise ValueError(msg) from e
    except FileNotFoundError as e:
        msg = f"File {path} does not exist"
        raise ValueError(msg) from e


def get_playbooks_dir_path() -> Path:
    """Get the content/playbooks path, creating it if it doesn't exist.

    Returns:
        The content/playbooks directory path.

    """
    content_dir: Path = mp.core.file_utils.common.utils.create_or_get_content_dir()
    return mp.core.file_utils.common.utils.create_dir_if_not_exists(
        content_dir / constants.PLAYBOOKS_DIR_NAME
    )


def create_or_get_playbook_out_dir() -> Path:
    """Get the out/content/playbooks path, creating it if it doesn't exist.

    Returns:
        The out/content/playbooks directory path.

    """
    out_content_dir: Path = mp.core.file_utils.common.utils.create_or_get_out_contents_dir()
    playbooks_out_dir: Path = mp.core.file_utils.common.utils.create_dir_if_not_exists(
        out_content_dir / constants.PLAYBOOKS_DIR_NAME
    )
    return playbooks_out_dir
