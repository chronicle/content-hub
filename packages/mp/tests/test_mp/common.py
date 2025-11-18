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

import json
import tomllib
from typing import TYPE_CHECKING, Any

import yaml

from mp.core.utils import is_windows

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


def get_toml_content(expected: Path, actual: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compare two TOML files.

    Args:
        expected: the path to the expected TOML file
        actual: path to the actual TOML file

    Returns:
        A tuple of the actual and expected toml file contents to be asserted in a test.

    """
    e: dict[str, Any] = tomllib.loads(expected.read_text(encoding="utf-8"))
    a: dict[str, Any] = tomllib.loads(actual.read_text(encoding="utf-8"))
    return e, a


def get_yaml_content(expected: Path, actual: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compare two YAML files.

    Args:
        expected: the path to the expected YAML file
        actual: path to the actual YAML file

    Returns:
        A tuple of the actual and expected toml file contents to be asserted in a test.

    """
    e: dict[str, Any] = yaml.safe_load(expected.read_text(encoding="utf-8"))
    a: dict[str, Any] = yaml.safe_load(actual.read_text(encoding="utf-8"))
    return e, a


def get_json_content(expected: Path, actual: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compare two JSON files.

    Args:
        expected: path to the expected JSON file
        actual: path to the actual JSON file

    Returns:
        A tuple of the actual and expected toml file contents to be asserted in a test.

    """
    e: dict[str, Any] = json.loads(expected.read_text(encoding="utf-8"))
    a: dict[str, Any] = json.loads(actual.read_text(encoding="utf-8"))
    return a, e


def compare_files(expected: Path, actual: Path) -> tuple[set[str], set[str]]:
    """Compare two directories' files.

    Args:
        expected: path to the expected dir
        actual: path to the actual dir

    Returns:
        A tuple of the actual and expected file names from each dir to be compared
        and asserted in a test

    """
    msg: str
    if not expected.is_dir():
        msg = f"Expected path is not a directory or does not exist: {expected}"
        raise ValueError(msg)
    if not actual.is_dir():
        msg = f"Actual path is not a directory or does not exist: {actual}"
        raise ValueError(msg)

    expected_files: set[str] = {p.name for p in expected.rglob("*.*") if ".venv" not in p.parts}
    actual_files: set[str] = {p.name for p in actual.rglob("*.*") if ".venv" not in p.parts}

    if is_windows():
        expected_files = _normalize_wheel_names(expected_files)
        actual_files = _normalize_wheel_names(actual_files)

    return actual_files, expected_files


def compare_dependencies(expected: Path, actual: Path) -> tuple[set[str], set[str]]:
    """Compare two dependencies directories.

    Args:
        expected: path to the expected dependencies dir
        actual: path to the actual dependencies dir

    Returns:
        A tuple of the actual and expected dependency names from each dir to be compared
        and asserted in a test

    """
    if not expected.is_dir():
        raise NotADirectoryError(expected)

    if not actual.is_dir():
        raise NotADirectoryError(actual)

    expected_dependencies: set[str] = {p.name for p in expected.iterdir()}
    actual_dependencies: set[str] = {p.name for p in actual.iterdir()}

    if is_windows():
        expected_dependencies = _normalize_wheel_names(expected_dependencies)
        actual_dependencies = _normalize_wheel_names(actual_dependencies)

    return actual_dependencies, expected_dependencies


def _normalize_wheel_names(file_names: Iterable[str]) -> set[str]:
    """
    Normalizes a set of filenames by stripping platform-specific tags from
    any wheel files, for testing-on-windows purposes only.

    Example:
        Input: {'test_project-1.0.0-cp310-cp310-win_amd64.whl'}
        Output: {'test_project-1.0.0.whl'}
    """
    return {
        "-".join(filename.split("-")[:2]) + ".whl" if filename.endswith(".whl") else filename
        for filename in file_names
    }
