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
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
import requests

from censys.core.api_manager import APIManager
from censys.core.censys_exceptions import UnauthorizedErrorException, ValidationException
from censys.core.constants import RETRY_COUNT
from censys.core.params import IntegrationParams

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

TOKEN_POST: str = "censys.core.oauth.requests.post"
SESSION_REQUEST: str = "requests.Session.request"


class FakeSoar:
    """SOAR stand-in with a mock logger and an in-memory context store."""

    integration_identifier: str = "Censys"
    integration_instance: str = "instance-1"

    def __init__(self) -> None:
        """Create the logger and the empty context store."""
        self.LOGGER = MagicMock()
        self.store: dict[tuple[str, str], str] = {}

    def get_system_version(self) -> str:
        """Return a fixed platform version for the User-Agent header."""
        return "1.0.0"

    def get_context_property(
        self,
        context_type: int,
        identifier: str,
        property_key: str,
    ) -> str | None:
        """Return a stored value, or None when it was never saved."""
        return self.store.get((identifier, property_key))

    def set_context_property(
        self,
        context_type: int,
        identifier: str,
        property_key: str,
        property_value: str,
    ) -> None:
        """Store a value under the given identifier and key."""
        self.store[(identifier, property_key)] = property_value


def _token_response(token: str, expires_in: int = 3599) -> MagicMock:
    """Build a successful token endpoint response."""
    response = MagicMock()
    response.status_code = 200
    response.ok = True
    response.json.return_value = {
        "access_token": token,
        "expires_in": expires_in,
        "token_type": "bearer",
    }
    return response


def _api_response(status: int, body: SingleJson | None = None) -> requests.Response:
    """Build a real ``requests.Response`` so raise_for_status behaves as in production."""
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(body if body is not None else {}).encode()
    return response


def _oauth_manager(soar: FakeSoar) -> APIManager:
    """Build an OAuth-mode API manager."""
    params = IntegrationParams(
        organization_id="org",
        use_oauth=True,
        client_id="cid",
        client_secret="secret",
    )
    return APIManager(params, siemplify=soar)


class TestAuthenticationSetup:
    """The API manager picks the credential for the selected method."""

    def test_oauth_mode_sends_the_access_token(self) -> None:
        """In OAuth mode the Authorization header carries the access token."""
        with patch(TOKEN_POST, return_value=_token_response("tok-1")) as post:
            manager = _oauth_manager(FakeSoar())

        assert manager.session.headers["Authorization"] == "Bearer tok-1"
        assert manager.oauth_manager is not None
        assert post.call_count == 1

    def test_api_key_mode_never_requests_a_token(self) -> None:
        """In API Key mode the key is sent as is and no OAuth manager exists."""
        with patch(TOKEN_POST) as post:
            manager = APIManager(IntegrationParams(organization_id="org", api_key="key-1"), siemplify=FakeSoar())

        assert manager.session.headers["Authorization"] == "Bearer key-1"
        assert manager.oauth_manager is None
        post.assert_not_called()

    def test_rejected_oauth_credentials_fail_before_any_api_call(self) -> None:
        """A rejected Client ID or Secret stops construction without calling Censys."""
        rejected = MagicMock(status_code=401, ok=False, text="invalid_client")
        with patch(TOKEN_POST, return_value=rejected):
            with patch(SESSION_REQUEST) as request:
                with pytest.raises(UnauthorizedErrorException, match="Client ID and Client Secret"):
                    _oauth_manager(FakeSoar())

        request.assert_not_called()

    def test_session_is_closed_when_oauth_setup_fails(self) -> None:
        """A rejected token request must not leave the HTTP session open."""
        rejected = MagicMock(status_code=401, ok=False, text="invalid_client")
        with patch(TOKEN_POST, return_value=rejected), patch("requests.Session.close") as close:
            with pytest.raises(UnauthorizedErrorException):
                _oauth_manager(FakeSoar())

        close.assert_called_once()

    def test_session_stays_open_when_oauth_setup_succeeds(self) -> None:
        """The session is only closed on failure."""
        with patch(TOKEN_POST, return_value=_token_response("tok-1")), patch("requests.Session.close") as close:
            _oauth_manager(FakeSoar())

        close.assert_not_called()

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"use_oauth": False, "api_key": ""}, "API Key is required"),
            ({"use_oauth": True, "client_id": "cid"}, "Client ID and Client Secret are required"),
            ({"use_oauth": True, "client_secret": "s"}, "Client ID and Client Secret are required"),
        ],
    )
    def test_missing_credentials_raise_before_any_request(
        self,
        kwargs: SingleJson,
        message: str,
    ) -> None:
        """Missing credentials for the selected method raise a validation error."""
        with patch(TOKEN_POST) as post, patch(SESSION_REQUEST) as request:
            with pytest.raises(ValidationException, match=message):
                APIManager(IntegrationParams(organization_id="org", **kwargs), siemplify=FakeSoar())

        post.assert_not_called()
        request.assert_not_called()

    def test_oauth_without_a_soar_object_raises_before_any_request(self) -> None:
        """OAuth caches the token in the SOAR context, so a missing SOAR object is a clear error."""
        params = IntegrationParams(
            organization_id="org",
            use_oauth=True,
            client_id="cid",
            client_secret="secret",
        )
        with patch(TOKEN_POST) as post, patch(SESSION_REQUEST) as request:
            with pytest.raises(ValidationException, match="Chronicle SOAR instance is required"):
                APIManager(params, siemplify=None)

        post.assert_not_called()
        request.assert_not_called()


class TestUnauthorizedHandling:
    """A 401 refreshes the token once in OAuth mode and is final in API Key mode."""

    def test_401_refreshes_the_token_and_retries_once(self) -> None:
        """A revoked token is replaced and the request is repeated with the new one."""
        soar = FakeSoar()
        tokens = [_token_response("tok-1"), _token_response("tok-2")]
        with patch(TOKEN_POST, side_effect=tokens) as post:
            manager = _oauth_manager(soar)
            with patch(
                SESSION_REQUEST,
                side_effect=[_api_response(401), _api_response(200, {"result": "ok"})],
            ) as request:
                result = manager.test_connectivity()

        assert result is True
        assert request.call_count == 2
        assert post.call_count == 2
        assert manager.session.headers["Authorization"] == "Bearer tok-2"
        logged = " ".join(c.args[0] for c in soar.LOGGER.info.call_args_list)
        assert "Request was rejected with 401" in logged

    def test_refresh_does_not_log_a_cached_token_reuse_or_request_a_third_token(self) -> None:
        """A token with a very short lifetime is used as returned, with one extra token request."""
        soar = FakeSoar()
        tokens = [_token_response("tok-1"), _token_response("tok-2", expires_in=30)]
        with patch(TOKEN_POST, side_effect=tokens) as post:
            manager = _oauth_manager(soar)
            with patch(
                SESSION_REQUEST,
                side_effect=[_api_response(401), _api_response(200, {"result": "ok"})],
            ):
                assert manager.test_connectivity() is True

        assert post.call_count == 2
        assert manager.session.headers["Authorization"] == "Bearer tok-2"
        logged = " ".join(c.args[0] for c in soar.LOGGER.info.call_args_list)
        assert "Reusing cached access token" not in logged

    def test_401_after_rate_limit_retries_still_refreshes_the_token(self) -> None:
        """Using up the rate-limit retries does not stop a later 401 from refreshing the token."""
        tokens = [_token_response("tok-1"), _token_response("tok-2")]
        responses = [_api_response(429) for _ in range(RETRY_COUNT)]
        responses += [_api_response(401), _api_response(200, {"result": "ok"})]
        with patch(TOKEN_POST, side_effect=tokens) as post:
            manager = _oauth_manager(FakeSoar())
            with patch(SESSION_REQUEST, side_effect=responses), patch("censys.core.api_manager.time.sleep"):
                assert manager.test_connectivity() is True

        assert post.call_count == 2
        assert manager.session.headers["Authorization"] == "Bearer tok-2"

    def test_second_401_is_reported_with_oauth_wording_and_not_retried_again(self) -> None:
        """If the new token is rejected too, the error names the OAuth settings."""
        tokens = [_token_response("tok-1"), _token_response("tok-2")]
        with patch(TOKEN_POST, side_effect=tokens):
            manager = _oauth_manager(FakeSoar())
            with patch(
                SESSION_REQUEST,
                side_effect=[_api_response(401), _api_response(401)],
            ) as request:
                with pytest.raises(UnauthorizedErrorException, match="Client ID, Client Secret"):
                    manager.test_connectivity()

        assert request.call_count == 2

    def test_api_key_401_is_not_retried_and_keeps_the_original_message(self) -> None:
        """In API Key mode a 401 is reported once with the original wording."""
        manager = APIManager(IntegrationParams(organization_id="org", api_key="key-1"), siemplify=FakeSoar())
        with patch(SESSION_REQUEST, return_value=_api_response(401)) as request:
            with pytest.raises(UnauthorizedErrorException, match="verify your API Key"):
                manager.test_connectivity()

        assert request.call_count == 1
