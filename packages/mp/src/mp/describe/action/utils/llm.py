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
from typing import TYPE_CHECKING, TypeVar

import anyio

from mp.core.gemini import Gemini, GeminiConfig
from mp.describe.action.data_models.action_ai_metadata import ActionAiMetadata

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from mp.core.llm_sdk import LlmSdk

GEMINI_MODEL_NAME: str = "gemini-3-flash-preview"
DESCRIBE_BULK_SIZE: int = 4

T_Schema = TypeVar("T_Schema")


@contextlib.asynccontextmanager
async def create_llm_session() -> AsyncIterator[LlmSdk]:
    """Create an LLM session with the system prompt configured.

    Yields:
        AsyncIterator[LlmSdk]: The LLM session.

    """
    llm_config = _create_gemini_config()
    async with Gemini(llm_config) as gemini:
        system_prompt = await _get_system_prompt()
        gemini.add_system_prompts_to_session(system_prompt)
        yield gemini


async def call_gemini_bulk(prompts: list[str]) -> list[ActionAiMetadata | str]:
    """Call Gemini to describe multiple prompts in bulk.

    Args:
        prompts: The prompts to send.

    Returns:
        list[ActionAiMetadata | str]: The responses from Gemini.

    """
    async with create_llm_session() as gemini:
        return await gemini.send_bulk_messages(
            prompts,
            response_json_schema=ActionAiMetadata,
        )


def _create_gemini_config() -> GeminiConfig:
    return GeminiConfig(model_name=GEMINI_MODEL_NAME)


async def _get_system_prompt() -> str:
    path = anyio.Path(__file__).parent.parent / "prompts" / "system.md"
    return await path.read_text(encoding="utf-8")
