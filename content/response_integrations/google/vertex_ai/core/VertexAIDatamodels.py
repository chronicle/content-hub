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

import copy
import hashlib
import itertools
import json
from dataclasses import dataclass, field

from TIPCommon.base.action import Action
from TIPCommon.base.connector import BaseConnector
from TIPCommon.base.job import Job
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.context import Context, get_context_factory
from TIPCommon.smp_time import unix_now
from TIPCommon.types import SingleJson


@dataclass(frozen=True, slots=True)
class GenerationCacheEntry:
    summary_creation_time: int
    summary: str | list[str]
    seed: int

    def is_expired(self, refresh_after: int) -> bool:
        return (
            self.summary_creation_time
            + refresh_after * 24 * 60 * 60 * NUM_OF_MILLI_IN_SEC
            <= unix_now()
        )

    def as_json(self) -> SingleJson:
        return {
            "summary_creation_time": self.summary_creation_time,
            "summary": self.summary,
            "seed": self.seed,
        }


class GenerationCache:
    def __init__(
        self,
        chronicle_soar: Action | Job | BaseConnector,
        environment: str,
        model_id: str,
        generation_config: GenerationConfig,
    ) -> None:
        self.environment = environment
        self.model_id = model_id
        self.generation_config = generation_config
        self.logger = chronicle_soar.logger
        self._context: Context = get_context_factory(chronicle_soar)

    def _generate_entity_seed(self, prompt: Prompt) -> int:
        return int(
            hashlib.sha256(
                json.dumps(
                    {
                        "model_id": self.model_id,
                        "contents": [prompt.build_prompt()],
                        "generationConfig": self.generation_config.build_config(),
                    },
                    sort_keys=True,
                ).encode("utf-8"),
            ).hexdigest(),
            16,
        )

    def _get_db_key(self, original_identifier: str) -> str:
        return f"cache_{original_identifier}_{self.environment}"

    def _get_entity_generation_cache(
        self, original_identifier: str,
    ) -> GenerationCacheEntry | None:
        """Fetch entity generation cache from DB / FS."""
        cache_entry = self._context.get_context(self._get_db_key(original_identifier))
        if cache_entry is None:
            return None

        return GenerationCacheEntry(**json.loads(cache_entry))

    def get_cached_summary(
        self,
        original_identifier: str,
        prompt: Prompt,
        refresh_after: int,
    ) -> str | None:
        """Returns existing cache entry if exists, otherwise returns None."""
        cache_entry = self._get_entity_generation_cache(original_identifier)
        if cache_entry is None or cache_entry.is_expired(refresh_after):
            self.logger.info("Cache is empty or expired, refreshing.")
            return None

        seed = self._generate_entity_seed(prompt)
        if cache_entry.seed != seed:
            self.logger.info("Seed has changed, refreshing cache.")
            return None

        return cache_entry.summary

    def save_summary(
        self, original_identifier: str, prompt: Prompt, summary: str,
    ) -> None:
        """Save entity summary into DB / FS context key."""
        self._context.set_context(
            self._get_db_key(original_identifier),
            json.dumps(
                GenerationCacheEntry(
                    summary_creation_time=unix_now(),
                    summary=summary,
                    seed=self._generate_entity_seed(prompt),
                ).as_json(),
            ),
        )


@dataclass
class Prompt:
    text: str
    file_data: list[SingleJson] = field(default_factory=list)
    inline_data: list[SingleJson] = field(default_factory=list)

    def build_prompt(self) -> SingleJson:
        """Build prompt contents object."""
        contents = {"role": "user", "parts": [{"text": self.text}]}
        for file_data in self.file_data:
            contents["parts"].append({"fileData": file_data})

        for inline_data in self.inline_data:
            contents["parts"].append({"inlineData": inline_data})

        return contents


@dataclass
class GenerationConfig:
    temperature: float | None = None
    candidate_count: int | None = None
    max_output_tokens: int | None = None
    response_mime_type: str | None = None
    response_schema: SingleJson | None = None

    def build_config(self) -> SingleJson:
        return {
            "temperature": self.temperature,
            "candidateCount": self.candidate_count,
            "maxOutputTokens": self.max_output_tokens,
            "responseMimeType": self.response_mime_type,
            "responseSchema": self.response_schema,
        }


@dataclass
class GenerationResult:
    raw_data: SingleJson
    candidates: list[SingleJson]
    finish_reason: str
    usage_metadata: SingleJson
    content: list[SingleJson]
    usage: SingleJson

    @classmethod
    def from_json(cls, json_data: SingleJson) -> GenerationResult:
        return cls(
            raw_data=json_data,
            candidates=json_data.get("candidates", []),
            finish_reason=json_data.get("finishReason"),
            usage_metadata=json_data.get("usageMetadata"),
            content=json_data.get("content", []),
            usage=json_data.get("usage", {}),
        )

    def to_json(self) -> SingleJson:
        json_ = copy.deepcopy(self.raw_data)
        json_["text_content"] = self.text_content
        json_["extracted_info"] = self.json_content
        return json_

    @property
    def text_content(self) -> str | list[str]:
        """Extract text content from generation candidates."""
        if self.candidates:
            text_parts = [
                part["text"]
                for part in itertools.chain(
                    *(
                        candidate.get("content", {}).get("parts", [])
                        for candidate in self.candidates
                    ),
                )
                if "text" in part
            ]
            return text_parts[0] if len(text_parts) == 1 else text_parts

        self.usage_metadata = self.usage
        return (
            [part.get("text", "") for part in self.content][0] if self.content else ""
        )

    @property
    def json_content(self) -> SingleJson | None:
        """Extract JSON content from generation candidates."""
        try:
            text_ = (
                self.text_content
                if isinstance(self.text_content, str)
                else "".join(self.text_content)
            )
            return json.loads(text_)

        except json.JSONDecodeError:
            return None
