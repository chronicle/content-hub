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

from typing import TYPE_CHECKING

from mp.describe.common.describe_all import (
    MarketplaceOrchestratorBase,
    get_all_integrations_paths,
)

from .describe import DescribeIntegration

if TYPE_CHECKING:
    from pathlib import Path


async def describe_all_integrations(
    src: Path | None = None, dst: Path | None = None, *, override: bool = False
) -> None:
    """Describe all integrations in the marketplace."""
    integrations_paths: list[Path] = get_all_integrations_paths(src=src)
    orchestrator = _MarketplaceOrchestrator(src, integrations_paths, dst=dst, override=override)
    await orchestrator.run()


class _MarketplaceOrchestrator(MarketplaceOrchestratorBase):
    def _create_describer(self, integration_name: str) -> DescribeIntegration:
        return DescribeIntegration(
            integration=integration_name,
            src=self.src,
            dst=self.dst,
            override=self.override,
        )
