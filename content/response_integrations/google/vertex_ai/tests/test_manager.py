from __future__ import annotations

import pytest
import requests

from vertex_ai.core.VertexAIApiManager import ApiManager
from vertex_ai.core.VertexAIDatamodels import (
    GenerationConfig,
    Prompt,
)
from vertex_ai.tests.core.session import ApiSession
from integration_testing.request import HttpMethod
from vertex_ai.core.VertexAIExceptions import (  # pylint: disable=wrong-import-order
    VertexAIManagerException,
)


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

        assert len(vertexai_script_session.request_history) >= 3
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

        assert len(vertexai_script_session.request_history) >= 3
        assert (
            vertexai_script_session.request_history[-1].request.method
            == HttpMethod.POST
        )
        assert (
            vertexai_script_session.request_history[-1].request.url.path
            .endswith("generateContent")
        )

    def test_extract_error_message(self, mocker):
        """Validate _extract_error_message extracts error payload from response."""
        response = mocker.MagicMock(spec=requests.Response)
        error = requests.HTTPError("400 Client Error")
        response.json.return_value = {
            "error": {"message": "Invalid model specified."}
        }
        # pylint: disable=protected-access
        extracted = ApiManager._extract_error_message(response, error)
        assert extracted == "Invalid model specified."

    def test_validate_response_success(self, mocker):
        """Validate response succeeds without raising for successful HTTP response."""
        response = mocker.MagicMock(spec=requests.Response)
        response.raise_for_status.return_value = None
        # Should not raise
        ApiManager.validate_response(response)

    def test_validate_response_google_error_message(self, mocker):
        """Validate response parses error.message from Google API error response."""
        response = mocker.MagicMock(spec=requests.Response)
        response.raise_for_status.side_effect = requests.HTTPError("400 Client Error")
        response.json.return_value = {
            "error": {
                "code": 400,
                "message": (
                    "The input token count (7201036) exceeds the "
                    "maximum number of tokens allowed (1048576)."
                ),
                "status": "INVALID_ARGUMENT",
            }
        }
        with pytest.raises(VertexAIManagerException) as exc_info:
            ApiManager.validate_response(response)
        assert (
            "An error occurred: The input token count (7201036) exceeds the "
            "maximum number of tokens allowed (1048576)."
            == str(exc_info.value)
        )

    def test_validate_response_legacy_details(self, mocker):
        """Validate response extracts legacy detail message from error details list."""
        response = mocker.MagicMock(spec=requests.Response)
        response.raise_for_status.side_effect = requests.HTTPError("400 Client Error")
        response.json.return_value = {
            "error": {
                "details": [{"detail": "Custom legacy detail message"}],
            }
        }
        with pytest.raises(VertexAIManagerException) as exc_info:
            ApiManager.validate_response(response)
        assert "An error occurred: Custom legacy detail message" == str(exc_info.value)

    def test_validate_response_string_error(self, mocker):
        """Validate response handles string error payload."""
        response = mocker.MagicMock(spec=requests.Response)
        response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        response.json.return_value = {"error": "Internal backend failure"}
        with pytest.raises(VertexAIManagerException) as exc_info:
            ApiManager.validate_response(response)
        assert "An error occurred: Internal backend failure" == str(exc_info.value)

    def test_validate_response_top_level_message(self, mocker):
        """Validate response extracts top-level message from error payload."""
        response = mocker.MagicMock(spec=requests.Response)
        response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        response.json.return_value = {"message": "Permission denied"}
        with pytest.raises(VertexAIManagerException) as exc_info:
            ApiManager.validate_response(response)
        assert "An error occurred: Permission denied" == str(exc_info.value)

    def test_validate_response_non_json_fallback(self, mocker):
        """Validate response falls back to raw text for non-JSON error response."""
        response = mocker.MagicMock(spec=requests.Response)
        response.raise_for_status.side_effect = requests.HTTPError("502 Bad Gateway")
        response.json.side_effect = ValueError("No JSON")
        response.text = "Bad Gateway"
        with pytest.raises(VertexAIManagerException) as exc_info:
            ApiManager.validate_response(response)
        assert "An error occurred: Bad Gateway" == str(exc_info.value)

    def test_validate_response_html_fallback(self, mocker):
        """Validate response strips HTML tags when falling back to HTML error page."""
        response = mocker.MagicMock(spec=requests.Response)
        response.raise_for_status.side_effect = requests.HTTPError("502 Bad Gateway")
        response.json.side_effect = ValueError("No JSON")
        response.text = (
            "<html><body><h1>502 Bad Gateway</h1>"
            "<p>The proxy server failed.</p></body></html>"
        )
        with pytest.raises(VertexAIManagerException) as exc_info:
            ApiManager.validate_response(response)
        assert (
            "An error occurred: 502 Bad Gateway The proxy server failed."
            == str(exc_info.value)
        )
