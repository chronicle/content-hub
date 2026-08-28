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
import pathlib

from ..core.VertexAIApiManager import ApiManager
from ..core.VertexAIDatamodels import Prompt, GenerationConfig

from ..tests.core.session import ApiSession
from integration_testing.request import HttpMethod


class TestApiManager:
    """Unit tests for Vertex AI ApiManager."""
    def test_count_tokens(
            self,
            vertexai_script_session: ApiSession,
            vertexai_manager: ApiManager
    ):
        prompt = Prompt(text="Sample text.")
        generation_config = GenerationConfig()
        vertexai_manager.count_tokens(
            "gemini-1.5-flash-002",
            prompt=prompt,
            generation_config=generation_config,
            publisher_name="google"
        )

        assert len(vertexai_script_session.request_history) >= 2
        assert (
            vertexai_script_session.request_history[-1].request.method
            == HttpMethod.POST
        )
        assert (
            vertexai_script_session.request_history[-1].request.url.path
            .endswith("countTokens")
        )

    def test_generate_content(
            self,
            vertexai_script_session: ApiSession,
            vertexai_manager: ApiManager
    ):
        prompt = Prompt(text="Sample text.")
        generation_config = GenerationConfig()
        vertexai_manager.generate_content(
            "gemini-1.5-flash-002",
            prompt=prompt,
            generation_config=generation_config,
            publisher_name="google"
        )

        assert len(vertexai_script_session.request_history) >= 2
        assert (
            vertexai_script_session.request_history[-1].request.method
            == HttpMethod.POST
        )
        assert (
            vertexai_script_session.request_history[-1].request.url.path
            .endswith("generateContent")
        )
