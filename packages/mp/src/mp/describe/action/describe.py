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
from typing import TYPE_CHECKING, Any, NamedTuple

import yaml

from mp.core import constants
from mp.core.data_models.integrations.action.ai.metadata import ActionAiMetadata
from mp.describe.common.describe import DescribeBase, IntegrationStatus

from .prompt_constructors.built import BuiltPromptConstructor
from .prompt_constructors.source import SourcePromptConstructor

if TYPE_CHECKING:
    import pathlib

    import anyio

    from mp.core.data_models.integrations.action.metadata import (
        BuiltActionMetadata,
        NonBuiltActionMetadata,
    )

logger: logging.Logger = logging.getLogger(__name__)


class DescriptionParams(NamedTuple):
    integration: anyio.Path
    integration_name: str
    action_name: str
    action_file_name: str
    status: IntegrationStatus


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
        """Get the name of the metadata file."""
        return constants.ACTIONS_AI_DESCRIPTION_FILE

    @property
    def resource_type_name(self) -> str:
        """Get the resource type name."""
        return "action"

    @property
    def response_schema(self) -> type[ActionAiMetadata]:
        """Get the response schema."""
        return ActionAiMetadata

    async def describe_actions(self, **kwargs: Any) -> None:  # noqa: ANN401
        """Describe actions (compatibility method)."""
        # Compatibility method
        await self.describe(**kwargs)

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

    async def _construct_prompts(
        self, resources: list[str], status: IntegrationStatus
    ) -> list[str]:
        prompts: list[str] = []
        for action_name in resources:
            params = DescriptionParams(
                self.integration,
                self.integration_name,
                action_name,
                self._action_name_to_file_stem.get(action_name, action_name),
                status,
            )
            constructor: BuiltPromptConstructor | SourcePromptConstructor = (
                _create_prompt_constructor(params)
            )
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
