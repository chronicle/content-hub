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
import asyncio
import contextlib
import itertools
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import anyio
import typer
from click import prompt
from rich.logging import RichHandler

from mp.core import constants
from mp.core.custom_types import RepositoryType
from mp.core.file_utils import get_integrations_repo_base_path
from mp.core.gemini import Gemini, GeminiConfig
from mp.core.llm_sdk import LlmSdk

from .data_models.action_ai_metadata import ActionAiMetadata

if TYPE_CHECKING:
    import pathlib

logger: logging.Logger = logging.getLogger("mp.describe_action")
logging.basicConfig(level="NOTSET", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])


class DescribeAction:
    def __init__(self, integration: str, actions: set[str]) -> None:
        self.integration: anyio.Path = _get_integration_path(integration)
        self.actions: set[str] = actions

    async def describe_actions(self) -> None:
        descriptions = await asyncio.gather(*[
            self.describe_action(a)
            async for a in (self.integration / constants.ACTIONS_DIR).iterdir()
            if a in self.actions
        ])

    async def describe_action(self, action: anyio.Path) -> ActionAiMetadata:
        prompt: str = f"{action.name}"
        async with self._create_llm_session() as gemini:
            return await gemini.send_message(
                prompt,
                response_json_schema=ActionAiMetadata,
                raise_error_if_empty_response=True,
            )

    @contextlib.asynccontextmanager
    async def _create_llm_session(self) -> AsyncIterator[LlmSdk]:
        llm_config: GeminiConfig = _create_gemini_config()
        async with Gemini(llm_config) as gemini:
            system_prompt: str = self._get_system_prompt()
            gemini.add_system_prompts_to_session(system_prompt)
            yield gemini

    def _get_system_prompt(self) -> str:
        return f"{self.integration}"


def _get_integration_path(name: str) -> anyio.Path:
    mp_paths: itertools.chain[pathlib.Path] = itertools.chain(
        get_integrations_repo_base_path(RepositoryType.COMMERCIAL).iterdir(),
        get_integrations_repo_base_path(RepositoryType.THIRD_PARTY).iterdir(),
    )
    for path in mp_paths:
        if (i := path / name).exists():
            return anyio.Path(i)

    logger.error("Integration '%s' not found in marketplace", name)
    raise typer.Exit(1)


def _create_gemini_config() -> GeminiConfig:
    return GeminiConfig()
