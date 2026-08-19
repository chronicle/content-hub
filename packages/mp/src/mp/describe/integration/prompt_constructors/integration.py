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

import contextlib
import json
import logging
import tomllib
from string import Template
from typing import TYPE_CHECKING, Any

import anyio
import yaml

from mp.core import constants
from mp.describe.common.metadata import (
    IntegrationOverridePromptParams,
    build_integration_override_prompt,
)
from mp.describe.common.prompt_constructors.prompt_constructor import PromptConstructor

if TYPE_CHECKING:
    from mp.core.data_models.integrations.integration_meta.metadata import NonBuiltIntegrationMetadata
    from mp.describe.common.metadata import PromptOverrideConfig

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

    async def construct(self, template: Template | None = None) -> str:
        """Construct the prompt for integrations.

        Args:
            template: Optional custom prompt template.

        Returns:
            str: The constructed prompt.

        """
        if template is None:
            template = await self.get_task_prompt()
        integration_description = await self._get_integration_description()
        actions_ai_descriptions = await self._get_actions_ai_descriptions()
        connectors_ai_descriptions = await self._get_connectors_ai_descriptions()
        jobs_ai_descriptions = await self._get_jobs_ai_descriptions()

        result = template.safe_substitute({
            "integration_name": self.integration_name,
            "integration_description": integration_description,
            "actions_ai_descriptions": actions_ai_descriptions,
            "connectors_ai_descriptions": connectors_ai_descriptions,
            "jobs_ai_descriptions": jobs_ai_descriptions,
        })

        if "<integration_description>" not in result:
            context = (
                f"\n\n### INTEGRATION CONTEXT\n\n"
                f"<integration_name>\n{self.integration_name}\n</integration_name>\n\n"
                f"<integration_description>\n{integration_description}\n</integration_description>\n\n"
                f"<actions_ai_descriptions>\n{actions_ai_descriptions}\n</actions_ai_descriptions>\n\n"
                f"<connectors_ai_descriptions>\n{connectors_ai_descriptions}\n</connectors_ai_descriptions>\n\n"
                f"<jobs_ai_descriptions>\n{jobs_ai_descriptions}\n</jobs_ai_descriptions>\n"
            )
            result += context

        return result

    async def construct_override(self, override: PromptOverrideConfig) -> str:
        """Construct the override prompt for integrations.

        Args:
            override: Prompt override configuration.

        Returns:
            str: The constructed override prompt.

        """
        return build_integration_override_prompt(
            IntegrationOverridePromptParams(
                target_field=override.target_field,
                criteria=override.criteria,
                integration_name=self.integration_name,
                integration_description=await self._get_integration_description(),
                actions_ai_descriptions=await self._get_actions_ai_descriptions(),
                connectors_ai_descriptions=await self._get_connectors_ai_descriptions(),
                jobs_ai_descriptions=await self._get_jobs_ai_descriptions(),
            )
        )

    async def _get_integration_description(self) -> str:
        # Try to find the description in various metadata files.
        # Order: .def file (built), definition.yaml (source), pyproject.toml (source)

        # 1. Check for built integration metadata (.def file)
        if desc := await self._get_description_from_def():
            return desc

        # 2. Check for source integration metadata (definition.yaml)
        if desc := await self._get_description_from_definition():
            return desc

        # 3. Check for pyproject.toml (standard PEP 621)
        if desc := await self._get_description_from_pyproject():
            return desc

        return "N/A"

    async def _get_description_from_def(self) -> str | None:
        # Search for any .def file in the root
        async for def_file in self.integration.glob("Integration-*.def"):
            content: str = await def_file.read_text(encoding="utf-8")
            with contextlib.suppress(json.JSONDecodeError):
                data: NonBuiltIntegrationMetadata = json.loads(content)
                if data and "description" in data:
                    return data["description"]

        return None

    async def _get_description_from_definition(self) -> str | None:
        definition_file: anyio.Path = self.integration / constants.DEFINITION_FILE
        if not await definition_file.exists():
            return None

        content: str = await definition_file.read_text(encoding="utf-8")
        try:
            data: NonBuiltIntegrationMetadata = yaml.safe_load(content)
            return data.get("description")
        except yaml.YAMLError:
            logger.warning("Failed to parse definition file %s", definition_file)
            return None

    async def _get_description_from_pyproject(self) -> str | None:
        pyproject_file: anyio.Path = self.integration / constants.PROJECT_FILE
        if not await pyproject_file.exists():
            return None

        content: str = await pyproject_file.read_text(encoding="utf-8")
        with contextlib.suppress(Exception):
            data: dict[str, Any] = tomllib.loads(content)
            if project_data := data.get("project"):
                return project_data.get("description")

        logger.warning("Failed to parse pyproject file %s", pyproject_file)
        return None

    async def _get_actions_ai_descriptions(self) -> str:
        ai_dir: anyio.Path = self.integration / constants.RESOURCES_DIR / constants.AI_DIR
        actions_ai_file: anyio.Path = ai_dir / constants.ACTIONS_AI_DESCRIPTION_FILE
        if await actions_ai_file.exists():
            return await actions_ai_file.read_text(encoding="utf-8")
        return "N/A"

    async def _get_connectors_ai_descriptions(self) -> str:
        ai_dir: anyio.Path = self.integration / constants.RESOURCES_DIR / constants.AI_DIR
        connectors_ai_file: anyio.Path = ai_dir / constants.CONNECTORS_AI_DESCRIPTION_FILE
        if await connectors_ai_file.exists():
            return await connectors_ai_file.read_text(encoding="utf-8")
        return "N/A"

    async def _get_jobs_ai_descriptions(self) -> str:
        ai_dir: anyio.Path = self.integration / constants.RESOURCES_DIR / constants.AI_DIR
        jobs_ai_file: anyio.Path = ai_dir / constants.JOBS_AI_DESCRIPTION_FILE
        if await jobs_ai_file.exists():
            return await jobs_ai_file.read_text(encoding="utf-8")
        return "N/A"
