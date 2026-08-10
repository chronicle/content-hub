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
from typing import TYPE_CHECKING

import toon_format
import yaml

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

    from mp.core.data_models.integrations.action.metadata import NonBuiltActionMetadata
    from mp.describe.common.metadata import PromptOverrideConfig

DEFAULT_FILE_CONTENT: str = "N/A"


class SourcePromptConstructor(PromptConstructor):
    __slots__: tuple[str, ...] = ()

    async def construct(self, template: Template | None = None) -> str:
        """Construct the prompt for non-built actions.

        Args:
            template: Optional custom prompt template.

        Returns:
            str: The constructed prompt.

        """
        core_names, core_content = await self._get_core_modules_names_and_content()
        if template is None:
            template = await self.task_prompt
        json_file_name = f"{self.action_file_name}.yaml"
        json_file_content = await self._get_non_built_action_def_content()
        python_file_name = f"{self.action_file_name}.py"
        python_file_content = await self._get_non_built_action_content()

        result = template.safe_substitute({
            "all_entity_param_examples": get_all_entity_param_examples_string(),
            "entity_type_mapping_rules": build_dynamic_entity_prompt_rules(),
            "json_file_name": json_file_name,
            "json_file_content": json_file_content,
            "python_file_name": python_file_name,
            "python_file_content": python_file_content,
            "manager_file_names": core_names or DEFAULT_FILE_CONTENT,
            "manager_files_content": core_content or DEFAULT_FILE_CONTENT,
        })

        if "<python_script" not in result:
            sources = (
                f"\n\n### SOURCE CODE & SPECIFICATIONS\n\n"
                f'<action_definition filename="{json_file_name}">\n{json_file_content}\n</action_definition>\n\n'
                f'<python_script filename="{python_file_name}">\n{python_file_content}\n</python_script>\n'
            )
            if core_content:
                sources += f'\n<shared_modules filenames="{core_names}">\n{core_content}\n</shared_modules>\n'
            result += sources

        return result

    async def construct_override(self, override: PromptOverrideConfig) -> str:
        """Construct the override prompt for non-built actions.

        Args:
            override: Prompt override configuration.

        Returns:
            str: The constructed override prompt.

        """
        core_names, core_content = await self._get_core_modules_names_and_content()
        json_file_name = f"{self.action_file_name}.yaml"
        json_file_content = await self._get_non_built_action_def_content()
        python_file_name = f"{self.action_file_name}.py"
        python_file_content = await self._get_non_built_action_content()

        return build_action_override_prompt(
            ActionOverridePromptParams(
                target_field=override.target_field,
                criteria=override.criteria,
                action_name=self.action_name,
                py_name=python_file_name,
                py_content=python_file_content,
                json_name=json_file_name,
                json_content=json_file_content,
                manager_names=core_names,
                manager_content=core_content,
            )
        )

    async def _get_core_modules_names_and_content(self) -> tuple[str, str]:
        names: list[str] = []
        content: io.StringIO = io.StringIO()
        core_dir: anyio.Path = self.integration / constants.CORE_SCRIPTS_DIR
        if await core_dir.exists():
            async for core_file in core_dir.glob("*.py"):
                names.append(core_file.name)
                content.write("```python\n")
                content.write(await core_file.read_text(encoding="utf-8"))
                content.write("\n```\n\n")

        return ", ".join(names), content.getvalue()

    async def _get_non_built_action_def_content(self) -> str:
        action_yaml: anyio.Path = (
            self.integration / constants.ACTIONS_DIR / f"{self.action_file_name}{constants.YAML_SUFFIX}"
        )
        if await action_yaml.exists():
            content: str = await action_yaml.read_text(encoding="utf-8")
            try:
                data: NonBuiltActionMetadata = yaml.safe_load(content)
                return toon_format.encode(data)

            except yaml.YAMLError:
                return content

        return DEFAULT_FILE_CONTENT

    async def _get_non_built_action_content(self) -> str:
        action_script: anyio.Path = self.integration / constants.ACTIONS_DIR / f"{self.action_file_name}.py"
        if await action_script.exists():
            return await action_script.read_text(encoding="utf-8")

        return DEFAULT_FILE_CONTENT
