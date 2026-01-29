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
from typing import TYPE_CHECKING, Any, NamedTuple, TypeAlias

import anyio
import yaml
from rich.progress import TaskID, track

from mp.core import constants

from .data_models.action_ai_metadata import ActionAiMetadata
from .prompt_constructors.built import BuiltPromptConstructor
from .prompt_constructors.source import SourcePromptConstructor
from .utils import llm, paths

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from rich.progress import Progress


logger: logging.Logger = logging.getLogger("mp.describe_action")
_PromptConstructor: TypeAlias = BuiltPromptConstructor | SourcePromptConstructor


class IntegrationStatus(NamedTuple):
    is_built: bool
    out_path: anyio.Path


class ActionDescriptionResult(NamedTuple):
    action_name: str
    metadata: ActionAiMetadata | None


class RichParams(NamedTuple):
    """Parameters for rich progress reporting and callbacks."""

    on_action_done: Callable[[], None] | None = None
    progress: Progress | None = None
    task_id: TaskID | None = None


class DescriptionParams(NamedTuple):
    """Parameters required to construct an action prompt."""

    integration: anyio.Path
    integration_name: str
    action_name: str
    status: IntegrationStatus


def _merge_results(metadata: dict[str, Any], results: list[ActionDescriptionResult]) -> None:
    for result in results:
        if result.metadata is not None:
            metadata[result.action_name] = result.metadata.model_dump(mode="json")


def _create_notifier(rich_params: RichParams) -> Callable[[], None]:
    """Create a notifier function to handle progress and callbacks.

    Args:
        rich_params: Progress and callback parameters.

    Returns:
        Callable[[], None]: A function that advances progress and calls the callback.

    """

    def notify() -> None:
        if rich_params.on_action_done:
            rich_params.on_action_done()
        if rich_params.progress and rich_params.task_id:
            rich_params.progress.advance(rich_params.task_id)

    return notify


def _map_bulk_results_to_actions(
    actions: list[str],
    valid_indices: list[int],
    results: list[ActionAiMetadata | str],
) -> list[ActionDescriptionResult]:
    """Map Gemini results back to action names.

    Args:
        actions: Original list of action names.
        valid_indices: Indices of actions that had valid prompts.
        results: Results from Gemini for those valid prompts.

    Returns:
        list[ActionDescriptionResult]: Mapped results.

    """
    final_results = [ActionDescriptionResult(a, None) for a in actions]
    for i, result in zip(valid_indices, results, strict=False):
        final_results[i] = ActionDescriptionResult(
            actions[i], result if isinstance(result, ActionAiMetadata) else None
        )
    return final_results


class DescribeAction:
    def __init__(
        self,
        integration: str,
        actions: set[str],
        *,
        src: anyio.Path | None = None,
        dst: anyio.Path | None = None,
        override: bool = False,
    ) -> None:
        self.integration_name: str = integration
        self.src: anyio.Path | None = src
        self.dst: anyio.Path | None = dst
        self.integration: anyio.Path = paths.get_integration_path(integration, src=src)
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

        if len(actions_to_process) == 1:
            logger.info(
                "Describing action %s for %s",
                next(iter(actions_to_process)),
                self.integration_name,
            )
        else:
            logger.info(
                "Describing %d actions for %s",
                len(actions_to_process),
                self.integration_name,
            )

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
            skipped_count: int = original_count - len(self.actions)
            if skipped_count > 0:
                if skipped_count == 1:
                    logger.info(
                        "Skipping 1 action that already has a description in %s",
                        self.integration_name,
                    )
                else:
                    logger.info(
                        "Skipping %d actions that already have a description in %s",
                        skipped_count,
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
        action_list: list[str] = list(actions)
        bulks: list[list[str]] = [
            action_list[i : i + llm.DESCRIBE_BULK_SIZE]
            for i in range(0, len(action_list), llm.DESCRIBE_BULK_SIZE)
        ]

        if len(actions) == 1:
            description = f"Describing action {next(iter(actions))} for {self.integration_name}..."
        else:
            description = f"Describing actions for {self.integration_name}..."

        results: list[ActionDescriptionResult] = []

        if progress:
            task_id = progress.add_task(description, total=len(actions))
            rich_params = RichParams(on_action_done, progress, task_id)
            tasks: list[asyncio.Task] = [
                asyncio.create_task(self._process_bulk_actions(bulk, status, sem, rich_params))
                for bulk in bulks
            ]
            for coro in asyncio.as_completed(tasks):
                results.extend(await coro)
            progress.remove_task(task_id)

        else:
            rich_params = RichParams(on_action_done)
            tasks: list[asyncio.Task] = [
                asyncio.create_task(self._process_bulk_actions(bulk, status, sem, rich_params))
                for bulk in bulks
            ]
            results.extend([
                res
                for bulk_res in track(
                    asyncio.as_completed(tasks),
                    description=description,
                    total=len(bulks),
                )
                for res in await bulk_res
            ])

        return results

    async def _process_bulk_actions(
        self,
        actions: list[str],
        status: IntegrationStatus,
        sem: asyncio.Semaphore | None = None,
        rich_params: RichParams | None = None,
    ) -> list[ActionDescriptionResult]:
        if rich_params is None:
            rich_params = RichParams()

        notify_done: Callable[[], None] = _create_notifier(rich_params)
        try:
            async with _maybe_use_semaphore(sem):
                return await self._describe_actions_bulk_with_error_handling(
                    actions, status, notify_done
                )

        except Exception:
            logger.exception("Failed to process bulk of actions: %s", actions)
            for _ in actions:
                notify_done()

            return [ActionDescriptionResult(a, None) for a in actions]

    async def _describe_actions_bulk_with_error_handling(
        self,
        actions: list[str],
        status: IntegrationStatus,
        notify_done: Callable[[], None],
    ) -> list[ActionDescriptionResult]:
        try:
            results: list[ActionDescriptionResult] = await self.describe_actions_bulk(
                actions, status
            )
        except Exception:
            logger.exception("Failed to describe actions bulk %s", actions)
            results: list[ActionDescriptionResult] = [
                ActionDescriptionResult(a, None) for a in actions
            ]

        for _ in actions:
            notify_done()

        return results

    async def describe_actions_bulk(
        self,
        actions: list[str],
        status: IntegrationStatus,
    ) -> list[ActionDescriptionResult]:
        """Describe multiple actions of a given integration in bulk.

        Args:
            actions: The names of the actions to describe.
            status: The status of the integration.

        Returns:
            list[ActionDescriptionResult]: The AI-generated metadata for the actions.

        """
        prompts: list[str] = await self._construct_prompts(actions, status)

        valid_indices: list[int] = [i for i, p in enumerate(prompts) if p]
        valid_prompts: list[str] = [prompts[i] for i in valid_indices]

        if not valid_prompts:
            return [ActionDescriptionResult(a, None) for a in actions]

        results: list[ActionAiMetadata | str] = await llm.call_gemini_bulk(valid_prompts)
        return _map_bulk_results_to_actions(actions, valid_indices, results)

    async def _construct_prompts(self, actions: list[str], status: IntegrationStatus) -> list[str]:
        """Construct prompts for a list of actions.

        Args:
            actions: Names of actions.
            status: Integration status.

        Returns:
            list[str]: List of constructed prompts.

        """
        prompts: list[str] = []
        for action_name in actions:
            params = DescriptionParams(
                integration=self.integration,
                integration_name=self.integration_name,
                action_name=action_name,
                status=status,
            )
            constructor: _PromptConstructor = _create_prompt_constructor(params)
            prompt: str = await constructor.construct()
            if not prompt:
                logger.warning("Could not construct prompt for action %s", action_name)
                prompts.append("")
            else:
                prompts.append(prompt)
        return prompts

    async def _get_integration_status(self) -> IntegrationStatus:
        out_path: anyio.Path = paths.get_out_path(self.integration_name, src=self.src)
        is_built: bool = await out_path.exists()

        # If it's not built in the out directory, check if the integration itself is built
        if not is_built:
            def_file: anyio.Path = self.integration / constants.INTEGRATION_DEF_FILE.format(
                self.integration_name
            )
            if await def_file.exists():
                is_built = True
                out_path = self.integration

        return IntegrationStatus(is_built=is_built, out_path=out_path)

    async def _get_all_actions(self, status: IntegrationStatus) -> set[str]:
        actions: set[str] = set()
        if status.is_built:
            path: anyio.Path = status.out_path / constants.OUT_ACTION_SCRIPTS_DIR
        else:
            path: anyio.Path = self.integration / constants.ACTIONS_DIR

        if await path.exists():
            async for file in path.glob("*.py"):
                if file.name != "__init__.py":
                    actions.add(file.stem)
        return actions

    async def _load_metadata(self) -> dict[str, Any]:
        metadata: dict[str, Any] = {}

        # Load from integration folder
        resource_ai_dir: anyio.Path = (
            self.integration / constants.RESOURCES_DIR / constants.AI_FOLDER
        )
        metadata_file: anyio.Path = resource_ai_dir / constants.ACTIONS_AI_DESCRIPTION_FILE
        if await metadata_file.exists():
            content: str = await metadata_file.read_text()
            with contextlib.suppress(yaml.YAMLError):
                metadata = yaml.safe_load(content) or {}

        # Load from dst folder if provided (overwrites integration metadata)
        if self.dst:
            dst_metadata_file: anyio.Path = (
                anyio.Path(self.dst) / constants.ACTIONS_AI_DESCRIPTION_FILE
            )
            if await dst_metadata_file.exists():
                content = await dst_metadata_file.read_text()
                with contextlib.suppress(yaml.YAMLError):
                    dst_metadata = yaml.safe_load(content) or {}
                    metadata.update(dst_metadata)

        return metadata

    async def _save_metadata(self, metadata: dict[str, Any]) -> None:
        if self.dst:
            resource_ai_dir = anyio.Path(self.dst)
        else:
            resource_ai_dir = self.integration / constants.RESOURCES_DIR / constants.AI_FOLDER

        await resource_ai_dir.mkdir(parents=True, exist_ok=True)
        metadata_file: anyio.Path = resource_ai_dir / constants.ACTIONS_AI_DESCRIPTION_FILE
        await metadata_file.write_text(yaml.dump(metadata))


def _create_prompt_constructor(
    params: DescriptionParams,
) -> BuiltPromptConstructor | SourcePromptConstructor:
    """Create the object.

    Returns:
        PromptConstructor: The constructed object.

    """
    if params.status.is_built:
        return BuiltPromptConstructor(
            params.integration, params.integration_name, params.action_name, params.status.out_path
        )
    return SourcePromptConstructor(
        params.integration, params.integration_name, params.action_name, params.status.out_path
    )


@contextlib.asynccontextmanager
async def _maybe_use_semaphore(sem: asyncio.Semaphore | None) -> AsyncIterator[None]:
    """Use a context manager that optionally uses semaphore.

    Args:
        sem: The semaphore to use, or None.

    Yields:
        None: When the semaphore is acquired or if no semaphore is provided.

    """
    if sem:
        async with sem:
            yield
    else:
        yield
