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

from abc import ABC
from string import Template

import anyio

from mp.describe.common.prompt_constructors.resource import ResourcePromptConstructor


class ConnectorPromptConstructor(ResourcePromptConstructor, ABC):
    __slots__: tuple[str, ...] = ()

    @staticmethod
    async def get_task_prompt() -> Template:
        """Get the task prompt.

        Returns:
            Template: The task prompt.

        """
        prompt_file: anyio.Path = anyio.Path(__file__).parent.parent / "prompts" / "task.md"
        return Template(await prompt_file.read_text(encoding="utf-8"))
