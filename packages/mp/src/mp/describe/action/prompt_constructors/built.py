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
from mp.core.data_models.integrations.action.ai.entity_types import (
    build_dynamic_entity_prompt_rules,
    get_all_entity_param_examples_string,
)
from mp.describe.common.metadata import (
    ActionOverridePromptParams,
    build_action_override_prompt,
)

from .prompt_constructor import PromptConstructor

if TYPE_CHECKING:
    from string import Template

    import anyio

    from mp.core.data_models.integrations.action.metadata import BuiltActionMetadata
    from mp.describe.common.metadata import PromptOverrideConfig

DEFAULT_FILE_CONTENT: str = "N/A"


class BuiltPromptConstructor(PromptConstructor):
    __slots__: tuple[str, ...] = ()

    async def construct(self, template: Template | None = None) -> str:
        """Construct the prompt for built actions.

        Args:
            template: Optional custom prompt template.

        Returns:
            str: The constructed prompt.

        """
        manager_names, manager_content = await self._get_managers_names_and_content()
        if template is None:
            template = await self.task_prompt
        json_file_name = f"{self.action_file_name}.yaml"
        json_file_content = await self._get_built_action_def_content()
        python_file_name = f"{self.action_file_name}.py"
        python_file_content = await self._get_built_action_content()

        result = template.safe_substitute({
            "all_entity_param_examples": get_all_entity_param_examples_string(),
            "entity_type_mapping_rules": build_dynamic_entity_prompt_rules(),
            "json_file_name": json_file_name,
            "json_file_content": json_file_content,
            "python_file_name": python_file_name,
            "python_file_content": python_file_content,
            "manager_file_names": manager_names or DEFAULT_FILE_CONTENT,
            "manager_files_content": manager_content or DEFAULT_FILE_CONTENT,
        })

        if "<python_script" not in result:
            sources = (
                f"\n\n### SOURCE CODE & SPECIFICATIONS\n\n"
                f'<action_definition filename="{json_file_name}">\n{json_file_content}\n</action_definition>\n\n'
                f'<python_script filename="{python_file_name}">\n{python_file_content}\n</python_script>\n'
            )
            if manager_content:
                sources += f'\n<shared_modules filenames="{manager_names}">\n{manager_content}\n</shared_modules>\n'
            result += sources

        return result

    async def construct_override(self, override: PromptOverrideConfig) -> str:
        """Construct the override prompt for built actions.

        Args:
            override: Prompt override configuration.

        Returns:
            str: The constructed override prompt.

        """
        manager_names, manager_content = await self._get_managers_names_and_content()
        json_file_name = f"{self.action_file_name}.yaml"
        json_file_content = await self._get_built_action_def_content()
        python_file_name = f"{self.action_file_name}.py"
        python_file_content = await self._get_built_action_content()

        return build_action_override_prompt(
            ActionOverridePromptParams(
                target_field=override.target_field,
                criteria=override.criteria,
                action_name=self.action_name,
                py_name=python_file_name,
                py_content=python_file_content,
                json_name=json_file_name,
                json_content=json_file_content,
                manager_names=manager_names,
                manager_content=manager_content,
            )
        )

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
            self.out_path / constants.OUT_ACTIONS_META_DIR / f"{self.action_file_name}{constants.ACTIONS_META_SUFFIX}"
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
        action_script: anyio.Path = self.out_path / constants.OUT_ACTION_SCRIPTS_DIR / f"{self.action_file_name}.py"
        if await action_script.exists():
            return await action_script.read_text(encoding="utf-8")

        return DEFAULT_FILE_CONTENT
