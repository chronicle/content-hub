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

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


class Configurations(NamedTuple):
    only_pre_build: bool


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
