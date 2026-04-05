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

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pathlib

import anyio
import typer

from mp.core.file_utils import (
    create_or_get_out_integrations_dir,
    get_marketplace_integration_path,
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
    if src:
        return _get_source_integration_path(name, src)
    return _get_marketplace_integration_path(name)


def _get_source_integration_path(name: str, src: pathlib.Path) -> anyio.Path:
    path = src / name
    if path.exists():
        return anyio.Path(path)
    logger.error("Integration '%s' not found in source '%s'", name, src)
    raise typer.Exit(1)


def _get_marketplace_integration_path(name: str) -> anyio.Path:
    path = get_marketplace_integration_path(name)
    if path:
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
    base_out: anyio.Path = anyio.Path(create_or_get_out_integrations_dir())
    if src:
        return base_out / src.name / integration_name
    return base_out / integration_name
