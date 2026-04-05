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
from typing import TYPE_CHECKING

import mp.core.config
from mp.describe.action.describe import DescribeAction
from mp.describe.connector.describe import DescribeConnector
from mp.describe.integration.describe import DescribeIntegration
from mp.describe.job.describe import DescribeJob

if TYPE_CHECKING:
    import pathlib


async def describe_all_content(
    integration: str,
    *,
    src: pathlib.Path | None = None,
    dst: pathlib.Path | None = None,
    override: bool = False,
) -> None:
    """Describe all content in an integration.

    Describes actions, connectors, jobs, and the integration itself.

    Args:
        integration: The name of the integration.
        src: Customize the source folder to describe from.
        dst: Customize the destination folder to save the AI descriptions.
        override: Whether to rewrite existing descriptions.

    """
    sem = asyncio.Semaphore(mp.core.config.get_gemini_concurrency())

    # 1. Describe actions
    await DescribeAction(integration, set(), src=src, dst=dst, override=override).describe(sem=sem)

    # 2. Describe connectors
    await DescribeConnector(integration, set(), src=src, dst=dst, override=override).describe(
        sem=sem
    )

    # 3. Describe jobs
    await DescribeJob(integration, set(), src=src, dst=dst, override=override).describe(sem=sem)

    # 4. Describe integration (last because it depends on previous results)
    await DescribeIntegration(integration, src=src, dst=dst, override=override).describe(sem=sem)
