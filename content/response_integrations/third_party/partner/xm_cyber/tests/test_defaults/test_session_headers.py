from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests

from xm_cyber.core.ApiManager import ApiManager
from xm_cyber.core.constants import (
    CONNECTOR_NAME_VERSION_HEADER,
    INTEGRATION_IDENTIFIER,
    INTEGRATION_VERSION,
)

EXPECTED_HEADER_VALUE = f"{INTEGRATION_IDENTIFIER}-v{INTEGRATION_VERSION}"


def _mock_siemplify() -> MagicMock:
    siemplify = MagicMock()
    siemplify.LOGGER = MagicMock()
    siemplify.integration_instance = "test-instance"
    return siemplify


class TestConnectorNameVersionHeader:
    def test_header_set_for_api_key_auth(self) -> None:
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        with patch.object(requests.Session, "request", return_value=mock_response):
            manager = ApiManager(
                auth_type=False,
                base_url="https://test.xmcyber.com",
                api_key="test-api-key",
                siemplify=_mock_siemplify(),
            )

        assert manager.session.headers[CONNECTOR_NAME_VERSION_HEADER] == EXPECTED_HEADER_VALUE

    def test_header_survives_oauth_session_replacement(self) -> None:
        # _init_oauth replaces self.session with a fresh AuthorizedOauthClient,
        # so the header must be re-applied there rather than only at the
        # requests.Session created earlier in __init__.
        mock_oauth_manager = MagicMock()
        mock_oauth_manager.refresh_if_expired.return_value = False

        with (
            patch("xm_cyber.core.ApiManager.XMCyberOAuthAdapter"),
            patch("xm_cyber.core.ApiManager.CredStorage"),
            patch(
                "xm_cyber.core.ApiManager.XMCyberOAuthManager",
                return_value=mock_oauth_manager,
            ),
        ):
            manager = ApiManager(
                auth_type=True,
                base_url="https://test.xmcyber.com",
                api_key="test-api-key",
                siemplify=_mock_siemplify(),
            )

        assert manager.session.headers[CONNECTOR_NAME_VERSION_HEADER] == EXPECTED_HEADER_VALUE
