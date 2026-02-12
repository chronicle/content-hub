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
from string import Template

import anyio


class PromptConstructor(abc.ABC):
    __slots__: tuple[str, ...] = (
        "action_file_name",
        "action_name",
        "integration",
        "integration_name",
        "out_path",
    )

    def __init__(
        self,
        integration: anyio.Path,
        integration_name: str,
        action_name: str,
        action_file_name: str,
        out_path: anyio.Path,
    ) -> None:
        self.integration: anyio.Path = integration
        self.integration_name: str = integration_name
        self.action_name: str = action_name
        self.action_file_name: str = action_file_name
        self.out_path: anyio.Path = out_path

    @property
    async def task_prompt(self) -> Template:
        """Get the task prompt.

        Returns:
            str: The task prompt.

        """
        prompt_file: anyio.Path = anyio.Path(__file__).parent.parent / "prompts" / "task.md"
        return Template(await prompt_file.read_text(encoding="utf-8"))

    @abc.abstractmethod
    async def construct(self) -> str:
        """Construct a prompt for generating action descriptions.

        Returns:
            str: The constructed prompt.

        """
        raise NotImplementedError
