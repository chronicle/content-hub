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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from string import Template

    import anyio


class PromptConstructor(abc.ABC):
    __slots__: tuple[str, ...] = (
        "integration",
        "integration_name",
        "out_path",
    )

    def __init__(
        self,
        integration: anyio.Path,
        integration_name: str,
        out_path: anyio.Path,
    ) -> None:
        self.integration: anyio.Path = integration
        self.integration_name: str = integration_name
        self.out_path: anyio.Path = out_path

    @staticmethod
    @abc.abstractmethod
    async def get_task_prompt() -> Template:
        """Get the task prompt.

        Returns:
            Template: The task prompt.

        """
        raise NotImplementedError

    @abc.abstractmethod
    async def construct(self) -> str:
        """Construct a prompt for generating AI descriptions.

        Returns:
            str: The constructed prompt.

        """
        raise NotImplementedError

    @property
    async def task_prompt(self) -> Template:
        """Get the task prompt (compatibility property)."""
        # Compatibility property
        return await self.get_task_prompt()
