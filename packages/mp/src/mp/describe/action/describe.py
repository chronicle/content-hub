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

import json
import logging
from typing import TYPE_CHECKING, Any

import anyio
import yaml

from mp.core import constants
from mp.core.data_models.integrations.action.ai.metadata import ActionAiMetadata
from mp.describe.common.describe import (
    DescribeBase,
    DescriptionParams,
    DescriptionResult,
    IntegrationStatus,
)
from mp.describe.common.metadata import (
    PromptOverrideConfig,
    parse_prompt_overrides_content,
)
from mp.describe.common.utils import llm

from .metadata import (
    FIELD_TO_OVERRIDE_MODEL,
)
from .prompt_constructors.built import BuiltPromptConstructor
from .prompt_constructors.source import SourcePromptConstructor
from .utils import create_dynamic_field_model, format_display_value

if TYPE_CHECKING:
    import asyncio
    import pathlib
    from collections.abc import Callable

    from pydantic import BaseModel
    from rich.progress import Progress

    from mp.core.data_models.integrations.action.metadata import BuiltActionMetadata, NonBuiltActionMetadata

logger: logging.Logger = logging.getLogger(__name__)

__all__: tuple[str, ...] = ("DescribeAction", "DescriptionParams", "MultiPromptDescribeAction")


class DescribeAction(DescribeBase[ActionAiMetadata]):
    def __init__(
        self,
        integration: str,
        actions: set[str],
        *,
        src: pathlib.Path | None = None,
        dst: pathlib.Path | None = None,
        override: bool = False,
    ) -> None:
        super().__init__(integration, actions, src=src, dst=dst, override=override)
        self._action_name_to_file_stem: dict[str, str] = {}

    @property
    def metadata_file_name(self) -> str:
        """Name of the metadata file."""
        return constants.ACTIONS_AI_DESCRIPTION_FILE

    @property
    def resource_type_name(self) -> str:
        """The resource type name."""
        return "action"

    @property
    def response_schema(self) -> type[ActionAiMetadata]:
        """The response schema."""
        return ActionAiMetadata

    async def describe_actions(
        self,
        sem: asyncio.Semaphore | None = None,
        on_done: Callable[[], None] | None = None,
        progress: Progress | None = None,
    ) -> None:
        """Describe actions (compatibility method)."""
        # Compatibility method
        await self.describe(sem=sem, on_done=on_done, progress=progress)

    async def get_actions_count(self) -> int:
        """Get actions' count (compatibility method).

        Returns:
            int: The number of actions.

        """
        # Compatibility method
        return await self.get_resources_count()

    async def _get_all_resources(self, status: IntegrationStatus) -> set[str]:
        actions: set[str] = set()
        if status.is_built:
            await self._get_all_built_actions(status.out_path, actions)
        else:
            await self._get_all_non_built_actions(actions)
        return actions

    async def _get_all_built_actions(self, out_path: anyio.Path, actions: set[str]) -> None:
        path: anyio.Path = out_path / constants.OUT_ACTIONS_META_DIR
        if await path.exists():
            async for file in path.glob(f"*{constants.ACTIONS_META_SUFFIX}"):
                content: str = await file.read_text(encoding="utf-8")
                try:
                    data: BuiltActionMetadata = json.loads(content)
                    name: str = data["Name"]
                    self._action_name_to_file_stem[name] = file.stem
                    actions.add(name)
                except (json.JSONDecodeError, KeyError):
                    logger.warning("Failed to parse built action metadata %s", file.name)

    async def _get_all_non_built_actions(self, actions: set[str]) -> None:
        path: anyio.Path = self.integration / constants.ACTIONS_DIR
        if await path.exists():
            async for file in path.glob(f"*{constants.YAML_SUFFIX}"):
                content: str = await file.read_text(encoding="utf-8")
                try:
                    data: NonBuiltActionMetadata = yaml.safe_load(content)
                    name: str = data["name"]
                    self._action_name_to_file_stem[name] = file.stem
                    actions.add(name)
                except (yaml.YAMLError, KeyError):
                    logger.warning("Failed to parse non-built action metadata %s", file.name)

    async def _construct_prompts(self, resources: list[str], status: IntegrationStatus) -> list[str]:
        prompts: list[str] = []
        for action_name in resources:
            params = DescriptionParams(
                self.integration,
                self.integration_name,
                action_name,
                self._action_name_to_file_stem.get(action_name, action_name),
                status,
            )
            constructor: BuiltPromptConstructor | SourcePromptConstructor = _create_prompt_constructor(params)
            prompts.append(await constructor.construct())
        return prompts


def _create_prompt_constructor(
    params: DescriptionParams,
) -> BuiltPromptConstructor | SourcePromptConstructor:
    if params.status.is_built:
        return BuiltPromptConstructor(
            params.integration,
            params.integration_name,
            params.action_name,
            params.action_file_name,
            params.status.out_path,
        )
    return SourcePromptConstructor(
        params.integration,
        params.integration_name,
        params.action_name,
        params.action_file_name,
        params.status.out_path,
    )


class MultiPromptDescribeAction(DescribeAction):
    def __init__(  # ruff:ignore[too-many-arguments]
        self,
        integration: str,
        actions: set[str],
        *,
        src: pathlib.Path | None = None,
        dst: pathlib.Path | None = None,
        override: bool = False,
        prompt_overrides: pathlib.Path | None = None,
    ) -> None:
        super().__init__(integration, actions, src=src, dst=dst, override=override)
        self.prompt_overrides_path: pathlib.Path | None = prompt_overrides

    async def describe_bulk(
        self,
        resources: list[str],
        status: IntegrationStatus,
    ) -> list[DescriptionResult]:
        """Describe multiple action resources in bulk with optional prompt overrides.

        Args:
            resources: Action resource names to describe.
            status: Status of the integration content build.

        Returns:
            list[DescriptionResult]: The list of action description results.

        """
        baseline_results: list[DescriptionResult] = await super().describe_bulk(resources, status)

        if not self.prompt_overrides_path:
            return baseline_results

        overrides: list[PromptOverrideConfig] = await self._load_prompt_overrides()
        if not overrides:
            return baseline_results

        return await self._apply_prompt_overrides(resources, status, baseline_results, overrides)

    async def _load_prompt_overrides(self) -> list[PromptOverrideConfig]:
        """Load and parse prompt overrides configuration from YAML or JSON file.

        Returns:
            list[PromptOverrideConfig]: List of prompt override configuration items.

        Raises:
            FileNotFoundError: If the configured prompt overrides file does not exist.
            ValueError: If the prompt overrides file contains invalid YAML/JSON.

        """
        if not self.prompt_overrides_path:
            return []

        path: anyio.Path = anyio.Path(self.prompt_overrides_path)
        if not await path.exists():
            error_msg = f"Prompt overrides file '{self.prompt_overrides_path}' does not exist."
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            content: str = await path.read_text(encoding="utf-8")
            return parse_prompt_overrides_content(content)
        except Exception as exc:
            error_msg = f"Failed to parse prompt overrides file '{self.prompt_overrides_path}': {exc}"
            logger.exception(error_msg)
            raise ValueError(error_msg) from exc

    async def _construct_custom_prompts(
        self, resources: list[str], status: IntegrationStatus, override: PromptOverrideConfig
    ) -> list[str]:
        """Construct custom prompts for actions using a prompt override configuration.

        Args:
            resources: Action resource names to construct prompts for.
            status: Status of the integration content build.
            override: Prompt override configuration.

        Returns:
            list[str]: Formatted custom prompt strings for each action.

        """
        prompts: list[str] = []
        for action_name in resources:
            params = DescriptionParams(
                self.integration,
                self.integration_name,
                action_name,
                self._action_name_to_file_stem.get(action_name, action_name),
                status,
            )
            constructor: BuiltPromptConstructor | SourcePromptConstructor = _create_prompt_constructor(params)
            prompts.append(await constructor.construct_override(override))
        return prompts

    async def _apply_prompt_overrides(
        self,
        resources: list[str],
        status: IntegrationStatus,
        baseline_results: list[DescriptionResult],
        overrides: list[PromptOverrideConfig],
    ) -> list[DescriptionResult]:
        """Apply custom prompt overrides sequentially to baseline description results.

        Args:
            resources: Action resource names to describe.
            status: Status of the integration content build.
            baseline_results: Baseline action description results.
            overrides: Parsed list of prompt override configurations.

        Returns:
            list[DescriptionResult]: Updated action description results with field overrides applied.

        """
        name_to_idx: dict[str, int] = {res.name: i for i, res in enumerate(baseline_results)}
        results: list[DescriptionResult] = list(baseline_results)

        for override in overrides:
            target_model: type[BaseModel] | None = FIELD_TO_OVERRIDE_MODEL.get(override.target_field)
            if target_model is None:
                target_model = create_dynamic_field_model(override.target_field, override.schema_def)

            logger.debug(
                "Applying prompt override for field '%s'",
                override.target_field,
            )

            custom_prompts: list[str] = await self._construct_custom_prompts(resources, status, override)
            valid_indices: list[int] = [i for i, prompt in enumerate(custom_prompts) if prompt]
            valid_prompts: list[str] = [custom_prompts[i] for i in valid_indices]

            if not valid_prompts:
                continue

            llm_results: list[Any | str] = await llm.call_gemini_bulk(valid_prompts, target_model)

            for i, result in zip(valid_indices, llm_results, strict=True):
                resource_name: str = resources[i]
                if isinstance(result, str):
                    logger.error(
                        "Failed custom describe for action %s field %s: %s",
                        resource_name,
                        override.target_field,
                        result,
                    )
                    continue

                idx = name_to_idx.get(resource_name)
                if idx is None:
                    continue

                curr_meta = results[idx].metadata
                if curr_meta is None:
                    continue

                override_val = getattr(result, override.target_field, None)
                if override_val is None:
                    continue

                logger.debug(
                    "Successfully overridden field '%s' for action '%s' with LLM response:\n%s",
                    override.target_field,
                    resource_name,
                    format_display_value(override_val),
                )

                updated_meta = curr_meta.model_copy(update={override.target_field: override_val})
                results[idx] = DescriptionResult(resource_name, updated_meta)

        return results
