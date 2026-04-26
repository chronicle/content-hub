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
from pathlib import Path
from typing import TYPE_CHECKING

import mp.core.config
from mp.describe.action.describe import DescribeAction
from mp.describe.common.describe_all import (
    MarketplaceOrchestratorBase,
    get_all_integrations_paths,
)
from mp.describe.common.utils.paths import get_integration_path
from mp.describe.connector.describe import DescribeConnector
from mp.describe.integration.describe import DescribeIntegration
from mp.describe.job.describe import DescribeJob

if TYPE_CHECKING:
    from collections.abc import Callable

    from rich.progress import Progress


async def describe_all_content(
    integration: str | None = None,
    *,
    integrations: list[str] | None = None,
    src: Path | None = None,
    dst: Path | None = None,
    override: bool = False,
) -> None:
    """Describe all content in one or more integrations.

    Args:
        integration: Single integration name (backward compatibility).
        integrations: List of integration names.
        src: Optional custom source path.
        dst: Optional custom destination path.
        override: Whether to rewrite existing descriptions.

    """
    all_integrations: list[str] = []
    if integration:
        all_integrations.append(integration)
    if integrations:
        all_integrations.extend(integrations)

    integrations_paths: list[Path]
    if all_integrations:
        integrations_paths = [Path(str(get_integration_path(name, src=src))) for name in all_integrations]
    else:
        integrations_paths = get_all_integrations_paths(src=src)

    orchestrator = AllContentMarketplaceOrchestrator(src, integrations_paths, dst=dst, override=override)
    await orchestrator.run()


class AllContentMarketplaceOrchestrator(MarketplaceOrchestratorBase):
    """Orchestrate all-content description across the entire marketplace."""

    def _create_describer(self, integration_name: str) -> AllContentDescriber:
        return AllContentDescriber(
            integration=integration_name,
            src=self.src,
            dst=self.dst,
            override=self.override,
        )


class AllContentDescriber:
    """Describer for all content types in an integration."""

    def __init__(
        self,
        integration: str,
        *,
        src: Path | None = None,
        dst: Path | None = None,
        override: bool = False,
    ) -> None:
        self.integration = integration
        self.src = src
        self.dst = dst
        self.override = override

    @staticmethod
    async def get_resources_count() -> int:
        """Get the number of resources to describe.

        For all-content, we use 4 as a representative number of stages:
        actions, connectors, jobs, and the integration metadata.

        Returns:
            int: The number of stages.

        """
        return 4

    async def describe(
        self,
        sem: asyncio.Semaphore | None = None,
        on_done: Callable[[], None] | None = None,
        progress: Progress | None = None,
    ) -> None:
        """Describe all content in an integration."""
        if sem is None:
            sem = asyncio.Semaphore(mp.core.config.get_gemini_concurrency())

        # 1. Describe actions
        await DescribeAction(self.integration, set(), src=self.src, dst=self.dst, override=self.override).describe(
            sem=sem, progress=progress
        )

        # 2. Describe connectors
        await DescribeConnector(self.integration, set(), src=self.src, dst=self.dst, override=self.override).describe(
            sem=sem, progress=progress
        )

        # 3. Describe jobs
        await DescribeJob(self.integration, set(), src=self.src, dst=self.dst, override=self.override).describe(
            sem=sem, progress=progress
        )

        # 4. Describe integration (last because it depends on previous results)
        await DescribeIntegration(self.integration, src=self.src, dst=self.dst, override=self.override).describe(
            sem=sem, progress=progress
        )

        if on_done:
            on_done()
