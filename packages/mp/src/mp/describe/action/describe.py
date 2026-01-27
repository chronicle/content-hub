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

import asyncio
import contextlib
import logging
import pathlib
from typing import TYPE_CHECKING, Any

import anyio
import typer
import yaml
from rich.progress import track

from mp.core import constants
from mp.core.custom_types import RepositoryType
from mp.core.file_utils import (
    create_or_get_out_integrations_dir,
    get_integration_base_folders_paths,
)
from mp.core.gemini import Gemini, GeminiConfig
from mp.core.llm_sdk import LlmSdk

from .data_models.action_ai_metadata import ActionAiMetadata

if TYPE_CHECKING:
    import pathlib
    from collections.abc import AsyncIterator, Callable

    from rich.progress import Progress

    from mp.core.llm_sdk import LlmSdk

logger: logging.Logger = logging.getLogger("mp.describe_action")


class DescribeAction:
    def __init__(
        self,
        integration: str,
        actions: set[str],
        *,
        src: pathlib.Path | None = None,
    ) -> None:
        self.integration_name: str = integration
        self.src: pathlib.Path | None = src
        self.integration: anyio.Path = _get_integration_path(integration, src=src)
        self.actions: set[str] = actions

    async def describe_actions(
        self,
        sem: asyncio.Semaphore | None = None,
        on_action_done: Callable[[], None] | None = None,
        progress: Progress | None = None,
    ) -> None:
        """Describe actions in a given integration.

        Args:
            sem: An optional semaphore to limit concurrent Gemini requests.
            on_action_done: An optional callback called when an action is finished.
            progress: An optional Progress object to use for progress reporting.

        """
        metadata = await self._load_metadata()
        is_built, out_path = await self._get_status_and_out_path()

        if not self.actions:
            self.actions = await self._get_all_actions(is_built=is_built, out_path=out_path)

        async def _process_action(action_name: str) -> tuple[str, ActionAiMetadata | None]:
            try:
                if sem:
                    async with sem:
                        return await self._describe_action_with_error_handling(
                            action_name, out_path, is_built=is_built
                        )
                return await self._describe_action_with_error_handling(
                    action_name, out_path, is_built=is_built
                )
            finally:
                if on_action_done:
                    on_action_done()

        tasks = [_process_action(action) for action in self.actions]

        description = f"Describing actions for {self.integration_name}..."
        if progress:
            task_id = progress.add_task(description, total=len(tasks))
            for coro in asyncio.as_completed(tasks):
                action, description_obj = await coro
                if description_obj is not None:
                    metadata[action] = description_obj.model_dump(mode="json")
                progress.advance(task_id)
            progress.remove_task(task_id)
        else:
            for coro in track(
                asyncio.as_completed(tasks),
                description=description,
                total=len(tasks),
            ):
                action, description_obj = await coro
                if description_obj is not None:
                    metadata[action] = description_obj.model_dump(mode="json")

        await self._save_metadata(metadata)

    async def get_actions_count(self) -> int:
        """Get the number of actions in the integration.

        Returns:
            int: The number of actions.

        """
        if not self.actions:
            is_built, out_path = await self._get_status_and_out_path()
            self.actions = await self._get_all_actions(is_built=is_built, out_path=out_path)
        return len(self.actions)

    async def _get_status_and_out_path(self) -> tuple[bool, anyio.Path]:
        out_path = self._get_out_path()
        is_built = await out_path.exists()

        # If it's not built in the out directory, check if the integration itself is built
        if not is_built:
            def_file = self.integration / constants.INTEGRATION_DEF_FILE.format(
                self.integration_name
            )
            if await def_file.exists():
                is_built = True
                out_path = self.integration
        return is_built, out_path

    async def _describe_action_with_error_handling(
        self, action_name: str, out_path: anyio.Path, *, is_built: bool
    ) -> tuple[str, ActionAiMetadata | None]:
        try:
            desc = await self.describe_action(
                action_name=action_name, is_built=is_built, out_path=out_path
            )
        except Exception:
            logger.exception("Failed to describe action %s", action_name)
            return action_name, None
        else:
            return action_name, desc

    async def _get_all_actions(
        self, *, is_built: bool, out_path: anyio.Path | None = None
    ) -> set[str]:
        actions: set[str] = set()
        if is_built:
            path = (out_path or self._get_out_path()) / constants.OUT_ACTION_SCRIPTS_DIR
        else:
            path = self.integration / constants.ACTIONS_DIR

        if await path.exists():
            async for file in path.glob("*.py"):
                if file.name != "__init__.py":
                    actions.add(file.stem)
        return actions

    async def describe_action(
        self, action_name: str, *, is_built: bool, out_path: anyio.Path | None = None
    ) -> ActionAiMetadata | None:
        """Describe an action of a given integration.

        Returns:
            ActionAiMetadata | None: The AI-generated metadata for the action,
                or None if description failed.

        """
        prompt: str = await PromptConstructor(
            self.integration,
            self.integration_name,
            action_name,
            src=self.src,
            out_path=out_path,
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
        resource_ai_dir: anyio.Path = (
            self.integration / constants.RESOURCES_DIR / constants.AI_FOLDER
        )
        metadata_file: anyio.Path = resource_ai_dir / constants.ACTIONS_AI_DESCRIPTION_FILE
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
        return await self._get_out_path().exists()

    def _get_out_path(self) -> anyio.Path:
        base_out = anyio.Path(create_or_get_out_integrations_dir())
        if self.src:
            return base_out / self.src.name / self.integration_name
        return base_out / self.integration_name


@contextlib.asynccontextmanager
async def _create_llm_session() -> AsyncIterator[LlmSdk]:
    llm_config: GeminiConfig = _create_gemini_config()
    async with Gemini(llm_config) as gemini:
        system_prompt: str = _get_system_prompt()
        gemini.add_system_prompts_to_session(system_prompt)
        yield gemini


def _get_system_prompt() -> str:
    return "You are an expert in analyzing integration code."


def _get_integration_path(name: str, *, src: pathlib.Path | None = None) -> anyio.Path:
    if src:
        path = src / name
        if path.exists():
            return anyio.Path(path)
        logger.error("Integration '%s' not found in source '%s'", name, src)
        raise typer.Exit(1)

    base_paths: list[pathlib.Path] = []
    for repo_type in [RepositoryType.COMMERCIAL, RepositoryType.THIRD_PARTY]:
        base_paths.extend(get_integration_base_folders_paths(repo_type.value))

    for path in base_paths:
        if (p := path / name).exists():
            return anyio.Path(p)

    logger.error("Integration '%s' not found in marketplace", name)
    raise typer.Exit(1)


def _create_gemini_config() -> GeminiConfig:
    return GeminiConfig()


class PromptConstructor:
    __slots__: tuple[str, ...] = ("action_name", "integration", "integration_name", "out_path")

    def __init__(
        self,
        integration: anyio.Path,
        integration_name: str,
        action_name: str,
        *,
        src: pathlib.Path | None = None,
        out_path: anyio.Path | None = None,
    ) -> None:
        self.integration: anyio.Path = integration
        self.integration_name: str = integration_name
        self.action_name: str = action_name
        if out_path:
            self.out_path = out_path
        else:
            base_out = anyio.Path(create_or_get_out_integrations_dir())
            if src:
                self.out_path = base_out / src.name / self.integration_name
            else:
                self.out_path = base_out / self.integration_name

    async def construct_prompt(self, *, is_built: bool) -> str:
        """Construct a prompt for generating action descriptions based on the provided parameters.

        Args:
            is_built (bool): Indicates whether the action is built or not.

        Returns:
            str: The constructed prompt.

        """
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
