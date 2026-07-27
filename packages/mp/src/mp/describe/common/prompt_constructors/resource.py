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

from .prompt_constructor import PromptConstructor as BasePromptConstructor

if TYPE_CHECKING:
    from string import Template

    import anyio


class ResourcePromptConstructor(BasePromptConstructor, abc.ABC):
    __slots__: tuple[str, ...] = ("resource_file_name", "resource_name")

    def __init__(
        self,
        integration: anyio.Path,
        integration_name: str,
        resource_name: str,
        resource_file_name: str,
        out_path: anyio.Path,
    ) -> None:
        super().__init__(integration, integration_name, out_path)
        self.resource_name: str = resource_name
        self.resource_file_name: str = resource_file_name

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
