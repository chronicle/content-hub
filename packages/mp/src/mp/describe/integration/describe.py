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
import logging
from typing import TYPE_CHECKING, Any

import anyio
import yaml

from mp.core import constants
from mp.core.data_models.integrations.integration_meta.ai.metadata import IntegrationAiMetadata
from mp.core.utils import folded_string_representer
from mp.describe.common.describe import DescribeBase, IntegrationStatus

from .prompt_constructors.integration import IntegrationPromptConstructor

if TYPE_CHECKING:
    import pathlib


logger: logging.Logger = logging.getLogger(__name__)


class DescribeIntegration(DescribeBase[IntegrationAiMetadata]):
    def __init__(
        self,
        integration: str,
        *,
        src: pathlib.Path | None = None,
        dst: pathlib.Path | None = None,
        override: bool = False,
    ) -> None:
        super().__init__(integration, {integration}, src=src, dst=dst, override=override)

    @property
    def metadata_file_name(self) -> str:
        """Get the name of the metadata file."""
        return constants.INTEGRATIONS_AI_DESCRIPTION_FILE

    @property
    def resource_type_name(self) -> str:
        """Get the resource type name."""
        return "integration"

    @property
    def response_schema(self) -> type[IntegrationAiMetadata]:
        """Get the response schema."""
        return IntegrationAiMetadata

    async def _get_all_resources(self, status: IntegrationStatus) -> set[str]:
        """Get all resources (only the integration itself).

        Args:
            status: The status of the integration.

        Returns:
            set[str]: The set of resource names.

        """
        del status  # Unused
        # There's only one integration to describe per integration folder.
        return {self.integration_name}

    async def _construct_prompts(
        self, resources: list[str], status: IntegrationStatus
    ) -> list[str]:
        # resources will be [self.integration_name]
        prompts: list[str] = []
        for integration_name in resources:
            constructor = IntegrationPromptConstructor(
                self.integration, integration_name, status.out_path
            )
            prompts.append(await constructor.construct())

        return prompts

    async def _load_metadata(self) -> dict[str, Any]:
        resource_ai_dir: anyio.Path = self.integration / constants.RESOURCES_DIR / constants.AI_DIR
        metadata_file: anyio.Path = resource_ai_dir / self.metadata_file_name

        metadata: dict[str, Any] = {}
        if await metadata_file.exists():
            content: str = await metadata_file.read_text()
            with contextlib.suppress(yaml.YAMLError):
                # For integrations, the file is NOT keyed by integration name
                if raw_metadata := yaml.safe_load(content) or {}:
                    metadata: dict[str, Any] = {self.integration_name: raw_metadata}

        if self.dst:
            dst_file: anyio.Path = anyio.Path(self.dst) / self.metadata_file_name
            if await dst_file.exists():
                content: str = await dst_file.read_text()
                with contextlib.suppress(yaml.YAMLError):
                    if dst_raw_metadata := yaml.safe_load(content) or {}:
                        metadata.update({self.integration_name: dst_raw_metadata})

        return metadata

    async def _save_metadata(self, metadata: dict[str, Any]) -> None:
        if self.dst:
            save_dir: anyio.Path = anyio.Path(self.dst)
        else:
            save_dir: anyio.Path = self.integration / constants.RESOURCES_DIR / constants.AI_DIR

        metadata_file: anyio.Path = save_dir / self.metadata_file_name

        # For integrations, we don't want to key it by integration name in the file
        if not (integration_metadata := metadata.get(self.integration_name)):
            if await metadata_file.exists():
                await metadata_file.unlink()

            return

        await save_dir.mkdir(parents=True, exist_ok=True)
        yaml.add_representer(str, folded_string_representer, Dumper=yaml.SafeDumper)
        await metadata_file.write_text(yaml.safe_dump(integration_metadata))
