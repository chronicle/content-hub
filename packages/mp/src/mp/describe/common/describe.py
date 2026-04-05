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

import abc
import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any, Generic, NamedTuple, TypeVar

import anyio
import yaml
from pydantic import BaseModel
from rich.progress import TaskID, track

from mp.core import constants
from mp.core.utils import folded_string_representer

from .utils import llm, paths

if TYPE_CHECKING:
    import pathlib
    from collections.abc import AsyncIterator, Callable

    from rich.progress import Progress

logger: logging.Logger = logging.getLogger(__name__)

T_Metadata = TypeVar("T_Metadata", bound=BaseModel)


class IntegrationStatus(NamedTuple):
    is_built: bool
    out_path: anyio.Path


class DescriptionResult(NamedTuple):
    name: str
    metadata: BaseModel | None


class RichParams(NamedTuple):
    on_done: Callable[[], None] | None = None
    progress: Progress | None = None
    task_id: TaskID | None = None


def _merge_results(metadata: dict[str, Any], results: list[DescriptionResult]) -> None:
    for result in results:
        if result.metadata is not None:
            metadata[result.name] = result.metadata.model_dump(mode="json")


def _create_notifier(rich_params: RichParams) -> Callable[[], None]:
    """Create a notifier function to handle progress and callbacks.

    Args:
        rich_params: Progress and callback parameters.

    Returns:
        Callable[[], None]: A function that advances progress and calls the callback.

    """

    def notify() -> None:
        if rich_params.on_done:
            rich_params.on_done()
        if rich_params.progress and rich_params.task_id:
            rich_params.progress.advance(rich_params.task_id)

    return notify


@contextlib.asynccontextmanager
async def _maybe_use_semaphore(sem: asyncio.Semaphore | None) -> AsyncIterator[None]:
    """Context manager to optionally use a semaphore.

    Args:
        sem: The semaphore to use, or None.

    Yields:
        None

    """
    if sem:
        async with sem:
            yield
    else:
        yield


class DescribeBase(abc.ABC, Generic[T_Metadata]):
    def __init__(
        self,
        integration_name: str,
        resource_names: set[str],
        *,
        src: pathlib.Path | None = None,
        dst: pathlib.Path | None = None,
        override: bool = False,
    ) -> None:
        self.integration_name: str = integration_name
        self.src: pathlib.Path | None = src
        self.integration: anyio.Path = paths.get_integration_path(integration_name, src=src)
        self.resource_names: set[str] = resource_names
        self.override: bool = override
        self.dst: pathlib.Path | None = dst

    @property
    @abc.abstractmethod
    def metadata_file_name(self) -> str:
        """The name of the metadata file."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def resource_type_name(self) -> str:
        """The name of the resource type (e.g., 'action', 'integration')."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def response_schema(self) -> type[T_Metadata]:
        """The schema for the LLM response."""
        raise NotImplementedError

    @abc.abstractmethod
    async def _get_all_resources(self, status: IntegrationStatus) -> set[str]:
        """Get all resources of the given type in the integration."""
        raise NotImplementedError

    @abc.abstractmethod
    async def _construct_prompts(
        self, resources: list[str], status: IntegrationStatus
    ) -> list[str]:
        """Construct prompts for the given resources."""
        raise NotImplementedError

    async def describe(
        self,
        sem: asyncio.Semaphore | None = None,
        on_done: Callable[[], None] | None = None,
        progress: Progress | None = None,
    ) -> None:
        """Describe resources in a given integration.

        Args:
            sem: Optional semaphore to limit concurrent Gemini requests.
            on_done: An optional callback is called when a resource is finished.
            progress: An optional Progress object to use for progress reporting.

        """
        metadata, status = await asyncio.gather(
            self._load_metadata(), self._get_integration_status()
        )

        resources_to_process: set[str] = await self._prepare_resources(status, metadata)
        if not resources_to_process:
            if not self.resource_names:
                await self._save_metadata(metadata)
            else:
                logger.info(
                    "All %ss in %s already have descriptions. Skipping.",
                    self.resource_type_name,
                    self.integration_name,
                )
            return

        if len(resources_to_process) == 1:
            logger.info(
                "Describing %s %s for %s",
                self.resource_type_name,
                next(iter(resources_to_process)),
                self.integration_name,
            )
        else:
            logger.info(
                "Describing %d %ss for %s",
                len(resources_to_process),
                self.resource_type_name,
                self.integration_name,
            )

        results: list[DescriptionResult] = await self._execute_descriptions(
            resources_to_process, status, sem, on_done, progress
        )

        _merge_results(metadata, results)
        await self._save_metadata(metadata)

    async def get_resources_count(self) -> int:
        """Get the number of resources in the integration.

        Returns:
            int: The number of resources.

        """
        status, metadata = await asyncio.gather(
            self._get_integration_status(), self._load_metadata()
        )
        resources: set[str] = await self._prepare_resources(status, metadata)
        return len(resources)

    async def _prepare_resources(
        self, status: IntegrationStatus, metadata: dict[str, Any]
    ) -> set[str]:
        if not self.resource_names:
            self.resource_names = await self._get_all_resources(status)

        # Prune metadata for resources that no longer exist
        # Only for non-integration types which use resource names as keys
        if self.resource_type_name != "integration":
            for key in list(metadata.keys()):
                if key not in self.resource_names:
                    del metadata[key]

        if not self.override:
            resources_to_process: set[str] = {
                res for res in self.resource_names if res not in metadata
            }
            skipped_count: int = len(self.resource_names) - len(resources_to_process)
            if skipped_count > 0:
                if skipped_count == 1:
                    logger.info(
                        "Skipping 1 %s that already has a description in %s",
                        self.resource_type_name,
                        self.integration_name,
                    )
                else:
                    logger.info(
                        "Skipping %d %ss that already have a description in %s",
                        skipped_count,
                        self.resource_type_name,
                        self.integration_name,
                    )
            return resources_to_process

        return self.resource_names

    async def _execute_descriptions(
        self,
        resources: set[str],
        status: IntegrationStatus,
        sem: asyncio.Semaphore | None = None,
        on_done: Callable[[], None] | None = None,
        progress: Progress | None = None,
    ) -> list[DescriptionResult]:
        resource_list = list(resources)
        bulks = [
            resource_list[i : i + llm.DESCRIBE_BULK_SIZE]
            for i in range(0, len(resource_list), llm.DESCRIBE_BULK_SIZE)
        ]

        if len(resources) == 1:
            description = (
                f"Describing {self.resource_type_name} {next(iter(resources))} for"
                f" {self.integration_name}..."
            )
        else:
            description = f"Describing {self.resource_type_name}s for {self.integration_name}..."

        results: list[DescriptionResult] = []

        if progress:
            task_id: TaskID = progress.add_task(description, total=len(resources))
            rich_params = RichParams(on_done, progress, task_id)
            tasks: list[asyncio.Task] = [
                asyncio.create_task(self._process_bulk_resources(bulk, status, sem, rich_params))
                for bulk in bulks
            ]
            for coro in asyncio.as_completed(tasks):
                results.extend(await coro)

            progress.remove_task(task_id)

        else:
            rich_params = RichParams(on_done)
            tasks: list[asyncio.Task] = [
                asyncio.create_task(self._process_bulk_resources(bulk, status, sem, rich_params))
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

    async def _process_bulk_resources(
        self,
        resources: list[str],
        status: IntegrationStatus,
        sem: asyncio.Semaphore | None = None,
        rich_params: RichParams | None = None,
    ) -> list[DescriptionResult]:
        if rich_params is None:
            rich_params = RichParams()

        notify_done: Callable[[], None] = _create_notifier(rich_params)
        try:
            async with _maybe_use_semaphore(sem):
                return await self._describe_resources_bulk_with_error_handling(
                    resources, status, notify_done
                )

        except Exception:
            logger.exception(
                "Failed to process bulk of %ss: %s", self.resource_type_name, resources
            )
            for _ in resources:
                notify_done()

            return [DescriptionResult(a, None) for a in resources]

    async def _describe_resources_bulk_with_error_handling(
        self,
        resources: list[str],
        status: IntegrationStatus,
        notify_done: Callable[[], None],
    ) -> list[DescriptionResult]:
        try:
            results: list[DescriptionResult] = await self.describe_bulk(resources, status)
        except Exception:
            logger.exception("Failed to describe %ss bulk %s", self.resource_type_name, resources)
            results: list[DescriptionResult] = [DescriptionResult(a, None) for a in resources]

        for _ in resources:
            notify_done()

        return results

    async def describe_bulk(
        self,
        resources: list[str],
        status: IntegrationStatus,
    ) -> list[DescriptionResult]:
        """Describe multiple resources of a given integration in bulk.

        Args:
            resources: The names of the resources to describe.
            status: The status of the integration.

        Returns:
            list[DescriptionResult]: The descriptions of the resources.

        """
        prompts: list[str] = await self._construct_prompts(resources, status)
        valid_indices: list[int] = [i for i, prompt in enumerate(prompts) if prompt]

        valid_prompts: list[str] = [prompts[i] for i in valid_indices]
        if not valid_prompts:
            return [DescriptionResult(a, None) for a in resources]

        llm_results: list[T_Metadata | str] = await llm.call_gemini_bulk(
            valid_prompts, self.response_schema
        )

        return self._map_bulk_results_to_resources(resources, valid_indices, llm_results)

    def _map_bulk_results_to_resources(
        self,
        resources: list[str],
        valid_indices: list[int],
        results: list[T_Metadata | str],
    ) -> list[DescriptionResult]:
        """Map Gemini results back to resource names.

        Args:
            resources: Original list of resource names.
            valid_indices: Indices of resources that had valid prompts.
            results: Results from Gemini for those valid prompts.

        Returns:
            list[DescriptionResult]: The mapped results.

        """
        final_results: list[DescriptionResult] = [DescriptionResult(a, None) for a in resources]

        for i, result in zip(valid_indices, results, strict=True):
            resource_name: str = resources[i]
            if isinstance(result, str):
                logger.error(
                    "Failed to describe %s %s: %s", self.resource_type_name, resource_name, result
                )
                continue

            # Special case for Ping action as in DescribeAction
            if (
                self.resource_type_name == "action"
                and resource_name.casefold() == "Ping".casefold()
                and hasattr(result, "categories")
            ):
                result.categories.enrichment = False

            final_results[i] = DescriptionResult(resource_name, result)

        return final_results

    async def _get_integration_status(self) -> IntegrationStatus:
        out_path: anyio.Path = paths.get_out_path(self.integration_name, src=self.src)
        is_built: bool = await out_path.exists()

        # If it's not built in the out directory, check if the integration itself is built
        if not is_built:
            # Look for any .def file in the integration directory
            async for _f in self.integration.glob("Integration-*.def"):
                is_built = True
                out_path = self.integration
                break

        return IntegrationStatus(is_built=is_built, out_path=out_path)

    async def _load_metadata(self) -> dict[str, Any]:
        resource_ai_dir: anyio.Path = self.integration / constants.RESOURCES_DIR / constants.AI_DIR
        metadata_file: anyio.Path = resource_ai_dir / self.metadata_file_name
        if not await metadata_file.exists():
            # Fallback to resources/
            metadata_file = self.integration / constants.RESOURCES_DIR / self.metadata_file_name

        metadata: dict[str, Any] = {}
        if await metadata_file.exists():
            content: str = await metadata_file.read_text()
            with contextlib.suppress(yaml.YAMLError):
                metadata = yaml.safe_load(content) or {}

        if self.dst:
            dst_file: anyio.Path = anyio.Path(self.dst) / self.metadata_file_name
            if await dst_file.exists():
                content: str = await dst_file.read_text()
                with contextlib.suppress(yaml.YAMLError):
                    dst_metadata = yaml.safe_load(content) or {}

                metadata.update(dst_metadata)

        return metadata

    async def _save_metadata(self, metadata: dict[str, Any]) -> None:
        if self.dst:
            save_dir: anyio.Path = anyio.Path(self.dst)
        else:
            save_dir: anyio.Path = self.integration / constants.RESOURCES_DIR / constants.AI_DIR

        metadata_file: anyio.Path = save_dir / self.metadata_file_name

        if not metadata:
            if await metadata_file.exists():
                await metadata_file.unlink()
            return

        await save_dir.mkdir(parents=True, exist_ok=True)
        yaml.add_representer(str, folded_string_representer, Dumper=yaml.SafeDumper)
        await metadata_file.write_text(yaml.safe_dump(metadata))
