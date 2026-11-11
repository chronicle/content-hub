from __future__ import annotations

import pytest
from vertex_ai.core.VertexAIExceptions import VertexAIValidationException
from vertex_ai.core.VertexAIBaseAction import BaseAction


class DummyAction(BaseAction):
    def _perform_action(self):
        pass

    def _extract_parameters(self) -> None:
        pass


class TestApiRootValidation:
    """Unit tests for API Root Regex and location fallback extraction."""

    @pytest.mark.parametrize(
        "api_root, expected_location",
        [
            # Category 1: Hyphenated Regional Subdomains
            ("https://us-central1-aiplatform.googleapis.com", "us-central1"),
            ("https://europe-west1-aiplatform.googleapis.com", "europe-west1"),
            ("https://asia-northeast1-aiplatform.googleapis.com", "asia-northeast1"),
            ("https://australia-southeast1-aiplatform.googleapis.com", "australia-southeast1"),
            ("https://me-central1-aiplatform.googleapis.com", "me-central1"),
            ("https://southamerica-east1-aiplatform.googleapis.com", "southamerica-east1"),
            # Category 2: Dot-Separated Multi-Region Residency Subdomains
            ("https://aiplatform.us.rep.googleapis.com", "us"),
            ("https://aiplatform.eu.rep.googleapis.com", "eu"),
            ("https://aiplatform.asia.rep.googleapis.com", "asia"),
            # Category 3: Regional Residency Subdomains
            ("https://us-aiplatform.rep.googleapis.com", "us"),
            ("https://eu-aiplatform.rep.googleapis.com", "eu"),
            ("https://europe-west1-aiplatform.rep.googleapis.com", "europe-west1"),
            # Category 4: Global Default Endpoint
            ("https://aiplatform.googleapis.com", "us-central1"),
        ],
    )
    def test_valid_api_roots(self, api_root: str, expected_location: str, mocker):
        action = DummyAction.__new__(DummyAction)
        mock_params = mocker.Mock()
        mock_params.api_root = api_root
        action._params = mock_params

        match = action._validate_api_root()
        assert match is not None

        location = action._BaseAction__get_fallback_location()
        assert location == expected_location

    @pytest.mark.parametrize(
        "invalid_api_root",
        [
            # Non-HTTPS Protocols
            "http://us-central1-aiplatform.googleapis.com",
            "http://aiplatform.us.rep.googleapis.com",
            "ftp://aiplatform.googleapis.com",
            # Wrong Domain / TLD
            "https://invalid-domain.com",
            "https://us-central1-aiplatform.google.com",
            "https://aiplatform.us.rep.googleapis.org",
            "https://aiplatform.us.rep.otherdomain.com",
            # Trailing Paths, Queries, and Fragments
            "https://aiplatform.googleapis.com/v1/projects",
            "https://us-central1-aiplatform.googleapis.com/",
            "https://us-central1-aiplatform.googleapis.com?query=1",
            "https://us-central1-aiplatform.googleapis.com#fragment",
            # Invalid Special Characters
            "https://us_central1-aiplatform.googleapis.com",
            "https://us.central1-aiplatform.googleapis.com",
            "https://-aiplatform.googleapis.com",
            "https://aiplatform..rep.googleapis.com",
            # Domain Spoofing / Extra Subdomains
            "https://fake-us-central1-aiplatform.googleapis.com.evil.com",
            "https://sub.us-central1-aiplatform.googleapis.com",
            # Malformed / Empty Inputs
            "",
            "   ",
            "https://",
            "aiplatform.googleapis.com",
            "not_a_url",
        ],
    )
    def test_invalid_api_roots(self, invalid_api_root: str, mocker):
        action = DummyAction.__new__(DummyAction)
        mock_params = mocker.Mock()
        mock_params.api_root = invalid_api_root
        action._params = mock_params

        with pytest.raises(VertexAIValidationException) as exc_info:
            action._validate_api_root()
        assert "expected pattern" in str(exc_info.value)

