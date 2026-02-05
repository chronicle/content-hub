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

import math
import pathlib
import tomllib
from typing import TYPE_CHECKING, Any

import rich
import typer

import mp.core.constants
from mp.core.config import get_marketplace_path

from .utils import (
    VersionCache,
    calculate_dependencies_hash,
    load_and_validate_cache,
    update_built_def_file,
    update_cache_file,
    update_version_cache,
)

if TYPE_CHECKING:
    from pathlib import Path

CONFIG_PATH = pathlib.Path.home() / ".mp_dev_env.json"
INTEGRATIONS_CACHE_DIR_NAME: str = ".integrations_cache"
VERSIONS_CACHE_FILE_NAME: str = "version_cache.yaml"


def minor_version_bump(
    integration_dir_built: Path,
    integration_dir_non_built: Path,
    integration_id: str,
) -> None:
    """Bump the minor version of an integration to enable new venv creation.

    Args:
        integration_dir_built (pathlib.Path): The path to the built integration directory.
        integration_dir_non_built (pathlib.Path): The path to the non-built integration directory.
        integration_id (str): The integration identifier.

    Raises:
        typer.Exit: If the 'packages/mp' folder cannot be found in a parent directory.

    """
    try:
        pyproject_path: Path = integration_dir_non_built / mp.core.constants.PROJECT_FILE
        pyproject_data: dict[str, Any] = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

        version: float = float(pyproject_data["project"]["version"])
        cache_dir: Path = get_marketplace_path() / INTEGRATIONS_CACHE_DIR_NAME
        cache: VersionCache | None = load_and_validate_cache(
            cache_dir, integration_id, math.floor(version)
        )
        updated_hash: str = calculate_dependencies_hash(pyproject_data)
        updated_version_cache: VersionCache = update_version_cache(cache, updated_hash, version)

        update_cache_file(cache_dir, integration_dir_built, updated_version_cache)
        update_built_def_file(integration_dir_built, updated_version_cache)

    except FileNotFoundError as e:
        rich.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e
