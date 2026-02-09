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

import asyncio
import io
import json
import logging
import os
from typing import TYPE_CHECKING, Annotated, Any, Literal, Self, overload

from google import genai
from google.genai.errors import ClientError
from google.genai.types import (
    BatchJob,
    Content,
    GenerateContentConfig,
    GoogleSearch,
    HarmBlockThreshold,
    HarmCategory,
    InlinedRequest,
    InlinedResponse,
    Part,
    SafetySetting,
    ThinkingConfig,
    ThinkingLevel,
    Tool,
    ToolListUnion,
    UrlContext,
)
from pydantic import Field
from tenacity import (
    after_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

import mp.core.config

from .sdk import LlmConfig, LlmSdk, T_Schema

if TYPE_CHECKING:
    from types import TracebackType

    from google.genai.client import AsyncClient


logger: logging.Logger = logging.getLogger("mp.gemini")


class ApiKeyNotFoundError(Exception):
    """Exception raised when the API key is not found."""


class GeminiConfig(LlmConfig):
    model_name: str = "gemini-3-pro-preview"
    temperature: float = 1.0
    sexually_explicit: str = "OFF"
    dangerous_content: str = "OFF"
    hate_speech: str = "OFF"
    harassment: str = "OFF"
    google_search: Annotated[bool, Field(description="Whether to use Google Search")] = True
    url_context: Annotated[bool, Field(description="Whether to use URL Context")] = True
    use_thinking: Annotated[bool, Field(description="Whether to use thinking mode")] = True
    request_response_validation: Annotated[
        bool,
        Field(description="Whether to add a response validate instruction in the system prompt"),
    ] = True

    @property
    def api_key(self) -> str:
        """Api Key.

        Raises:
            ApiKeyNotFoundError: If the API key is not found.

        """
        gemini_api_key: str | None = os.environ.get("GEMINI_API_KEY")
        if gemini_api_key:
            return gemini_api_key

        if mp_api_key := mp.core.config.get_gemini_api_key():
            return mp_api_key

        msg: str = (
            "Could not find a saved Gemini API key in the configuration. "
            "Please configure it using 'mp config --gemini-api-key <KEY>' or"
            " set the GEMINI_API_KEY environment variable."
        )
        raise ApiKeyNotFoundError(msg) from None


class Gemini(LlmSdk[GeminiConfig]):
    def __init__(self, config: GeminiConfig) -> None:
        super().__init__(config)
        self.client: AsyncClient = genai.client.Client(api_key=self.config.api_key).aio
        self.content: Content = Content(role="user", parts=[])
        self.bulk_threshold: int = 4

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

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

    @retry(
        retry=retry_if_exception_type(ClientError),
        stop=stop_after_attempt(10),
        wait=wait_exponential(),
        after=after_log(logger, logging.WARNING),  # ty:ignore[invalid-argument-type]
    )
    async def send_message(
        self,
        prompt: str,
        /,
        *,
        raise_error_if_empty_response: bool,
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

    async def send_bulk_messages(
        self,
        prompts: list[str],
        /,
        *,
        response_json_schema: type[T_Schema] | None = None,
    ) -> list[T_Schema | str]:
        """Send multiple messages to the LLM and get responses.

        Args:
            prompts: The prompts to send to the LLM.
            response_json_schema: The JSON schema to use for validation.

        Returns:
            The LLM responses as a list of strings or Pydantic models.

        """
        if not prompts:
            return []

        if len(prompts) <= self.bulk_threshold:
            return await asyncio.gather(*[
                self._send_single_message_independent(prompt, response_json_schema)
                for prompt in prompts
            ])

        requests: list[InlinedRequest] = self._prepare_batch_requests(prompts, response_json_schema)
        batch_job: BatchJob = await self._create_batch_job(requests)
        await self._poll_batch_job(batch_job)
        return await self._get_batch_results(batch_job, response_json_schema)

    @retry(
        retry=retry_if_exception_type(ClientError),
        stop=stop_after_attempt(10),
        wait=wait_exponential(),
        after=after_log(logger, logging.WARNING),  # ty:ignore[invalid-argument-type]
    )
    async def _send_single_message_independent(
        self,
        prompt: str,
        response_json_schema: type[T_Schema] | None = None,
    ) -> T_Schema | str:
        """Send a single message independently of the session history.

        Args:
            prompt: The prompt to send.
            response_json_schema: Optional schema for JSON response.

        Returns:
            The LLM response.

        """
        schema: dict[str, Any] | None = None
        if response_json_schema is not None:
            schema = response_json_schema.model_json_schema()

        config: GenerateContentConfig = self.create_generate_content_config(schema)

        parts: list[Part] = []
        if self.content.parts:
            parts.extend(self.content.parts)
        parts.append(Part.from_text(text=prompt))

        response = await self.client.models.generate_content(
            model=self.config.model_name,
            contents=[Content(role="user", parts=parts)],
            config=config,
        )

        text: str = response.text or ""
        if response_json_schema is not None and text:
            return response_json_schema.model_validate_json(text, by_alias=True)

        return text

    def _prepare_batch_requests(
        self,
        prompts: list[str],
        response_json_schema: type[T_Schema] | None,
    ) -> list[InlinedRequest]:
        """Prepare inlined requests for a batch job.

        Args:
            prompts: The prompts to send.
            response_json_schema: Optional schema for JSON responses.

        Returns:
            list[types.InlinedRequest]: The prepared requests.

        """
        schema: dict[str, Any] | None = None
        if response_json_schema is not None:
            schema = response_json_schema.model_json_schema()

        config: GenerateContentConfig = self.create_generate_content_config(schema)

        inlined_requests: list[InlinedRequest] = []
        for prompt in prompts:
            parts: list[Part] = []
            if self.content.parts:
                parts.extend(self.content.parts)
            parts.append(Part.from_text(text=prompt))

            inlined_requests.append(
                InlinedRequest(
                    model=self.config.model_name,
                    contents=[Content(role="user", parts=parts)],
                    config=config,
                )
            )

        return inlined_requests

    async def _create_batch_job(self, requests: list[InlinedRequest]) -> BatchJob:
        """Create a batch job on the Gemini API.

        Args:
            requests: The requests to include in the batch.

        Returns:
            types.BatchJob: The created batch job.

        Raises:
            RuntimeError: If job creation fails.

        """
        batch_job: BatchJob = await self.client.batches.create(
            model=self.config.model_name,
            src=requests,
        )

        if not batch_job.name:
            msg: str = "Batch job creation failed: no name returned"
            raise RuntimeError(msg)

        logger.info("Created batch job: %s", batch_job.name)
        return batch_job

    async def _poll_batch_job(self, batch_job: BatchJob) -> None:
        """Poll the batch job until it completes or fails.

        Args:
            batch_job: The job to poll.

        Raises:
            RuntimeError: If the job fails or loses its name.

        """
        while batch_job.state in {
            "JOB_STATE_PENDING",
            "JOB_STATE_RUNNING",
            "JOB_STATE_QUEUED",
            "JOB_STATE_UNSPECIFIED",
        }:
            logger.info("Batch job %s is in state %s, waiting...", batch_job.name, batch_job.state)
            await asyncio.sleep(10)
            if not batch_job.name:
                msg: str = "Batch job lost name during polling"
                raise RuntimeError(msg)

            batch_job = await self.client.batches.get(name=batch_job.name)
            logger.debug("Batch job %s state: %s", batch_job.name, batch_job.state)

        if batch_job.state != "JOB_STATE_SUCCEEDED":
            msg: str = f"Batch job {batch_job.name} failed with state {batch_job.state}"
            if batch_job.error:
                msg += f": {batch_job.error}"

            raise RuntimeError(msg)

    async def _get_batch_results(
        self,
        batch_job: BatchJob,
        response_json_schema: type[T_Schema] | None,
    ) -> list[T_Schema | str]:
        """Extract results from a completed batch job.

        Args:
            batch_job: The completed job.
            response_json_schema: Optional schema for result validation.

        Returns:
            list[T_Schema | str]: The parsed results.

        Raises:
            RuntimeError: If no results are found.

        """
        if not batch_job.dest:
            msg: str = f"Batch job {batch_job.name} succeeded but no results destination found"
            raise RuntimeError(msg)

        if batch_job.dest.inlined_responses:
            return _parse_inlined_responses(batch_job.dest.inlined_responses, response_json_schema)

        if batch_job.dest.file_name:
            return await self._parse_file_responses(batch_job.dest.file_name, response_json_schema)

        msg: str = f"Batch job {batch_job.name} succeeded but no results found in dest"
        raise RuntimeError(msg)

    async def _parse_file_responses(
        self,
        file_name: str,
        response_json_schema: type[T_Schema] | None,
    ) -> list[T_Schema | str]:
        """Parse file-based responses from a batch job.

        Returns:
            list[T_Schema | str]: The parsed results.

        """
        results: list[T_Schema | str] = []
        output_bytes: bytes = await self.client.files.download(file=file_name)
        for line in output_bytes.decode().splitlines():
            if not line.strip():
                continue

            text: str = _parse_response_line_to_text(line)
            if response_json_schema is not None and text:
                results.append(response_json_schema.model_validate_json(text, by_alias=True))
            else:
                results.append(text)

        return results

    def create_generate_content_config(
        self, response_json_schema: str | None = None
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
        system_prompt: str = self.system_prompt
        if self.config.request_response_validation:
            system_prompt = (
                f"{system_prompt}"
                " Before providing the final results, perform a mental validation pass."
                " Check for schema inconsistencies and factual inaccuracies."
                " If you find an error, correct it in the final output."
            )

        return GenerateContentConfig(
            temperature=self.config.temperature,
            response_mime_type=response_mime_type,
            thinking_config=thinking_config,
            response_json_schema=response_json_schema,
            tools=tools,
            safety_settings=safety_settings,
            system_instruction=system_prompt,
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


def _parse_response_line_to_text(line: str) -> str:
    data: dict[str, Any] = json.loads(line)
    response_data: dict[str, Any] = data.get("response")
    text: str = ""
    if response_data and response_data.get("candidates"):
        resp_content: dict[str, Any] = response_data["candidates"][0].get("content", {})
        parts: list[dict[str, Any]] = resp_content.get("parts", [])
        if parts:
            text: str = parts[0].get("text", "")

    return text


def _parse_inlined_responses(
    inline_responses: list[InlinedResponse],
    response_json_schema: type[T_Schema] | None,
) -> list[T_Schema | str]:
    """Parse inlined responses from a batch job.

    Returns:
        list[T_Schema | str]: The parsed results.

    """
    results: list[T_Schema | str] = []
    for inline_response in inline_responses:
        if not inline_response.response:
            continue

        text: str = inline_response.response.text or ""
        if response_json_schema is not None and text:
            results.append(response_json_schema.model_validate_json(text, by_alias=True))
        else:
            results.append(text)

    return results
