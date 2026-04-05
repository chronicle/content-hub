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
from typing import TYPE_CHECKING, NamedTuple

import yaml

from mp.core import constants
from mp.core.data_models.integrations.connector.ai.metadata import ConnectorAiMetadata
from mp.describe.common.describe import DescribeBase, IntegrationStatus

from .prompt_constructors.built import BuiltPromptConstructor
from .prompt_constructors.source import SourcePromptConstructor

if TYPE_CHECKING:
    import pathlib

    import anyio

logger: logging.Logger = logging.getLogger(__name__)


class DescriptionParams(NamedTuple):
    integration: anyio.Path
    integration_name: str
    connector_name: str
    connector_file_name: str
    status: IntegrationStatus


class DescribeConnector(DescribeBase[ConnectorAiMetadata]):
    def __init__(
        self,
        integration: str,
        connectors: set[str],
        *,
        src: pathlib.Path | None = None,
        dst: pathlib.Path | None = None,
        override: bool = False,
    ) -> None:
        super().__init__(integration, connectors, src=src, dst=dst, override=override)
        self._connector_name_to_file_stem: dict[str, str] = {}

    @property
    def metadata_file_name(self) -> str:
        """Get the name of the metadata file."""
        return constants.CONNECTORS_AI_DESCRIPTION_FILE

    @property
    def resource_type_name(self) -> str:
        """Get the resource type name."""
        return "connector"

    @property
    def response_schema(self) -> type[ConnectorAiMetadata]:
        """Get the response schema."""
        return ConnectorAiMetadata

    async def _get_all_resources(self, status: IntegrationStatus) -> set[str]:
        connectors: set[str] = set()
        if status.is_built:
            await self._get_all_built_connectors(status.out_path, connectors)
        else:
            await self._get_all_non_built_connectors(connectors)
        return connectors

    async def _get_all_built_connectors(self, out_path: anyio.Path, connectors: set[str]) -> None:
        path: anyio.Path = out_path / constants.OUT_CONNECTORS_META_DIR
        if await path.exists():
            async for file in path.glob(f"*{constants.CONNECTORS_META_SUFFIX}"):
                content: str = await file.read_text(encoding="utf-8")
                try:
                    data: dict = json.loads(content)
                    name: str = data["Name"]
                    self._connector_name_to_file_stem[name] = file.stem
                    connectors.add(name)
                except (json.JSONDecodeError, KeyError):
                    logger.warning("Failed to parse built connector metadata %s", file.name)

    async def _get_all_non_built_connectors(self, connectors: set[str]) -> None:
        path: anyio.Path = self.integration / constants.CONNECTORS_DIR
        if await path.exists():
            async for file in path.glob(f"*{constants.YAML_SUFFIX}"):
                content: str = await file.read_text(encoding="utf-8")
                try:
                    data: dict = yaml.safe_load(content)
                    name: str = data["name"]
                    self._connector_name_to_file_stem[name] = file.stem
                    connectors.add(name)
                except (yaml.YAMLError, KeyError):
                    logger.warning("Failed to parse non-built connector metadata %s", file.name)

    async def _construct_prompts(
        self, resources: list[str], status: IntegrationStatus
    ) -> list[str]:
        prompts: list[str] = []
        for connector_name in resources:
            params = DescriptionParams(
                self.integration,
                self.integration_name,
                connector_name,
                self._connector_name_to_file_stem.get(connector_name, connector_name),
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
            params.connector_name,
            params.connector_file_name,
            params.status.out_path,
        )
    return SourcePromptConstructor(
        params.integration,
        params.integration_name,
        params.connector_name,
        params.connector_file_name,
        params.status.out_path,
    )
