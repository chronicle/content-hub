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

from unittest.mock import MagicMock
import pytest
import zscalerManager
from ..core.auth import AuthenticatedSession, SessionAuthenticationParameters
from ..core.data_models import IntegrationParameters
from ..core.exceptions import ZscalerManagerError


class TestZscalerOAuth:
    """
    Tests the OAuth 2.0 implementation in ZscalerManager using
    the strict soar-legacy-integration Black-Box mocking pattern.
    """

    def test_oauth_authentication_success(
        self,
        script_session,
    ) -> None:
        """
        Verifies that ZscalerManager correctly extracts an access token
        using the client credentials workflow via the central mocked session.
        """

        params = SessionAuthenticationParameters(
            api_root="https://admin.zscalertwo.net",
            client_id="test_client_id",
            client_secret="test_client_secret",
            login_api_root="https://siempify.zslogin.net",
        )
        auth_session = AuthenticatedSession()
        auth_session.authenticate_session(params, MagicMock())

        config = IntegrationParameters(
            api_root="https://admin.zscalertwo.net",
            client_id="test_client_id",
            client_secret="test_client_secret",
            login_api_root="https://siempify.zslogin.net",
        )

        manager: ZscalerManager.ZscalerManager = ZscalerManager.ZscalerManager(
            authenticated_session=auth_session,
            configuration=config,
            logger=None,
        )

        assert manager.use_oauth is True
        assert manager.use_legacy is False
        assert manager.authenticated_session.access_token == "mocked_oauth_token"
        auth_header = manager.session.headers.get("Authorization")
        assert auth_header == "Bearer mocked_oauth_token"
        # pylint: disable=protected-access
        assert script_session._is_authenticated is True

    def test_authentication_fallback_legacy(
        self,
        script_session,
    ) -> None:
        """
        Verifies that providing Legacy credentials falls back to the old method
        and sets internal auth state correctly on the mock session.
        """
        # pylint: disable=protected-access
        script_session._product.expected_api_key = "legacy_key"


        params = SessionAuthenticationParameters(
            api_root="https://admin.zscalertwo.net",
            login_id="admin@test.com",
            api_key="legacy_key",
            password="legacy_password",
        )
        auth_session = AuthenticatedSession()
        auth_session.authenticate_session(params, MagicMock())

        config = IntegrationParameters(
            api_root="https://admin.zscalertwo.net",
            login_id="admin@test.com",
            api_key="legacy_key",
            password="legacy_password",
        )

        manager: ZscalerManager.ZscalerManager = ZscalerManager.ZscalerManager(
            authenticated_session=auth_session,
            configuration=config,
            logger=None,
        )

        assert manager.use_oauth is False
        assert manager.use_legacy is True
        # pylint: disable=protected-access
        assert script_session._is_authenticated is True

    def test_authentication_missing_credentials(self) -> None:
        """
        Verifies that omitting all credentials raises a ZscalerManagerError.
        """

        with pytest.raises(ZscalerManagerError) as exc_info:
            params = SessionAuthenticationParameters(
                api_root="https://admin.zscalertwo.net"
            )
            auth_session = AuthenticatedSession()
            auth_session.authenticate_session(params, MagicMock())

        assert "Authentication failed" in str(exc_info.value)
