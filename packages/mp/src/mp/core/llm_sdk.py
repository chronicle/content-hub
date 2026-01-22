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
from typing import TYPE_CHECKING, Generic, Literal, Self, TypeVar, overload

from pydantic import BaseModel

if TYPE_CHECKING:
    from types import TracebackType


class LlmConfig(BaseModel, abc.ABC):
    @property
    @abc.abstractmethod
    def api_key(self) -> str:
        """API key for the LLM provider.

        Raises:
            ApiKeyNotFoundError: If the API key is not found.

        """


T_LlmConfig = TypeVar("T_LlmConfig", bound=LlmConfig)
T_Schema = TypeVar("T_Schema", bound=BaseModel)


class LlmSdk(AbstractAsyncContextManager, abc.ABC):
    @abc.abstractmethod
    def __init__(self, llm_config: T_LlmConfig) -> None:
        self.llm_config: T_LlmConfig = llm_config

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
    ) -> T_Schema | str: ...

    @abc.abstractmethod
    def clean_session_history(self) -> None: ...

    @abc.abstractmethod
    def add_system_prompts_to_session(self, *prompts: str) -> None: ...

    @abc.abstractmethod
    async def __aenter__(self) -> Self: ...

    @abc.abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
