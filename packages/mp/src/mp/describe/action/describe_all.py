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
import collections
import logging
from asyncio import Task
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
from mp.core.custom_types import RepositoryType
from mp.core.file_utils import get_integration_base_folders_paths
from mp.describe.action.describe import DescribeAction

if TYPE_CHECKING:
    from pathlib import Path


logger: logging.Logger = logging.getLogger("mp.describe_marketplace")
MAX_ACTIVE_INTEGRATIONS: int = 5
MAX_ACTIVE_TASKS: int = 3


class IntegrationTask(NamedTuple):
    task: asyncio.Task[None]
    integration_name: str
    initial_action_count: int


async def describe_all_actions(src: Path | None = None, *, override: bool = False) -> None:
    """Describe all actions in all integrations in the marketplace."""
    integrations_paths: list[Path] = _get_all_integrations_paths(src=src)
    orchestrator = _MarketplaceOrchestrator(src, integrations_paths, override=override)
    await orchestrator.run()


class _MarketplaceOrchestrator:
    def __init__(
        self, src: Path | None, integrations_paths: list[Path], *, override: bool = False
    ) -> None:
        self.src: Path | None = src
        self.integrations_paths: list[Path] = integrations_paths
        self.concurrency: int = mp.core.config.get_gemini_concurrency()
        self.action_sem: asyncio.Semaphore = asyncio.Semaphore(self.concurrency)
        self.max_active_integrations: int = max(MAX_ACTIVE_INTEGRATIONS, self.concurrency)
        self.override: bool = override

        self.pending_paths: collections.deque[Path] = collections.deque(integrations_paths)
        self.active_tasks: set[IntegrationTask] = set()
        self.actions_in_flight: int = 0

    def _on_action_done(self) -> None:
        self.actions_in_flight -= 1

    def _can_start_more(self) -> bool:
        """Check if we have capacity and space in UI to start new integrations.

        Returns:
            bool: True if we can start more integrations, False otherwise.

        """
        # We want to have at least 'concurrency' actions in flight (or queued),
        # But we also want to limit the number of integrations to keep the UI clean.
        return bool(
            self.pending_paths
            and (
                self.actions_in_flight < self.concurrency
                or len(self.active_tasks) < MAX_ACTIVE_TASKS
            )
            and len(self.active_tasks) < self.max_active_integrations
        )

    async def _start_next_integration(self, progress: Progress) -> None:
        """Start describing the next integration in the queue."""
        path: Path = self.pending_paths.popleft()
        da: DescribeAction = DescribeAction(
            integration=path.name, actions=set(), src=self.src, override=self.override
        )

        # Pre-discover action count to decide if we should start more
        count: int = await da.get_actions_count()
        self.actions_in_flight += count

        task: Task[None] = asyncio.create_task(
            da.describe_actions(
                sem=self.action_sem, on_action_done=self._on_action_done, progress=progress
            )
        )
        self.active_tasks.add(
            IntegrationTask(
                task=task,
                integration_name=path.name,
                initial_action_count=count,
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
                await _process_completed_tasks(done_integration_tasks, progress, main_task)


async def _process_completed_tasks(
    done_integration_tasks: set[IntegrationTask],
    progress: Progress,
    main_task: TaskID,
) -> None:
    """Process results and exceptions for completed tasks."""
    for it in done_integration_tasks:
        progress.advance(main_task)
        try:
            await it.task
        except Exception:
            logger.exception(
                "Failed to describe integration %s",
                it.integration_name,
            )


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
