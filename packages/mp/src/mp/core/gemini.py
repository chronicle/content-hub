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

import io
import logging
import os
from typing import TYPE_CHECKING, Self

from google import genai
from google.genai.errors import ClientError
from google.genai.types import (
    Content,
    GenerateContentConfig,
    GoogleSearch,
    HarmBlockThreshold,
    HarmCategory,
    Part,
    SafetySetting,
    ThinkingConfig,
    ThinkingLevel,
    Tool,
    ToolListUnion,
    UrlContext,
)
from rich.logging import RichHandler
from tenacity import (
    after_log,
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .llm_sdk import LlmConfig, LlmSdk, T_Schema

if TYPE_CHECKING:
    from types import TracebackType

    from google.genai.client import AsyncClient


logger: logging.Logger = logging.getLogger("mp.gemini")
logging.basicConfig(level="INFO", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])


class ApiKeyNotFoundError(Exception):
    """Exception raised when the API key is not found."""


class GeminiConfig(LlmConfig):
    model_name: str = "gemini-3-pro-preview"
    temperature: float = 1.0
    sexually_explicit: str = "OFF"
    dangerous_content: str = "OFF"
    hate_speech: str = "OFF"
    harassment: str = "OFF"
    google_search: bool = True
    url_context: bool = True
    use_thinking: bool = True

    @property
    def api_key(self) -> str:
        """Api Key.

        Raises:
            ApiKeyNotFoundError: If the API key is not found.

        """
        gemini_api_key: str | None = os.environ.get("GEMINI_API_KEY")
        if gemini_api_key:
            return gemini_api_key

        msg: str = (
            "Could not find a saved Gemini API key in the configuration. "
            "Please configure it using 'eve config -k'."
        )
        raise ApiKeyNotFoundError(msg) from None


class Gemini(LlmSdk[GeminiConfig, T_Schema]):
    def __init__(self, config: GeminiConfig) -> None:
        super().__init__(config)
        self.client: AsyncClient = genai.client.Client(api_key=self.config.api_key).aio
        self.content: Content = Content(role="user", parts=[])

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    @retry(
        retry=retry_if_not_exception_type(ClientError),
        stop=stop_after_attempt(4),
        wait=wait_exponential(),
        after=after_log(logger, logging.DEBUG),
    )
    async def send_message(
        self,
        prompt: str,
        /,
        *,
        raise_error_if_empty_response: bool = False,
        response_json_schema: type[T_Schema] | None = None,
    ) -> T_Schema | str:
        """Send a message to the LLM and get a response.

        Args:
            prompt: The prompt to send to the LLM.
            raise_error_if_empty_response:
                If True, raise an error if the LLM response is empty.
                If False, return an empty string if the LLM response is empty.
            response_json_schema: The JSON schema to use for validation.
                If None, no validation is performed.

        Returns:
            The LLM response as a string or a Pydantic model.

        Raises:
            ValueError: If the JSON schema is invalid.

        """
        schema: str | None = None
        if response_json_schema is not None:
            schema = response_json_schema.model_json_schema()

        config: GenerateContentConfig = self.create_generate_content_config(schema)
        logger.debug("Sending prompt: %s", prompt)
        if not self.content.parts:
            self.content.parts = []

        self.content.parts.append(Part.from_text(text=prompt))

        response: io.StringIO = io.StringIO()
        async for chunk in await self.client.models.generate_content_stream(
            model=self.config.model_name,
            contents=self.content,
            config=config,
        ):
            if chunk.text:
                response.write(chunk.text)

        text: str = response.getvalue()
        logger.debug("Response text: %s", text)
        if raise_error_if_empty_response and not text:
            msg: str = f"Received {text!r} from the LLM as generation results"
            raise ValueError(msg)

        if text:
            self.content.parts.append(Part.from_text(text=text))

        if response_json_schema is not None and text:
            return response_json_schema.model_validate_json(text, by_alias=True)

        return text

    async def close(self) -> None:
        """Close the client."""
        self.clean_session_history()
        await self.client.aclose()

    def clean_session_history(self) -> None:
        """Clean the session history."""
        self.content = Content(role="user", parts=[])

    def add_system_prompts_to_session(self, *prompts: str) -> None:
        """Add system prompts to the session.

        This can only be done if there are no other registered prompts yet
        """
        if self.content.parts:
            return

        self.content.parts = []
        for prompt in prompts:
            self.content.parts.append(Part.from_text(text=prompt))

    def create_generate_content_config(
        self,
        response_json_schema: str | None = None,
    ) -> GenerateContentConfig:
        """Create a GenerateContentConfig object for the Gemini API.

        Args:
            response_json_schema: The JSON schema to validate the response against.

        Returns:
            The GenerateContentConfig object.

        """
        response_mime_type: str = "plain/text"
        if response_json_schema is not None:
            response_mime_type = "application/json"

        tools: ToolListUnion = self._get_tools()
        safety_settings: list[SafetySetting] = self._get_safety_settings()
        thinking_config: ThinkingConfig | None = self._get_thinking_config()
        return GenerateContentConfig(
            temperature=self.config.temperature,
            response_mime_type=response_mime_type,
            thinking_config=thinking_config,
            response_json_schema=response_json_schema,
            tools=tools,
            safety_settings=safety_settings,
        )

    def _get_safety_settings(self) -> list[SafetySetting]:
        try:
            return [
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=HarmBlockThreshold(self.config.harassment),
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=HarmBlockThreshold(self.config.hate_speech),
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=HarmBlockThreshold(self.config.dangerous_content),
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=HarmBlockThreshold(self.config.sexually_explicit),
                ),
            ]
        except ValueError as e:
            msg: str = (
                "Invalid HarmBlockThreshold value."
                " Value must be one of the string representations of"
                " HarmBlockThreshold enum (e.g., 'OFF', 'BLOCK_LOW_AND_ABOVE')"
            )
            raise ValueError(msg) from e

    def _get_tools(self) -> ToolListUnion:
        results: ToolListUnion = []
        if self.config.google_search:
            results.append(Tool(google_search=GoogleSearch()))

        if self.config.url_context:
            results.append(Tool(url_context=UrlContext()))

        return results

    def _get_thinking_config(self) -> ThinkingConfig | None:
        return (
            ThinkingConfig(thinking_level=ThinkingLevel.HIGH) if self.config.use_thinking else None
        )
