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

import abc
import asyncio
import collections
import logging
from typing import TYPE_CHECKING, NamedTuple

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
)

import mp.core.config
from mp.core.file_utils import (
    get_all_marketplace_integrations_paths,
    get_integrations_from_paths,
)

if TYPE_CHECKING:
    from pathlib import Path

    from .describe import DescribeBase

logger: logging.Logger = logging.getLogger(__name__)
MAX_ACTIVE_INTEGRATIONS: int = 3
MAX_ACTIVE_TASKS: int = 3


class IntegrationTask(NamedTuple):
    task: asyncio.Task[None]
    integration_name: str
    initial_resource_count: int


class MarketplaceOrchestratorBase(abc.ABC):
    def __init__(
        self,
        src: Path | None,
        integrations_paths: list[Path],
        *,
        dst: Path | None = None,
        override: bool = False,
    ) -> None:
        self.src: Path | None = src
        self.dst: Path | None = dst
        self.integrations_paths: list[Path] = integrations_paths
        self.concurrency: int = mp.core.config.get_gemini_concurrency()
        self.sem: asyncio.Semaphore = asyncio.Semaphore(self.concurrency)
        self.max_active_integrations: int = max(MAX_ACTIVE_INTEGRATIONS, self.concurrency)
        self.override: bool = override

        self.pending_paths: collections.deque[Path] = collections.deque(integrations_paths)
        self.active_tasks: set[IntegrationTask] = set()
        self.resources_in_flight: int = 0

    def _on_resource_done(self) -> None:
        self.resources_in_flight -= 1

    def _can_start_more(self) -> bool:
        """Check if we have capacity and space in UI to start new integrations.

        Returns:
            bool: True if we can start more integrations, False otherwise.

        """
        return bool(
            self.pending_paths
            and (
                self.resources_in_flight < self.concurrency
                or len(self.active_tasks) < MAX_ACTIVE_TASKS
            )
            and len(self.active_tasks) < self.max_active_integrations
        )

    @abc.abstractmethod
    def _create_describer(self, integration_name: str) -> DescribeBase:
        """Create a describer for the given integration."""
        raise NotImplementedError

    async def _start_next_integration(self, progress: Progress) -> None:
        """Start describing the next integration in the queue."""
        path: Path = self.pending_paths.popleft()
        describer: DescribeBase = self._create_describer(path.name)

        # Pre-discover resource count to decide if we should start more
        count: int = await describer.get_resources_count()
        self.resources_in_flight += count

        task: asyncio.Task[None] = asyncio.create_task(
            describer.describe(sem=self.sem, on_done=self._on_resource_done, progress=progress)
        )
        self.active_tasks.add(
            IntegrationTask(
                task=task,
                integration_name=path.name,
                initial_resource_count=count,
            )
        )

    async def _wait_for_tasks(self) -> set[IntegrationTask]:
        """Wait for at least one active task to complete and return done tasks.

        Returns:
            set[IntegrationTask]: Set of completed tasks.

        """
        if not self.active_tasks:
            return set()

        done_tasks, pending_tasks = await asyncio.wait(
            {it.task for it in self.active_tasks}, return_when=asyncio.FIRST_COMPLETED
        )

        done_integration_tasks: set[IntegrationTask] = {
            it for it in self.active_tasks if it.task in done_tasks
        }
        self.active_tasks: set[IntegrationTask] = {
            it for it in self.active_tasks if it.task in pending_tasks
        }

        return done_integration_tasks

    async def run(self) -> None:
        """Run the orchestration loop."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
        ) as progress:
            main_task: TaskID = progress.add_task(
                description="Describing integrations...",
                total=len(self.integrations_paths),
            )

            while self.pending_paths or self.active_tasks:
                while self._can_start_more():
                    await self._start_next_integration(progress)

                if not self.active_tasks:
                    break

                done_integration_tasks: set[IntegrationTask] = await self._wait_for_tasks()
                for it in done_integration_tasks:
                    progress.advance(main_task)
                    try:
                        await it.task
                    except Exception:
                        logger.exception(
                            "Failed to describe integration %s",
                            it.integration_name,
                        )


def get_all_integrations_paths(src: Path | None = None) -> list[Path]:
    """Get all integrations paths from the marketplace or a custom source.

    Args:
        src: Optional custom source path.

    Returns:
        list[Path]: The paths to the integrations.

    """
    if src:
        return sorted(get_integrations_from_paths(src)) if src.exists() else []

    return get_all_marketplace_integrations_paths()
