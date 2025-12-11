"""Module containing general utility functions."""

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

import os
import platform
import re
import sys
from typing import TYPE_CHECKING, Any, TypedDict, TypeVar

from mp.core.constants import WINDOWS_PLATFORM
from mp.core.custom_types import RepositoryType

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from mp.core.custom_types import YamlFileContent

SNAKE_PATTERN_1 = re.compile(r"(.)([A-Z][a-z]+)")
SNAKE_PATTERN_2 = re.compile(r"([a-z0-9])([A-Z])")
GIT_STATUS_REGEXP: re.Pattern[str] = re.compile(r"^[ A-Z?!]{2} ")
ERR_MSG_STRING_LIMIT: int = 256
TRIM_CHARS: str = " ... "

_T = TypeVar("_T")


def get_python_version_from_version_string(version: str) -> str:
    """Get the smallest python version found in a version string.

    Examples:
        >>> v: str = ">=3.11,<3.13"
        >>> get_python_version_from_version_string(v)
        3.11


    Args:
        version: the version string containing versions

    Returns:
        The string of the version

    """
    versions: list[str] = re.findall(r"[<~>!=]={0,2}(\d+\.\d+)", version)
    version_tuples: list[tuple[int, int]] = []
    for v in versions:
        major, minor = v.split(".")
        version_tuples.append((int(major), int(minor)))

    version_tuples.sort()
    lowest_version: tuple[int, int] = version_tuples[0]
    return ".".join(map(str, lowest_version))


class _TypedDictType(TypedDict):
    """Wrapper for TypedDicts to allow for attribute access."""


def remove_none_entries_from_mapping(d: _TypedDictType, /) -> None:
    """Remove all the keys that have `None` value in place.

    Args:
        d: the mapping to remove keys that have `None` as the value

    """
    keys_to_remove: list[str] = [k for k, v in d.items() if v is None]
    for k in keys_to_remove:
        del d[k]  # type: ignore[misc]


def str_to_snake_case(s: str) -> str:
    """Change a string into snake_case.

    Args:
        s: the string to transform

    Returns:
        A new string with the value of the original string in snake_case

    """
    s = s.replace(" ", "").replace("-", "")
    s = re.sub(SNAKE_PATTERN_1, r"\1_\2", s)
    return re.sub(SNAKE_PATTERN_2, r"\1_\2", s).lower()


def trim_values(s: str, /) -> str:
    """Trims a given string if its length exceeds a defined limit and appends ellipses.

    The function is designed to enforce an upper length constraint for strings.

    Args:
        s: The input string to be trimmed if it exceeds the defined length limit.

    Returns:
        The trimmed string if the length of the input string exceeds the limit,
        otherwise the original string is returned.

    """
    padding: int = len(TRIM_CHARS)
    if len(s) > ERR_MSG_STRING_LIMIT:
        return f"{s[: ERR_MSG_STRING_LIMIT - padding * 2]}{TRIM_CHARS}{s[len(s) - padding :]}"

    return s


def is_windows() -> bool:
    """Determine if the current operating system is Windows.

    Returns:
        bool: True if the operating system is Windows, otherwise False.

    """
    return sys.platform.startswith(WINDOWS_PLATFORM)


def ensure_valid_list(value: list[_T] | Any) -> list[_T]:  # noqa: ANN401
    """Ensure that the input is a valid list.

    This function checks whether the given value is a valid list. If the value is
    the `type` object (e.g., `<class 'list'>`), which can happen in GitHub actions.
    it returns an empty list Otherwise, it returns the value as-is.

    Args:
        value (list[str] | list[RepositoryType] | type): The value to validate.

    Returns:
        list: A valid list object. Returns an empty list if the input was of type `type`.

    """
    return value if isinstance(value, list) else []


def is_github_actions() -> bool:
    """Determine if the current environment is GitHub Actions.

    Returns:
        bool: True if the code is running inside a GitHub Actions workflow,
              False otherwise.

    """
    return os.getenv("GITHUB_ACTIONS") == "true"


def is_louhi() -> bool:
    """Determine if the current environment is running in the context of louhi flow.

    Returns:
        bool: True if the code is running inside louhi,
              False otherwise.

    """
    return any(key.startswith("_LOUHI_") for key in os.environ)


def is_ci_cd() -> bool:
    """Determine if the current environment is running in the context of CI CD.

    Returns:
        bool: True if the code is running inside in the context of CI CD,
              False otherwise.

    """
    return is_github_actions() or is_louhi()


def get_current_platform() -> tuple[str, str]:
    """Get the simplified operating system name and its version.

    Returns:
       A tuple containing two strings:
       1. The simplified OS name ('macOS', 'Windows', 'Linux').
       2. The OS's primary version string (e.g., '14.5', '11').

    """
    system_name: str = platform.system()
    os_name: str = "Unknown"
    version: str = "Unknown"

    if system_name == "Darwin":
        os_name = "macOS"
        version = platform.mac_ver()[0]
    elif system_name == "Windows":
        os_name = "Windows"
        version = platform.release()
    elif system_name == "Linux":
        os_name = "Linux"
        version = platform.release()

    return os_name, version


def filter_and_map_yaml_files(
    yaml_files: list[YamlFileContent],
    filter_fn: Callable[[YamlFileContent], bool],
    map_fn: Callable[[YamlFileContent], Any],
) -> list[Any]:
    """Filter and map a list of parsed YAML files.

    Returns:
        a list of the filtered file's mapped values.

    """
    return [map_fn(d) for d in yaml_files if filter_fn(d)]


def to_snake_case(s: str, /) -> str:
    """Change string to snake case.

    Args:
        s: The input string to convert.

    Returns:
        The string converted to snake_case.

    """
    s = (
        re.sub(r"(?<=[a-z])(?=[A-Z])|[^a-zA-Z\d]", " ", s)
        .strip()
        .replace(" ", "_")
        .replace("-", "_")
    )
    return s.lower()


def should_preform_integration_logic(
    integrations: Iterable[str],
    repos: Iterable[RepositoryType],
) -> bool:
    """Decide if needed to build integrations or not.

    Returns:
        True if yes overwise False

    """
    return bool(
        integrations or RepositoryType.COMMERCIAL in repos or RepositoryType.COMMUNITY in repos
    )


def should_preform_playbook_logic(
    playbooks: Iterable[str], repos: Iterable[RepositoryType]
) -> bool:
    """Decide if needed to build playbooks or not.

    Returns:
        True if yes overwise False

    """
    return bool(playbooks or RepositoryType.PLAYBOOKS in repos)
