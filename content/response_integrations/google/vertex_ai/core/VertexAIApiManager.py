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

import json
from urllib.parse import urljoin

import requests
from google.auth.transport.requests import AuthorizedSession
from TIPCommon.base.interfaces import Apiable
from TIPCommon.base.utils import NewLineLogger
from TIPCommon.types import SingleJson
from ..core.VertexAIConstants import (
    ANTHROPIC_VERSION,
    DEFAULT_MAX_OUTPUT_TOKENS,
    VERTEX_SDK_PUBLISHERS,
)
from ..core.VertexAIDatamodels import GenerationConfig, GenerationResult, Prompt
from ..core.VertexAIExceptions import VertexAIManagerException

ENDPOINTS = {
    "publishers.models.get": "v1/publishers/{publisher_name}/models/{model_id}",
    "projects.locations.endpoints.countTokens": (
        "v1/projects/{project_id}/locations/{location_id}/publishers/"
        "{publisher_name}/models/{model_id}:countTokens"
    ),
    "projects.locations.endpoints.generateContent": (
        "v1/projects/{project_id}/locations/{location_id}/publishers/"
        "{publisher_name}/models/{model_id}:generateContent"
    ),
    "projects.locations.endpoints.vertex_sdk_count_tokens": (
        "v1/projects/{project_id}/locations/{location_id}/publishers/"
        "{publisher_name}/models/count-tokens:rawPredict"
    ),
    "projects.locations.endpoints.rawPredict": (
        "v1/projects/{project_id}/locations/{location_id}/publishers/"
        "{publisher_name}/models/{model_id}:rawPredict"
    ),
}

API_REQUEST_TIMEOUT = 600


class ApiManager(Apiable):
    def __init__(
        self,
        api_root: str,
        session: AuthorizedSession,
        location_id: str,
        project_id: str,
        logger: NewLineLogger,
    ) -> None:
        """Manager for handling API interactions.

        Args:
            api_root: Api root for Vertex API
            session: Session object with corresponding headers
            location_id: ID of location to use in requests
            project_id: Project ID to be used for request
            logger: The logger object

        """
        self.api_root = api_root
        self.session = session
        self.location_id = location_id
        self.project_id = project_id
        self.logger = logger

    def _get_url(self, endpoint: str, **kwargs) -> str:
        url_path = ENDPOINTS[endpoint].format(
            location_id=self.location_id, project_id=self.project_id, **kwargs,
        )
        return urljoin(self.api_root, url_path)

    def test_connectivity(self, model_id: str, publisher_name: str) -> None:
        """Test connectivity."""
        self.get_publishers_model(model_id=model_id, publisher_name=publisher_name)

    @staticmethod
    def validate_response(
        response: requests.Response,
        error_msg: str = "An error occurred",
    ) -> None:
        """Validate response

        Args:
            response (requests.Response): Response to validate
            error_msg (str): Default message to display on error

        Raises:
            GoogleCloudApiHTTPException: If there is any error in the response

        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                error_details = response.json()["error"]["details"][0]["detail"]
                if error_details:
                    raise VertexAIManagerException(
                        f"{error_msg}: {error_details}",
                    ) from error
            except (KeyError, IndexError, json.decoder.JSONDecodeError):
                pass

            raise VertexAIManagerException(
                f"{error_msg}: {error} {error.response.content}",
            ) from error

    def get_publishers_model(
        self,
        model_id: str,
        publisher_name: str,
    ) -> SingleJson:
        """Get model by ID and publisher name"""
        endpoint = self._get_url(
            "publishers.models.get", model_id=model_id, publisher_name=publisher_name,
        )
        response = self.session.get(endpoint)
        self.validate_response(response)
        return response.json()

    def count_tokens(
        self,
        model_id: str,
        prompt: Prompt,
        publisher_name: str,
        generation_config: GenerationConfig,
    ) -> int:
        """Count tokens for a given model and prompt.

        Args:
            model_id: ID of the model to be used.
            prompt: Prompt contents.
            publisher_name: Model publisher name
            generation_config: Generation Config.

        Returns:
            int: The number of token used.

        """
        if publisher_name in VERTEX_SDK_PUBLISHERS:
            return self._count_tokens_vertex_api(
                model_id=model_id,
                prompt=prompt,
                publisher_name=publisher_name,
            )
        return self._count_tokens_standard(
            model_id=model_id,
            prompt=prompt,
            publisher_name=publisher_name,
            generation_config=generation_config,
        )

    def _count_tokens_standard(
        self,
        model_id: str,
        prompt: Prompt,
        publisher_name: str,
        generation_config: GenerationConfig,
    ):
        """Count tokens for standard Google API format.

        This method is used for publishers that do not use
        Vertex AI SDK and API but instead rely on the
        standard Google API.

        Args:
            model_id: ID of the model to be used.
            prompt: Prompt contents.
            publisher_name: Model publisher name
            generation_config: Generation Config.

        Returns:
            int: The number of input tokens used in the request.

        """
        endpoint = self._get_url(
            "projects.locations.endpoints.countTokens",
            model_id=model_id,
            publisher_name=publisher_name,
        )
        payload = {
            "contents": [prompt.build_prompt()],
            "generationConfig": generation_config.build_config(),
        }
        return self._post_and_extract(endpoint, payload, result_param="totalTokens")

    def _count_tokens_vertex_api(
        self,
        model_id: str,
        prompt: Prompt,
        publisher_name: str,
    ):
        """Count input tokens using Vertex AI API.
        This method is used for publishers that follow
        the Vertex SDK rawPredict API format.

        Args:
            model_id: ID of the model to be used.
            prompt: Prompt contents.
            publisher_name: Model publisher name
        Returns:
            int: The number of input tokens used in the request.

        """
        endpoint = self._get_url(
            "projects.locations.endpoints.vertex_sdk_count_tokens",
            model_id=model_id,
            publisher_name=publisher_name,
        )
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt.text}],
        }
        return self._post_and_extract(endpoint, payload, result_param="input_tokens")

    def _post_and_extract(
        self, endpoint: str, payload: SingleJson, result_param: str,
    ) -> int:
        response = self.session.post(
            endpoint,
            json=payload,
        )
        self.validate_response(response)
        return response.json()[result_param]

    def generate_content(
        self,
        model_id: str,
        prompt: Prompt,
        publisher_name: str,
        generation_config: GenerationConfig,
        content_data: str = "",
        max_output_tokens: int = None,
    ) -> GenerationResult:
        """Generate content for the given model and prompt.

        Args:
            model_id: ID of the model to be used.
            prompt: Prompt contents.
            publisher_name: Model publisher name
            generation_config: Generation Config.
            content_data: Additional base64 encoded text to append to prompt.
            max_output_tokens: Optional limit for the number of generated tokens.

        Returns:
            GenerationResult: Parsed model response.

        """
        if publisher_name in VERTEX_SDK_PUBLISHERS:
            return self._generate_vertex_publisher_response(
                model_id=model_id,
                prompt=prompt,
                publisher_name=publisher_name,
                content_data=content_data,
                max_output_tokens=max_output_tokens,
            )
        return self._generate_standard_response(
            model_id=model_id,
            prompt=prompt,
            publisher_name=publisher_name,
            generation_config=generation_config,
        )

    def _generate_standard_response(
        self,
        model_id: str,
        prompt: Prompt,
        publisher_name: str,
        generation_config: GenerationConfig,
    ) -> GenerationResult:
        """Generate a standard response for model using
        a Google API-like interface(non-Vertex AI API).

        Args:
            model_id: ID of the model.
            prompt: Input prompt to be sent to the model..
            publisher_name: Name of the model publisher.
            generation_config: Configuration settings for generation.

        """
        endpoint = self._build_url(
            path="projects.locations.endpoints.generateContent",
            model_id=model_id,
            publisher_name=publisher_name,
        )
        payload = {
            "contents": [prompt.build_prompt()],
            "generationConfig": generation_config.build_config(),
        }
        return self._post_and_parse(endpoint, payload)

    def _post_and_parse(self, endpoint: str, payload: SingleJson) -> GenerationResult:
        response = self.session.post(
            endpoint,
            json=payload,
            timeout=API_REQUEST_TIMEOUT
        )
        self.validate_response(response)
        return GenerationResult.from_json(response.json())

    def _generate_vertex_publisher_response(
        self,
        model_id: str,
        prompt: Prompt,
        publisher_name: str,
        content_data: str,
        max_output_tokens: int = None,
    ) -> GenerationResult:
        """Build and send a rawPredict payload for Vertex publishers

        Args:
            model_id: ID of the model.
            prompt: Prompt object.
            publisher_name: Name of the publisher
            content_data: Additional user content to append.
            max_output_tokens: Optional limit on nu,ber of tokens.

        Returns:
            GenerationResult:Parsed model response.

        """
        endpoint = self._get_url(
            "projects.locations.endpoints.rawPredict",
            model_id=model_id,
            publisher_name=publisher_name,
        )
        max_tokens = (
            max_output_tokens or DEFAULT_MAX_OUTPUT_TOKENS
        )
        payload = {
            "anthropic_version": ANTHROPIC_VERSION,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt.text + " " + content_data},
                    ],
                },
            ],
            "max_tokens": max_tokens,
            "stream": False,
        }
        return self._post_and_parse(endpoint, payload)

    def _build_url(self, path: str, model_id: str, publisher_name: str) -> str:
        """Construct the endpoint URL with model and publisher info.

        Args:
            path: Endpoint path pattern.
            model_id: Model ID name.
            publisher_name: Publisher name

        """
        return self._get_url(
            path,
            model_id=model_id,
            publisher_name=publisher_name,
        )
