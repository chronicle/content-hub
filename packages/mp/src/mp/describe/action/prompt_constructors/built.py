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

import io
import json
from typing import TYPE_CHECKING

import toon_format

from mp.core import constants

from .prompt_constructor import PromptConstructor

if TYPE_CHECKING:
    from string import Template

    import anyio

    from mp.core.data_models.integrations.action.metadata import BuiltActionMetadata

DEFAULT_FILE_CONTENT: str = "N/A"


class BuiltPromptConstructor(PromptConstructor):
    __slots__: tuple[str, ...] = ()

    async def construct(self) -> str:
        """Construct the prompt for built actions.

        Returns:
            str: The constructed prompt.

        """
        manager_names, manager_content = await self._get_managers_names_and_content()
        template: Template = await self.task_prompt
        return template.safe_substitute({
            "json_file_name": f"{self.action_name}.yaml",
            "json_file_content": await self._get_built_action_def_content(),
            "python_file_name": f"{self.action_name}.py",
            "python_file_content": await self._get_built_action_content(),
            "manager_file_names": manager_names or DEFAULT_FILE_CONTENT,
            "manager_files_content": manager_content or DEFAULT_FILE_CONTENT,
        })

    async def _get_managers_names_and_content(self) -> tuple[str, str]:
        names: list[str] = []
        content: io.StringIO = io.StringIO()
        managers_dir: anyio.Path = self.out_path / constants.OUT_MANAGERS_SCRIPTS_DIR
        if await managers_dir.exists():
            async for core_file in managers_dir.glob("*.py"):
                names.append(core_file.name)
                content.write("```python\n")
                content.write(await core_file.read_text(encoding="utf-8"))
                content.write("\n```\n\n")

        return ", ".join(names), content.getvalue()

    async def _get_built_action_def_content(self) -> str:
        action_def: anyio.Path = (
            self.out_path
            / constants.OUT_ACTIONS_META_DIR
            / f"{self.action_name}{constants.ACTIONS_META_SUFFIX}"
        )
        if await action_def.exists():
            content: str = await action_def.read_text(encoding="utf-8")
            try:
                data: BuiltActionMetadata = json.loads(content)
                return toon_format.encode(data)

            except json.JSONDecodeError:
                return content

        return DEFAULT_FILE_CONTENT

    async def _get_built_action_content(self) -> str:
        action_script: anyio.Path = (
            self.out_path / constants.OUT_ACTION_SCRIPTS_DIR / f"{self.action_name}.py"
        )
        if await action_script.exists():
            return await action_script.read_text(encoding="utf-8")

        return DEFAULT_FILE_CONTENT
