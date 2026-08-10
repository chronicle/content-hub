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
from mp.describe.common.describe import DescribeBase, DescriptionResult, IntegrationStatus
from mp.describe.common.metadata import (
    PromptOverrideConfig,
    parse_prompt_overrides_content,
)
from mp.describe.common.utils import llm
from mp.describe.common.utils.overrides import create_dynamic_field_model, format_display_value

from .metadata import (
    FIELD_TO_OVERRIDE_MODEL,
)
from .prompt_constructors.integration import IntegrationPromptConstructor

if TYPE_CHECKING:
    import pathlib

    from pydantic import BaseModel

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
        """Name of the metadata file."""
        return constants.INTEGRATIONS_AI_DESCRIPTION_FILE

    @property
    def resource_type_name(self) -> str:
        """The resource type name."""
        return "integration"

    @property
    def response_schema(self) -> type[IntegrationAiMetadata]:
        """The response schema."""
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

    async def _construct_prompts(self, resources: list[str], status: IntegrationStatus) -> list[str]:
        # resources will be [self.integration_name]
        prompts: list[str] = []
        for integration_name in resources:
            constructor = IntegrationPromptConstructor(self.integration, integration_name, status.out_path)
            prompts.append(await constructor.construct())

        return prompts

    async def _load_metadata(self) -> dict[str, Any]:
        resource_ai_dir: anyio.Path = self.integration / constants.RESOURCES_DIR / constants.AI_DIR
        metadata_file: anyio.Path = resource_ai_dir / self.metadata_file_name

        metadata: dict[str, Any] = {}
        if await metadata_file.exists():
            content: str = await metadata_file.read_text(encoding="utf-8")
            with contextlib.suppress(yaml.YAMLError):
                # For integrations, the file is NOT keyed by integration name
                if raw_metadata := yaml.safe_load(content) or {}:
                    metadata: dict[str, Any] = {self.integration_name: raw_metadata}

        if self.dst:
            dst_file: anyio.Path = anyio.Path(self.dst) / self.metadata_file_name
            if await dst_file.exists():
                content: str = await dst_file.read_text(encoding="utf-8")
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
        await metadata_file.write_text(yaml.safe_dump(integration_metadata, allow_unicode=True), encoding="utf-8")


class MultiPromptDescribeIntegration(DescribeIntegration):
    def __init__(
        self,
        integration: str,
        *,
        src: pathlib.Path | None = None,
        dst: pathlib.Path | None = None,
        override: bool = False,
        prompt_overrides: pathlib.Path | None = None,
    ) -> None:
        super().__init__(integration, src=src, dst=dst, override=override)
        self.prompt_overrides_path: pathlib.Path | None = prompt_overrides

    async def describe_bulk(
        self,
        resources: list[str],
        status: IntegrationStatus,
    ) -> list[DescriptionResult]:
        """Describe multiple integration resources in bulk with optional prompt overrides.

        Args:
            resources: Integration resource names to describe.
            status: Status of the integration content build.

        Returns:
            list[DescriptionResult]: The list of integration description results.

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
        """Construct custom prompts for integrations using a prompt override configuration.

        Args:
            resources: Integration resource names to construct prompts for.
            status: Status of the integration content build.
            override: Prompt override configuration.

        Returns:
            list[str]: Formatted custom prompt strings for each integration.

        """
        prompts: list[str] = []
        for integration_name in resources:
            constructor = IntegrationPromptConstructor(self.integration, integration_name, status.out_path)
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
            resources: Integration resource names to describe.
            status: Status of the integration content build.
            baseline_results: Baseline integration description results.
            overrides: Parsed list of prompt override configurations.

        Returns:
            list[DescriptionResult]: Updated integration description results with field overrides applied.

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
                        "Failed custom describe for integration %s field %s: %s",
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
                    "Successfully overridden field '%s' for integration '%s' with LLM response:\n%s",
                    override.target_field,
                    resource_name,
                    format_display_value(override_val),
                )

                updated_meta = curr_meta.model_copy(update={override.target_field: override_val})
                results[idx] = DescriptionResult(resource_name, updated_meta)

        return results
