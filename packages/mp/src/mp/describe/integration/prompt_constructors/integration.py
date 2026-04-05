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

import logging
from string import Template
from typing import TYPE_CHECKING

import anyio
import yaml

from mp.core import constants
from mp.describe.common.prompt_constructors.prompt_constructor import PromptConstructor

if TYPE_CHECKING:
    from mp.core.data_models.integrations.integration_meta.metadata import (
        NonBuiltIntegrationMetadata,
    )

logger: logging.Logger = logging.getLogger(__name__)


class IntegrationPromptConstructor(PromptConstructor):
    @staticmethod
    async def get_task_prompt() -> Template:
        """Get the task prompt.

        Returns:
            Template: The task prompt.

        """
        prompt_file: anyio.Path = anyio.Path(__file__).parent.parent / "prompts" / "task.md"
        return Template(await prompt_file.read_text(encoding="utf-8"))

    async def construct(self) -> str:
        """Construct the prompt for integrations.

        Returns:
            str: The constructed prompt.

        """
        template: Template = await self.get_task_prompt()
        return template.safe_substitute({
            "integration_name": self.integration_name,
            "integration_description": await self._get_integration_description(),
            "actions_ai_descriptions": await self._get_actions_ai_descriptions(),
        })

    async def _get_integration_description(self) -> str:
        # We need to read the integration description from its metadata file.
        # It's usually in integration_name.yaml or integration_name.json
        # But we can try to find it.
        integration_def: anyio.Path = self.integration / constants.INTEGRATION_DEF_FILE.format(
            self.integration_name
        )
        if await integration_def.exists():
            content: str = await integration_def.read_text(encoding="utf-8")
            try:
                data: NonBuiltIntegrationMetadata = yaml.safe_load(content)
                return data.get("description", "N/A")
            except yaml.YAMLError:
                logger.warning("Failed to parse integration metadata %s", integration_def)

        return "N/A"

    async def _get_actions_ai_descriptions(self) -> str:
        ai_dir: anyio.Path = self.integration / constants.RESOURCES_DIR / constants.AI_DIR
        actions_ai_file: anyio.Path = ai_dir / constants.ACTIONS_AI_DESCRIPTION_FILE
        if await actions_ai_file.exists():
            return await actions_ai_file.read_text(encoding="utf-8")
        return "N/A"
