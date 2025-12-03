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

import shutil
from typing import TYPE_CHECKING

import yaml

import mp.core.config

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any


VALID_REPEATED_FILES: set[str] = {"__init__.py"}


def recreate_dir(path: Path) -> None:
    """Remove the provided directory and create a new one."""
    if path.exists() and is_path_in_marketplace(path):
        shutil.rmtree(path)
        path.mkdir()


def remove_paths_if_exists(*paths: Path) -> None:
    """Remove all the provided paths."""
    for path in paths:
        _remove_path_if_exists(path)


def remove_rglobs_if_exists(*patterns: str, root: Path) -> None:
    """Remove all files and directories matching the given glob patterns.

    Args:
        *patterns: Glob patterns to match (e.g., "*.pyc", "**/__pycache__").
        root: The root directory to search from.

    """
    for pattern in patterns:
        for path in root.rglob(pattern):
            _remove_path_if_exists(path)


def _remove_path_if_exists(path: Path) -> None:
    if path.is_file() and is_path_in_marketplace(path):
        path.unlink(missing_ok=True)

    elif path.is_dir() and path.exists() and is_path_in_marketplace(path):
        shutil.rmtree(path)


def is_path_in_marketplace(path: Path) -> bool:
    """Check whether a path is in the marketplace.

    This is mostly used to ensure any file deletion will not occur outside the
    boundaries of the configured project.

    Returns:
        Whether the path is a sub path of the configured marketplace.

    """
    return mp.core.config.get_marketplace_path() in path.parents


def flatten_dir(path: Path, dest: Path) -> None:
    """Flatten a nested directory.

    Args:
        path: The path to the directory to flatten
        dest: The destination of the flattened dir

    Raises:
        FileExistsError: If more than one file with the same name is found

    """
    if path.is_file() and is_path_in_marketplace(path):
        new_path: Path = dest / path.name
        if new_path.exists():
            if new_path.name in VALID_REPEATED_FILES:
                return

            msg: str = f"File already exists: {new_path}"
            raise FileExistsError(msg)

        shutil.copyfile(path, new_path)

    elif path.is_dir() and is_path_in_marketplace(path):
        for child in path.iterdir():
            flatten_dir(child, dest)


def remove_files_by_suffix_from_dir(dir_: Path, suffix: str) -> None:
    """Remove all files with a specific suffix from a directory."""
    for file in dir_.rglob(f"*{suffix}"):
        if file.is_file() and is_path_in_marketplace(file):
            file.unlink(missing_ok=True)


def save_yaml(data: dict[str, Any], path: Path) -> None:
    """Create or overwrites a YAML file at the specified path with the provided data.

    Args:
        data: The dictionary data to serialize and write to the YAML file.
        path: The pathlib.Path object representing the target file location.

    Raises:
        OSError: If the file write operation fails (e.g., permission denied, invalid path).
        ValueError: If got yaml error.

    """
    try:
        yaml_content = yaml.dump(data, indent=4, sort_keys=False)
        path.write_text(yaml_content, encoding="utf-8")

    except OSError as e:
        msg = f"Failed to write YAML file to {path}. Check permissions or path validity."
        raise OSError(msg) from e
    except yaml.YAMLError as e:
        msg = "Failed to serialize data to YAML format."
        raise ValueError(msg) from e
