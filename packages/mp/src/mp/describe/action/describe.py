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
import contextlib
import dataclasses
import itertools
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

import anyio
import typer
import yaml
from click.decorators import T
from rich.logging import RichHandler
from rich.progress import track

from mp.core import constants
from mp.core.custom_types import RepositoryType
from mp.core.file_utils import create_or_get_out_integrations_dir, get_integrations_repo_base_path
from mp.core.gemini import Gemini, GeminiConfig
from mp.core.llm_sdk import LlmSdk

from .data_models.action_ai_metadata import ActionAiMetadata

if TYPE_CHECKING:
    import pathlib

logger: logging.Logger = logging.getLogger("mp.describe_action")
logging.basicConfig(level="INFO", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])


class DescribeAction:
    def __init__(self, integration: str, actions: set[str]) -> None:
        self.integration_name: str = integration
        self.integration: anyio.Path = _get_integration_path(integration)
        self.actions: set[str] = actions

    async def describe_actions(self) -> None:
        """Describe actions in a given integration."""
        metadata = await self._load_metadata()
        is_built = await self._is_built()

        for action in track(
            self.actions, description=f"Describing actions for {self.integration_name}..."
        ):
            try:
                description: ActionAiMetadata | None = await self.describe_action(
                    action_name=action,
                    is_built=is_built,
                )
                if description is not None:
                    metadata[action] = description.model_dump(mode="json")
            except Exception:
                logger.exception("Failed to describe action %s", action)

        await self._save_metadata(metadata)

    async def describe_action(self, action_name: str, *, is_built: bool) -> ActionAiMetadata | None:
        """Describe an action of a given integration.

        Returns:
            ActionAiMetadata | None: The AI-generated metadata for the action,
                or None if description failed.

        """
        prompt: str = await PromptConstructor(
            self.integration, self.integration_name, action_name
        ).construct_prompt(is_built=is_built)
        if not prompt:
            logger.warning("Could not construct prompt for action %s", action_name)
            return None

        async with _create_llm_session() as gemini:
            return await gemini.send_message(
                prompt,
                response_json_schema=ActionAiMetadata,
                raise_error_if_empty_response=True,
            )

    async def _load_metadata(self) -> dict[str, Any]:
        resource_ai_dir: anyio.Path = self.integration / constants.RESOURCES_DIR / "ai"
        metadata_file: anyio.Path = resource_ai_dir / "ai_description.yaml"
        if await metadata_file.exists():
            content: str = await metadata_file.read_text()
            try:
                return yaml.safe_load(content) or {}
            except yaml.YAMLError:
                return {}

        return {}

    async def _save_metadata(self, metadata: dict[str, Any]) -> None:
        resource_ai_dir = self.integration / constants.RESOURCES_DIR / "ai"
        await resource_ai_dir.mkdir(parents=True, exist_ok=True)
        metadata_file = resource_ai_dir / "ai_description.yaml"
        await metadata_file.write_text(yaml.dump(metadata))

    async def _is_built(self) -> bool:
        out_path = anyio.Path(create_or_get_out_integrations_dir()) / self.integration_name
        return await out_path.exists()


@contextlib.asynccontextmanager
async def _create_llm_session() -> AsyncIterator[LlmSdk]:
    llm_config: GeminiConfig = _create_gemini_config()
    async with Gemini(llm_config) as gemini:
        system_prompt: str = _get_system_prompt()
        gemini.add_system_prompts_to_session(system_prompt)
        yield gemini


def _get_system_prompt() -> str:
    return "You are an expert in analyzing integration code."


def _get_integration_path(name: str) -> anyio.Path:
    mp_paths: itertools.chain[pathlib.Path] = itertools.chain(
        get_integrations_repo_base_path(RepositoryType.COMMERCIAL).iterdir(),
        (
            get_integrations_repo_base_path(RepositoryType.THIRD_PARTY)
            / constants.COMMUNITY_DIR_NAME
        ).iterdir(),
    )
    for path in mp_paths:
        if (i := path / name).exists():
            return anyio.Path(i)

    logger.error("Integration '%s' not found in marketplace", name)
    raise typer.Exit(1)


def _create_gemini_config() -> GeminiConfig:
    return GeminiConfig()


class PromptConstructor:
    __slots__: tuple[str, ...] = ("action_name", "integration", "integration_name", "out_path")

    def __init__(self, integration: anyio.Path, integration_name: str, action_name: str) -> None:
        self.integration: anyio.Path = integration
        self.integration_name: str = integration_name
        self.action_name: str = action_name
        self.out_path = anyio.Path(create_or_get_out_integrations_dir()) / self.integration_name

    async def construct_prompt(self, *, is_built: bool) -> str:
        prompt_parts: list[str] = []

        if is_built:
            prompt_parts.extend(await self._create_managers_prompt())
            prompt_parts.extend(await self._create_built_action_prompt())
            prompt_parts.extend(await self._create_built_action_def_prompt())

        else:
            prompt_parts.extend(await self._create_core_packages_prompt())
            prompt_parts.extend(await self._create_non_built_action_prompt())
            prompt_parts.extend(await self._create_non_built_action_def_prompt())

        return "\n\n".join(prompt_parts)

    async def _create_managers_prompt(self) -> list[str]:
        prompt_parts: list[str] = []
        managers_dir: anyio.Path = self.out_path / constants.OUT_MANAGERS_SCRIPTS_DIR
        if await managers_dir.exists():
            async for manager_file in managers_dir.glob("*.py"):
                content: str = await manager_file.read_text()
                prompt_parts.append(f"Manager {manager_file.name}:\n{content}")

        return prompt_parts

    async def _create_built_action_prompt(self) -> list[str]:
        prompt_parts: list[str] = []
        action_script: anyio.Path = (
            self.out_path / constants.OUT_ACTION_SCRIPTS_DIR / f"{self.action_name}.py"
        )
        if await action_script.exists():
            content: str = await action_script.read_text()
            prompt_parts.append(f"Action Script:\n{content}")

        return prompt_parts

    async def _create_built_action_def_prompt(self) -> list[str]:
        prompt_parts: list[str] = []
        action_def: anyio.Path = (
            self.out_path
            / constants.OUT_ACTIONS_META_DIR
            / f"{self.action_name}{constants.ACTIONS_META_SUFFIX}"
        )
        if await action_def.exists():
            content: str = await action_def.read_text()
            prompt_parts.append(f"Action Definition:\n{content}")

        return prompt_parts

    async def _create_core_packages_prompt(self) -> list[str]:
        prompt_parts: list[str] = []
        core_dir: anyio.Path = self.integration / constants.CORE_SCRIPTS_DIR
        if await core_dir.exists():
            async for core_file in core_dir.glob("*.py"):
                content: str = await core_file.read_text()
                prompt_parts.append(f"Core {core_file.name}:\n{content}")

        return prompt_parts

    async def _create_non_built_action_prompt(self) -> list[str]:
        prompt_parts: list[str] = []
        action_script: anyio.Path = (
            self.integration / constants.ACTIONS_DIR / f"{self.action_name}.py"
        )
        if await action_script.exists():
            content: str = await action_script.read_text()
            prompt_parts.append(f"Action Script:\n{content}")

        return prompt_parts

    async def _create_non_built_action_def_prompt(self) -> list[str]:
        prompt_parts: list[str] = []
        action_yaml: anyio.Path = (
            self.integration / constants.ACTIONS_DIR / f"{self.action_name}{constants.YAML_SUFFIX}"
        )
        if await action_yaml.exists():
            content: str = await action_yaml.read_text()
            prompt_parts.append(f"Action YAML:\n{content}")

        return prompt_parts
