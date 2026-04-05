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

from pathlib import Path

from mp.describe.common.describe_all import (
    MarketplaceOrchestratorBase,
    get_all_integrations_paths,
)
from mp.describe.common.utils.paths import get_integration_path

from .describe import DescribeIntegration


async def describe_all_integrations(
    src: Path | None = None,
    dst: Path | None = None,
    *,
    override: bool = False,
    integrations: list[str] | None = None,
) -> None:
    """Describe all integrations in the marketplace or specific ones.

    Args:
        src: Optional custom source path.
        dst: Optional custom destination path.
        override: Whether to rewrite existing descriptions.
        integrations: Optional list of integration names to describe.

    """
    integrations_paths: list[Path]
    if integrations:
        integrations_paths = [
            Path(str(get_integration_path(name, src=src))) for name in integrations
        ]
    else:
        integrations_paths = get_all_integrations_paths(src=src)

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
