# Copyright 2026 Google LLC
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

import contextlib
import logging
import pathlib
import tomllib
from typing import Any

import anyio
import typer
import yaml

from mp.core import constants
from mp.core.file_utils import (
    create_or_get_out_integrations_dir,
    get_marketplace_integration_path,
    is_built,
)

logger: logging.Logger = logging.getLogger(__name__)


def get_integration_path(name: str, *, src: pathlib.Path | None = None) -> anyio.Path:
    """Get the path to an integration.

    Args:
        name: The name of the integration.
        src: Optional custom source path.

    Returns:
        anyio.Path: The path to the integration.

    """
    return _get_source_integration_path(name, src) if src else _get_marketplace_integration_path(name)


def _get_source_integration_path(name: str, src: pathlib.Path) -> anyio.Path:
    if (path := src / name).exists():
        return anyio.Path(path)

    logger.error("Integration '%s' not found in source '%s'", name, src)
    raise typer.Exit(1)


def _get_marketplace_integration_path(name: str) -> anyio.Path:
    if (path := get_marketplace_integration_path(name)) is not None:
        return anyio.Path(path)

    logger.error("Integration '%s' not found in marketplace", name)
    raise typer.Exit(1)


def get_out_path(integration_name: str, src: pathlib.Path | None = None) -> anyio.Path:
    """Get the output path for a built integration.

    Args:
        integration_name: The name of the integration.
        src: Optional custom source path.

    Returns:
        anyio.Path: The output path.

    """
    base_out: pathlib.Path = create_or_get_out_integrations_dir()
    if src:
        return anyio.Path(base_out / src.name / integration_name)

    identifier: str = _resolve_integration_identifier(integration_name)

    for identifier_to_try in (identifier, integration_name):
        if (path := _find_built_integration_in_repos(base_out, identifier_to_try)) is not None:
            return path

    if (path := base_out / identifier).exists() and is_built(path):
        return anyio.Path(path)

    return anyio.Path(base_out / integration_name)


def _resolve_integration_identifier(integration_name: str) -> str:
    with contextlib.suppress(Exception):
        if source_p := get_marketplace_integration_path(integration_name):
            source_path = pathlib.Path(source_p)
            return _get_identifier_from_source(source_path)
    return integration_name


def _find_built_integration_in_repos(base_out: pathlib.Path, identifier: str) -> anyio.Path | None:
    for repo_type in (
        constants.COMMERCIAL_REPO_NAME,
        constants.THIRD_PARTY_REPO_NAME,
        constants.CUSTOM_REPO_NAME,
    ):
        if (path := base_out / repo_type / identifier).exists() and is_built(path):
            return anyio.Path(path)

    return None


def _get_identifier_from_source(source_path: pathlib.Path) -> str:
    if identifier := _get_identifier_from_definition(source_path):
        return identifier

    if identifier := _get_identifier_from_pyproject(source_path):
        return identifier

    return source_path.name


def _get_identifier_from_definition(source_path: pathlib.Path) -> str | None:
    if (definition_file := source_path / constants.DEFINITION_FILE).exists():
        with definition_file.open("r", encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f)
            if data and (identifier := data.get("identifier")):
                return identifier

    return None


def _get_identifier_from_pyproject(source_path: pathlib.Path) -> str | None:
    if (pyproject_file := source_path / constants.PROJECT_FILE).exists():
        with pyproject_file.open("rb") as f:
            data: dict[str, Any] = tomllib.load(f)
            if (project := data.get("project")) and (identifier := project.get("name")):
                return identifier

    return None
