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
from contextlib import AbstractAsyncContextManager
from typing import Generic, Literal, TypeVar, overload

from pydantic import BaseModel


class LlmConfig(BaseModel, abc.ABC):
    @property
    @abc.abstractmethod
    def api_key(self) -> str:
        """API key for the LLM provider.

        Raises:
            ApiKeyNotFoundError: If the API key is not found.

        """


T_LlmConfig_co = TypeVar("T_LlmConfig_co", bound=LlmConfig, covariant=True)
T_Schema = TypeVar("T_Schema", bound=BaseModel)


DEFAULT_BULK_THRESHOLD: int = 4


class LlmSdk(AbstractAsyncContextManager, abc.ABC, Generic[T_LlmConfig_co]):
    def __init__(
        self,
        config: T_LlmConfig_co,
        *,
        bulk_threshold: int = DEFAULT_BULK_THRESHOLD,
    ) -> None:
        self.system_prompt: str = ""
        self.config: T_LlmConfig_co = config
        self.bulk_threshold: int = bulk_threshold

    @overload
    async def send_message(
        self,
        prompt: str,
        /,
        *,
        raise_error_if_empty_response: Literal[True],
        response_json_schema: type[T_Schema],
    ) -> T_Schema: ...

    @overload
    async def send_message(
        self,
        prompt: str,
        /,
        *,
        raise_error_if_empty_response: Literal[False],
        response_json_schema: type[T_Schema],
    ) -> T_Schema | Literal[""]: ...

    @overload
    async def send_message(
        self,
        prompt: str,
        /,
        *,
        raise_error_if_empty_response: bool,
        response_json_schema: None = None,
    ) -> str: ...

    @abc.abstractmethod
    async def send_message(
        self,
        prompt: str,
        /,
        *,
        raise_error_if_empty_response: bool,
        response_json_schema: type[T_Schema] | None = None,
    ) -> T_Schema | str:
        """Send a message to the LLM provider.

        Args:
            prompt: The prompt to send to the LLM provider.
            raise_error_if_empty_response: Whether to raise an error if the response is empty.
            response_json_schema: The JSON schema to validate the response against.

        Returns:
            The response from the LLM provider.

        """

    @abc.abstractmethod
    async def send_bulk_messages(
        self,
        prompts: list[str],
        /,
        *,
        response_json_schema: type[T_Schema] | None = None,
        use_batch: bool = False,
    ) -> list[T_Schema | str]:
        """Send multiple messages to the LLM provider in bulk.

        Args:
            prompts: The prompts to send to the LLM provider.
            response_json_schema: The JSON schema to validate the responses against.
            use_batch: Whether to use Google GenAI Batch API when count exceeds threshold.

        Returns:
            The responses from the LLM provider.

        """

    @abc.abstractmethod
    def clean_session_history(self) -> None:
        """Clean the session history."""

    def set_system_prompt_to_session(self, prompt: str) -> None:
        """Set the system prompt for the session."""
        self.system_prompt = prompt
