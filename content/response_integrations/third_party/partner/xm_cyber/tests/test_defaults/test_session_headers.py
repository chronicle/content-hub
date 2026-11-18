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

"""Tests that ApiManager attaches the X-XMCYBER-CONNECTOR-NAME-VERSION header."""

from __future__ import annotations

import tomllib
from unittest.mock import MagicMock, patch

import requests

from xm_cyber.core.ApiManager import ApiManager
from xm_cyber.core.constants import (
    CONNECTOR_NAME_VERSION_HEADER,
    FALLBACK_INTEGRATION_VERSION,
    INTEGRATION_IDENTIFIER,
    INTEGRATION_VERSION,
)

from .. import common

EXPECTED_HEADER_VALUE: str = f"{INTEGRATION_IDENTIFIER}-v{INTEGRATION_VERSION}"


def _mock_siemplify() -> MagicMock:
    """Build a minimal Siemplify mock accepted by ApiManager."""
    siemplify = MagicMock()
    siemplify.LOGGER = MagicMock()
    siemplify.integration_instance = "test-instance"
    return siemplify


class TestConnectorNameVersionHeader:
    """Verify the connector name/version header is sent for every auth type."""

    def test_header_set_for_api_key_auth(self) -> None:
        """Header is present on the requests session when using an API key."""
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
        """Header is re-applied when _init_oauth swaps in an AuthorizedOauthClient."""
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


def test_fallback_version_matches_pyproject() -> None:
    """The metadata fallback must not drift from the version in pyproject.toml."""
    pyproject = common.INTEGRATION_PATH / "pyproject.toml"
    with pyproject.open("rb") as f:
        assert tomllib.load(f)["project"]["version"] == FALLBACK_INTEGRATION_VERSION
