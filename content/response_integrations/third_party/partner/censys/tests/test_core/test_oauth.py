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

from typing import NamedTuple
from unittest.mock import MagicMock, patch

import pytest
import requests
from TIPCommon.oauth import AuthenticationError
from TIPCommon.smp_time import unix_now
from TIPCommon.types import SingleJson

from censys.core.censys_exceptions import CensysException, UnauthorizedErrorException
from censys.core.oauth import (
    CensysOAuthAdapter,
    CensysOAuthManager,
    build_oauth_manager,
    generate_encryption_key,
)
from censys.core.params import IntegrationParams

TOKEN_POST: str = "censys.core.oauth.requests.post"


class Credentials(NamedTuple):
    """Client ID, Client Secret and Organization ID used to build a manager."""

    client_id: str = "cid"
    client_secret: str = "secret"
    organization_id: str = "org"


class FakeSiemplify:
    """Minimal SOAR stand-in with an in-memory context store."""

    integration_identifier: str = "Censys"
    integration_instance: str = "instance-1"

    def __init__(self) -> None:
        """Create an empty context store."""
        self.store: dict[tuple[str, str], str] = {}

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


def _response(status: int = 200, body: SingleJson | None = None) -> MagicMock:
    """Build a fake ``requests`` response for the token endpoint."""
    response = MagicMock()
    response.status_code = status
    response.ok = status < 400
    response.text = str(body)
    response.json.return_value = body if body is not None else {}
    return response


def _token_body(token: str = "tok-1", expires_in: int | str = 3599) -> SingleJson:
    """Build a token endpoint response body."""
    return {"access_token": token, "expires_in": expires_in, "token_type": "bearer"}


def _manager(
    siemplify: FakeSiemplify,
    credentials: Credentials | None = None,
) -> CensysOAuthManager:
    """Build an OAuth manager backed by the fake SOAR context store."""
    creds = credentials or Credentials()
    params = IntegrationParams(
        organization_id=creds.organization_id,
        use_oauth=True,
        client_id=creds.client_id,
        client_secret=creds.client_secret,
    )
    return build_oauth_manager(params, siemplify)


class TestEncryptionKey:
    """The cache encryption key depends on all three configuration values."""

    def test_deterministic(self) -> None:
        """The same inputs always give the same key."""
        assert generate_encryption_key("a", "b", "c") == generate_encryption_key("a", "b", "c")

    @pytest.mark.parametrize(
        "other",
        [("x", "b", "c"), ("a", "x", "c"), ("a", "b", "x")],
    )
    def test_changes_with_any_input(self, other: tuple[str, str, str]) -> None:
        """Changing the Client ID, Client Secret or Organization ID changes the key."""
        assert generate_encryption_key("a", "b", "c") != generate_encryption_key(*other)


class TestTokenCaching:
    """Tokens are stored encrypted, reused while valid and replaced when stale."""

    def test_first_call_fetches_and_stores_encrypted_token(self) -> None:
        """The first call requests a token and stores it without the raw value."""
        soar = FakeSiemplify()
        with patch(TOKEN_POST, return_value=_response(200, _token_body())) as post:
            assert _manager(soar).get_access_token() == "tok-1"

        assert post.call_count == 1
        stored = next(iter(soar.store.values()))
        assert "tok-1" not in stored

    def test_valid_cached_token_is_reused(self) -> None:
        """A second manager reuses the stored token without a token request."""
        soar = FakeSiemplify()
        with patch(TOKEN_POST, return_value=_response(200, _token_body())) as post:
            _manager(soar).get_access_token()
            assert _manager(soar).get_access_token() == "tok-1"

        assert post.call_count == 1

    def test_expired_token_is_refreshed(self) -> None:
        """A token past its expiry time is replaced by a new one."""
        soar = FakeSiemplify()
        with patch(TOKEN_POST, return_value=_response(200, _token_body("tok-1"))):
            first = _manager(soar)
            first.get_access_token()
            first._token.expiration_time = unix_now() - 1000
            first.save_token()

        with patch(TOKEN_POST, return_value=_response(200, _token_body("tok-2"))) as post:
            assert _manager(soar).get_access_token() == "tok-2"

        assert post.call_count == 1

    @pytest.mark.parametrize(
        "second",
        [
            Credentials(client_id="other"),
            Credentials(client_secret="other"),
            Credentials(organization_id="other"),
        ],
    )
    def test_changed_credentials_do_not_reuse_token(self, second: Credentials) -> None:
        """Changing any credential value makes the stored token unusable."""
        soar = FakeSiemplify()
        with patch(TOKEN_POST, return_value=_response(200, _token_body("tok-1"))):
            _manager(soar).get_access_token()

        with patch(TOKEN_POST, return_value=_response(200, _token_body("tok-2"))) as post:
            assert _manager(soar, second).get_access_token() == "tok-2"

        assert post.call_count == 1

    def test_force_refresh_replaces_token(self) -> None:
        """force_refresh stores a new token that later calls return."""
        soar = FakeSiemplify()
        with patch(TOKEN_POST, return_value=_response(200, _token_body("tok-1"))):
            manager = _manager(soar)
            manager.get_access_token()
        with patch(TOKEN_POST, return_value=_response(200, _token_body("tok-2"))):
            manager.force_refresh()

        assert manager.get_access_token() == "tok-2"

    def test_token_issued_for_another_client_id_is_not_used(self) -> None:
        """A cached token whose signer is another Client ID is replaced."""
        soar = FakeSiemplify()
        with patch(TOKEN_POST, return_value=_response(200, _token_body("tok-1"))):
            manager = _manager(soar)
            manager.get_access_token()

        manager._token.signer = "someone-else"
        logger = MagicMock()
        manager._logger = logger
        with patch(TOKEN_POST, return_value=_response(200, _token_body("tok-2"))) as post:
            assert manager.get_access_token() == "tok-2"

        assert post.call_count == 1
        assert "different Client ID" in " ".join(c.args[0] for c in logger.info.call_args_list)

    def test_unreadable_cached_token_is_logged_and_replaced(self) -> None:
        """A token that cannot be decrypted (changed credentials) is logged and replaced."""
        soar = FakeSiemplify()
        with patch(TOKEN_POST, return_value=_response(200, _token_body("tok-1"))):
            _manager(soar).get_access_token()

        logger = MagicMock()
        params = IntegrationParams(
            organization_id="org",
            use_oauth=True,
            client_id="cid",
            client_secret="rotated-secret",
        )
        with patch(TOKEN_POST, return_value=_response(200, _token_body("tok-2"))) as post:
            manager = build_oauth_manager(params, soar, logger=logger)
            assert manager.get_access_token() == "tok-2"

        messages = " ".join(c.args[0] for c in logger.info.call_args_list)
        assert post.call_count == 1
        assert "could not be read" in messages
        assert "tok-1" not in messages

    def test_adapter_authentication_error_is_reported_as_unauthorized(self) -> None:
        """An AuthenticationError from the adapter becomes UnauthorizedErrorException."""
        manager = _manager(FakeSiemplify())
        with patch.object(
            manager._oauth_adapter,
            "refresh_token",
            side_effect=AuthenticationError("rejected"),
        ):
            with pytest.raises(UnauthorizedErrorException, match="rejected"):
                manager.force_refresh()


class TestSecureDefaults:
    """SSL verification is on unless the Verify SSL parameter turns it off."""

    def test_adapter_verifies_ssl_by_default(self) -> None:
        """The adapter verifies certificates when no value is given."""
        assert CensysOAuthAdapter("cid", "secret").verify_ssl is True

    def test_integration_params_verify_ssl_by_default(self) -> None:
        """IntegrationParams verifies certificates when no value is given."""
        assert IntegrationParams(organization_id="org").verify_ssl is True

    def test_configured_value_reaches_the_token_request(self) -> None:
        """The Verify SSL value is passed to the token endpoint call."""
        with patch(TOKEN_POST, return_value=_response(200, _token_body())) as post:
            CensysOAuthAdapter("cid", "secret", verify_ssl=False).refresh_token()

        assert post.call_args.kwargs["verify"] is False


class TestAdapterErrors:
    """The adapter turns token endpoint problems into integration errors."""

    def test_401_raises_unauthorized(self) -> None:
        """A 401 from the token endpoint means the credentials were rejected."""
        with patch(TOKEN_POST, return_value=_response(401, {"error": "invalid_client"})):
            with pytest.raises(UnauthorizedErrorException):
                CensysOAuthAdapter("cid", "secret").refresh_token()

    def test_other_http_error_raises_censys_exception(self) -> None:
        """Any other failing status is reported with its status code and error code only."""
        body = {"error": "boom", "error_description": "internal detail that must not be echoed"}
        with patch(TOKEN_POST, return_value=_response(500, body)):
            with pytest.raises(CensysException, match="HTTP 500 - boom") as error:
                CensysOAuthAdapter("cid", "secret").refresh_token()

        assert "internal detail" not in str(error.value)

    def test_missing_access_token_raises(self) -> None:
        """A response without access_token is rejected."""
        with patch(TOKEN_POST, return_value=_response(200, {"expires_in": 10})):
            with pytest.raises(CensysException, match="Invalid OAuth token response"):
                CensysOAuthAdapter("cid", "secret").refresh_token()

    @pytest.mark.parametrize("body", [[1, 2], "not-json-object", 42, None])
    def test_non_object_token_body_raises_clean_error(self, body: object) -> None:
        """A token response that is not a JSON object becomes a CensysException, not a crash."""
        with patch(TOKEN_POST, return_value=_response(200, body)):
            with pytest.raises(CensysException, match="Invalid OAuth token response"):
                CensysOAuthAdapter("cid", "secret").refresh_token()

    def test_connection_error_raises_censys_exception(self) -> None:
        """A network failure while requesting the token is reported clearly."""
        with patch(TOKEN_POST, side_effect=requests.ConnectionError("no route")):
            with pytest.raises(CensysException, match="Failed to connect to the Censys OAuth") as error:
                CensysOAuthAdapter("cid", "secret").refresh_token()

        assert isinstance(error.value.__cause__, requests.ConnectionError)

    def test_expiry_includes_safety_buffer(self) -> None:
        """The stored lifetime is expires_in minus the 60 second safety buffer."""
        with patch(TOKEN_POST, return_value=_response(200, _token_body(expires_in=3600))):
            token = CensysOAuthAdapter("cid", "secret").refresh_token()

        remaining_ms = token.expiration_time - unix_now()
        assert 3500_000 < remaining_ms < 3600_000

    @pytest.mark.parametrize("expires_in", ["not-a-number", None])
    def test_invalid_expires_in_falls_back_to_default_lifetime(
        self,
        expires_in: str | None,
    ) -> None:
        """A missing or non-numeric expires_in uses the default lifetime."""
        body = _token_body()
        body["expires_in"] = expires_in
        with patch(TOKEN_POST, return_value=_response(200, body)):
            token = CensysOAuthAdapter("cid", "secret").refresh_token()

        remaining_ms = token.expiration_time - unix_now()
        assert 3500_000 < remaining_ms < 3600_000

    def test_expires_in_shorter_than_buffer_is_not_negative(self) -> None:
        """A very short lifetime does not produce an expiry time in the past."""
        with patch(TOKEN_POST, return_value=_response(200, _token_body(expires_in=10))):
            token = CensysOAuthAdapter("cid", "secret").refresh_token()

        assert token.expiration_time >= unix_now() - 1000


class TestLogging:
    """The token lifecycle is logged without ever logging the token."""

    def _logged(self, soar: FakeSiemplify) -> tuple[MagicMock, CensysOAuthManager]:
        """Build a manager whose logger is a mock."""
        logger = MagicMock()
        params = IntegrationParams(
            organization_id="org",
            use_oauth=True,
            client_id="cid",
            client_secret="secret",
        )
        return logger, build_oauth_manager(params, soar, logger=logger)

    def _messages(self, logger: MagicMock) -> str:
        """Join everything the logger received."""
        return " ".join(c.args[0] for c in logger.info.call_args_list)

    def test_logs_new_then_reuse_then_expired_without_leaking_token(self) -> None:
        """New, reused and expired tokens are logged and the token value is not."""
        soar = FakeSiemplify()
        with patch(TOKEN_POST, return_value=_response(200, _token_body("tok-secret"))):
            logger, manager = self._logged(soar)
            manager.get_access_token()
            assert "No usable cached access token" in self._messages(logger)
            assert "New access token obtained and stored" in self._messages(logger)

            logger, manager = self._logged(soar)
            manager.get_access_token()
            assert "Reusing cached access token" in self._messages(logger)

            manager._token.expiration_time = unix_now() - 1000
            manager.get_access_token()
            assert "has expired" in self._messages(logger)

        assert "tok-secret" not in self._messages(logger)
