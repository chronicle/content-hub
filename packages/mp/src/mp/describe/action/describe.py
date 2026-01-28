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
from typing import TYPE_CHECKING, Any, NamedTuple

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
from .prompt_constructors.built import BuiltPromptConstructor
from .prompt_constructors.source import SourcePromptConstructor

if TYPE_CHECKING:
    import pathlib
    from collections.abc import AsyncIterator, Callable

    from rich.progress import Progress

    from mp.core.llm_sdk import LlmSdk


GEMINI_MODEL_NAME: str = "gemini-3-flash-preview"

logger: logging.Logger = logging.getLogger("mp.describe_action")


class IntegrationStatus(NamedTuple):
    is_built: bool
    out_path: anyio.Path


class ActionDescriptionResult(NamedTuple):
    action_name: str
    metadata: ActionAiMetadata | None


def _merge_results(metadata: dict[str, Any], results: list[ActionDescriptionResult]) -> None:
    for result in results:
        if result.metadata is not None:
            metadata[result.action_name] = result.metadata.model_dump(mode="json")


class DescribeAction:
    def __init__(
        self,
        integration: str,
        actions: set[str],
        *,
        src: pathlib.Path | None = None,
        override: bool = False,
    ) -> None:
        self.integration_name: str = integration
        self.src: pathlib.Path | None = src
        self.integration: anyio.Path = _get_integration_path(integration, src=src)
        self.actions: set[str] = actions
        self.override: bool = override

    async def describe_actions(
        self,
        sem: asyncio.Semaphore | None = None,
        on_action_done: Callable[[], None] | None = None,
        progress: Progress | None = None,
    ) -> None:
        """Describe actions in a given integration.

        Args:
            sem: Optional semaphore to limit concurrent Gemini requests.
            on_action_done: An optional callback is called when an action is finished.
            progress: An optional Progress object to use for progress reporting.

        """
        metadata, status = await asyncio.gather(
            self._load_metadata(), self._get_integration_status()
        )

        actions_to_process: set[str] = await self._prepare_actions(status, metadata)
        if not actions_to_process:
            logger.info(
                "All actions in %s already have descriptions. Skipping.", self.integration_name
            )
            return

        results: list[ActionDescriptionResult] = await self._execute_descriptions(
            actions_to_process, status, sem, on_action_done, progress
        )

        _merge_results(metadata, results)
        await self._save_metadata(metadata)

    async def get_actions_count(self) -> int:
        """Get the number of actions in the integration.

        Returns:
            int: The number of actions.

        """
        status, metadata = await asyncio.gather(
            self._get_integration_status(), self._load_metadata()
        )
        actions: set[str] = await self._prepare_actions(status, metadata)
        return len(actions)

    async def _prepare_actions(
        self, status: IntegrationStatus, metadata: dict[str, Any]
    ) -> set[str]:
        if not self.actions:
            self.actions = await self._get_all_actions(status)

        if not self.override:
            original_count: int = len(self.actions)
            self.actions = {action for action in self.actions if action not in metadata}
            if len(self.actions) < original_count:
                logger.info(
                    "Skipping %d actions that already have a description in %s",
                    original_count - len(self.actions),
                    self.integration_name,
                )

        return self.actions

    async def _execute_descriptions(
        self,
        actions: set[str],
        status: IntegrationStatus,
        sem: asyncio.Semaphore | None = None,
        on_action_done: Callable[[], None] | None = None,
        progress: Progress | None = None,
    ) -> list[ActionDescriptionResult]:
        tasks: list[asyncio.Task] = [
            asyncio.create_task(self._process_single_action(action, status, sem, on_action_done))
            for action in actions
        ]
        description = f"Describing actions for {self.integration_name}..."

        results: list[ActionDescriptionResult] = []
        if progress:
            task_id = progress.add_task(description, total=len(tasks))
            for coro in asyncio.as_completed(tasks):
                results.append(await coro)
                progress.advance(task_id)
            progress.remove_task(task_id)
        else:
            results.extend([
                await coro
                for coro in track(
                    asyncio.as_completed(tasks),
                    description=description,
                    total=len(tasks),
                )
            ])

        return results

    async def _process_single_action(
        self,
        action_name: str,
        status: IntegrationStatus,
        sem: asyncio.Semaphore | None = None,
        on_action_done: Callable[[], None] | None = None,
    ) -> ActionDescriptionResult:
        try:
            if sem:
                async with sem:
                    return await self._describe_action_with_error_handling(action_name, status)
            return await self._describe_action_with_error_handling(action_name, status)
        finally:
            if on_action_done:
                on_action_done()

    async def _get_integration_status(self) -> IntegrationStatus:
        out_path: anyio.Path = self._get_out_path()
        is_built: bool = await out_path.exists()

        # If it's not built in the out directory, check if the integration itself is built
        if not is_built:
            def_file: anyio.Path = self.integration / constants.INTEGRATION_DEF_FILE.format(
                self.integration_name
            )
            if await def_file.exists():
                is_built = True
                out_path: anyio.Path = self.integration

        return IntegrationStatus(is_built=is_built, out_path=out_path)

    async def _describe_action_with_error_handling(
        self, action_name: str, status: IntegrationStatus
    ) -> ActionDescriptionResult:
        try:
            desc = await self.describe_action(action_name=action_name, status=status)
        except Exception:
            logger.exception("Failed to describe action %s", action_name)
            return ActionDescriptionResult(action_name, None)
        else:
            return ActionDescriptionResult(action_name, desc)

    async def _get_all_actions(self, status: IntegrationStatus) -> set[str]:
        actions: set[str] = set()
        if status.is_built:
            path = status.out_path / constants.OUT_ACTION_SCRIPTS_DIR
        else:
            path = self.integration / constants.ACTIONS_DIR

        if await path.exists():
            async for file in path.glob("*.py"):
                if file.name != "__init__.py":
                    actions.add(file.stem)
        return actions

    async def describe_action(
        self, action_name: str, status: IntegrationStatus
    ) -> ActionAiMetadata | None:
        """Describe an action of a given integration.

        Returns:
            ActionAiMetadata | None: The AI-generated metadata for the action,
                or None if description failed.

        """
        constructor: BuiltPromptConstructor | SourcePromptConstructor = _create_prompt_constructor(
            integration=self.integration,
            integration_name=self.integration_name,
            action_name=action_name,
            status=status,
        )
        prompt: str = await constructor.construct()
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
        resource_ai_dir: anyio.Path = (
            self.integration / constants.RESOURCES_DIR / constants.AI_FOLDER
        )
        await resource_ai_dir.mkdir(parents=True, exist_ok=True)
        metadata_file: anyio.Path = resource_ai_dir / constants.ACTIONS_AI_DESCRIPTION_FILE
        await metadata_file.write_text(yaml.dump(metadata))

    def _get_out_path(self) -> anyio.Path:
        base_out: anyio.Path = anyio.Path(create_or_get_out_integrations_dir())
        if self.src:
            return base_out / self.src.name / self.integration_name
        return base_out / self.integration_name


@contextlib.asynccontextmanager
async def _create_llm_session() -> AsyncIterator[LlmSdk]:
    llm_config: GeminiConfig = _create_gemini_config()
    async with Gemini(llm_config) as gemini:
        system_prompt: str = await _get_system_prompt()
        gemini.add_system_prompts_to_session(system_prompt)
        yield gemini


async def _get_system_prompt() -> str:
    path: anyio.Path = anyio.Path(__file__).parent / "prompts" / "system.md"
    return await path.read_text(encoding="utf-8")


def _get_integration_path(name: str, *, src: pathlib.Path | None = None) -> anyio.Path:
    if src:
        return _get_source_integration_path(name, src)
    return _get_marketplace_integration_path(name)


def _get_source_integration_path(name: str, src: pathlib.Path) -> anyio.Path:
    path = src / name
    if path.exists():
        return anyio.Path(path)
    logger.error("Integration '%s' not found in source '%s'", name, src)
    raise typer.Exit(1)


def _get_marketplace_integration_path(name: str) -> anyio.Path:
    base_paths: list[pathlib.Path] = []
    for repo_type in [RepositoryType.COMMERCIAL, RepositoryType.THIRD_PARTY]:
        base_paths.extend(get_integration_base_folders_paths(repo_type.value))

    for path in base_paths:
        if (p := path / name).exists():
            return anyio.Path(p)

    logger.error("Integration '%s' not found in marketplace", name)
    raise typer.Exit(1)


def _create_gemini_config() -> GeminiConfig:
    return GeminiConfig(model_name=GEMINI_MODEL_NAME)


def _create_prompt_constructor(
    integration: anyio.Path,
    integration_name: str,
    action_name: str,
    status: IntegrationStatus,
) -> BuiltPromptConstructor | SourcePromptConstructor:
    """Create the object.

    Returns:
        PromptConstructor: The constructed object.

    """
    if status.is_built:
        return BuiltPromptConstructor(integration, integration_name, action_name, status.out_path)
    return SourcePromptConstructor(integration, integration_name, action_name, status.out_path)
