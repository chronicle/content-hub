from unittest.mock import MagicMock, patch

import pytest
from core.opencti_client.client import OpenCTIClient, OpenCTIClientError


@pytest.fixture
def mock_pycti_client():
    """Return a MagicMock replacing pycti.OpenCTIApiClient."""
    with patch("core.opencti_client.client.OpenCTIApiClient") as mock_cls:
        instance = MagicMock()
        mock_cls.return_value = instance
        yield instance


@pytest.fixture
def client(mock_pycti_client):
    return OpenCTIClient(
        base_url="https://opencti.example.com",
        api_token="token",
    )


class TestOpenCTIClientInit:
    def test_health_check_called_on_successful_connection(self):
        with patch("pycti.OpenCTIApiClient.health_check") as mock_health_check:
            mock_health_check.return_value = True

            OpenCTIClient(base_url="https://opencti.example.com", api_token="token")

            mock_health_check.assert_called_once()

    def test_raises_on_invalid_connection(self):
        with patch("core.opencti_client.client.OpenCTIApiClient") as mock_cls:
            mock_cls.side_effect = ValueError("bad url")

            with pytest.raises(
                OpenCTIClientError, match="Failed to establish connection"
            ):
                OpenCTIClient(base_url="bad", api_token="token")
