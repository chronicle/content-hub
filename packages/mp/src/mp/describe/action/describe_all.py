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

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from rich.progress import track

import mp.core.config
from mp.core.custom_types import RepositoryType
from mp.core.file_utils import get_integration_base_folders_paths
from mp.describe.action.describe import DescribeAction

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from pathlib import Path


logger: logging.Logger = logging.getLogger("mp.describe_marketplace")
MAX_INTEGRATION_IN_BATCH: int = 5


async def describe_all_actions(src: Path | None = None) -> None:
    """Describe all actions in all integrations in the marketplace."""
    integrations_paths: list[Path] = _get_all_integrations_paths(src=src)
    sem: asyncio.Semaphore = asyncio.Semaphore(
        min(MAX_INTEGRATION_IN_BATCH, mp.core.config.get_processes_number())
    )

    async def _describe_with_sem(path: Path) -> None:
        async with sem:
            try:
                await describe_integration(path, src=src)
            except Exception:
                logger.exception("Failed to describe integration %s", path.name)

    tasks: list[Coroutine[Any, Any, None]] = [
        _describe_with_sem(path) for path in integrations_paths
    ]
    for coro in track(
        sequence=asyncio.as_completed(tasks),
        description="Describing integrations...",
        total=len(tasks),
    ):
        await coro


async def describe_integration(integration_path: Path, src: Path | None = None) -> None:
    """Describe all actions in a given integration."""
    await DescribeAction(integration_path.name, set(), src=src).describe_actions()


def _get_all_integrations_paths(src: Path | None = None) -> list[Path]:
    if src:
        return (
            [p for p in src.iterdir() if p.is_dir() and not p.name.startswith(".")]
            if src.exists()
            else []
        )

    paths: list[Path] = []
    base_paths: list[Path] = []
    for repo_type in [RepositoryType.COMMERCIAL, RepositoryType.THIRD_PARTY]:
        base_paths.extend(get_integration_base_folders_paths(repo_type.value))

    for base_path in base_paths:
        if not base_path.exists():
            continue

        paths.extend([p for p in base_path.iterdir() if p.is_dir() and not p.name.startswith(".")])

    return paths
