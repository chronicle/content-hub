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

import hashlib
from typing import Protocol

import requests
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.oauth import (
    AuthenticationError,
    CredStorage,
    OAuthAdapter,
    OauthManager,
    OauthToken,
)
from TIPCommon.smp_time import unix_now
from TIPCommon.types import ChronicleSOAR

from .censys_exceptions import CensysException, UnauthorizedErrorException
from .constants import (
    AUTH_ENDPOINT,
    DEFAULT_AUTH_URL,
    DEFAULT_REQUEST_TIMEOUT,
    OAUTH_AUDIENCE,
    OAUTH_DEFAULT_EXPIRY_SECONDS,
    OAUTH_SCOPE,
    OAUTH_TOKEN_EXPIRY_BUFFER_SECONDS,
    UNAUTHORIZED_STATUS_CODE,
)
from .params import IntegrationParams

PBKDF2_ITERATIONS: int = 200_000


class InfoLogger(Protocol):
    """Anything with an ``info`` method, such as the SOAR action logger."""

    def info(self, message: str) -> None:
        """Write an informational message."""


def generate_encryption_key(client_id: str, client_secret: str, organization_id: str) -> str:
    """Derive the key used to encrypt the cached access token.

    The key is derived from ``client_id:client_secret`` with the organization ID as the salt, so
    changing any of the three values makes the previously cached token undecryptable and forces a
    fresh token request.

    Args:
        client_id: Censys OAuth Client ID.
        client_secret: Censys OAuth Client Secret.
        organization_id: Censys Organization ID.

    Returns:
        str: Hex-encoded 32 byte key.
    """
    key_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        f"{client_id}:{client_secret}".encode(),
        organization_id.encode(),
        PBKDF2_ITERATIONS,
        dklen=32,
    )
    return key_bytes.hex()


def _usable_lifetime_seconds(expires_in: object) -> int:
    """Return how long a token may be used, after subtracting the safety buffer.

    Args:
        expires_in: The ``expires_in`` value from the token response, if any.

    Returns:
        int: Seconds the token can be reused; falls back to the default lifetime when the value
            is missing or not a number.
    """
    try:
        lifetime = int(expires_in) if expires_in is not None else OAUTH_DEFAULT_EXPIRY_SECONDS
    except (TypeError, ValueError):
        lifetime = OAUTH_DEFAULT_EXPIRY_SECONDS
    return max(lifetime - OAUTH_TOKEN_EXPIRY_BUFFER_SECONDS, 0)


def _error_code(response: requests.Response) -> str:
    """Return the OAuth ``error`` code of a failed token response, formatted for a message.

    Only the short error code is used; the response body is never copied into messages or logs.

    Args:
        response: The failed token endpoint response.

    Returns:
        str: `` - <error code>`` or an empty string when the body has no error code.
    """
    try:
        code = response.json().get("error")
    except (AttributeError, ValueError, TypeError):
        return ""
    return f" - {code}" if isinstance(code, str) and code else ""


class CensysOAuthAdapter(OAuthAdapter):
    """Adapter that obtains Censys access tokens using the client credentials grant."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        verify_ssl: bool = False,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.verify_ssl = verify_ssl

    def check_signer(self, token: OauthToken) -> bool:
        """Return True if the cached token was issued for the configured Client ID."""
        return token.signer == self.client_id

    def refresh_token(self) -> OauthToken:
        """Request a new access token from the Censys OAuth server.

        Returns:
            OauthToken: The new token, with its absolute expiration time in milliseconds.

        Raises:
            UnauthorizedErrorException: If the client credentials are rejected.
            CensysException: If the token request fails for any other reason.
        """
        try:
            response = requests.post(
                f"{DEFAULT_AUTH_URL}{AUTH_ENDPOINT}",
                auth=(self.client_id, self.client_secret),
                data={
                    "grant_type": "client_credentials",
                    "scope": OAUTH_SCOPE,
                    "audience": OAUTH_AUDIENCE,
                },
                verify=self.verify_ssl,
                timeout=DEFAULT_REQUEST_TIMEOUT,
            )
        except requests.RequestException as e:
            raise CensysException(f"Failed to connect to the Censys OAuth server: {e}")

        if response.status_code == UNAUTHORIZED_STATUS_CODE:
            raise UnauthorizedErrorException(
                "OAuth authentication failed. Please verify your Client ID and Client Secret."
            )
        if not response.ok:
            raise CensysException(
                f"Failed to obtain OAuth access token: HTTP {response.status_code}{_error_code(response)}"
            )

        try:
            data = response.json()
            access_token = data["access_token"]
        except (KeyError, ValueError, TypeError) as e:
            raise CensysException(f"Invalid OAuth token response: {e}")

        expires_in = _usable_lifetime_seconds(data.get("expires_in"))

        return OauthToken(
            access_token=access_token,
            expiration_time=unix_now() + expires_in * NUM_OF_MILLI_IN_SEC,
            signer=self.client_id,
            additional_data={"type": data.get("token_type", "bearer")},
        )

    @staticmethod
    def validate_bad_credentials(response: object) -> bool:
        """Not used; requests are made with a plain session and 401s are handled by the caller."""
        return False

    def prepare_authorized_client(self, token: OauthToken, auth_client: object) -> object:
        """Not used; the access token is read directly from the manager."""
        return auth_client


class CensysOAuthManager(OauthManager):
    """OauthManager with a corrected expiry check and a plain-token accessor.

    TIPCommon's ``OauthManager._token_is_expired`` treats a token as expired while its expiration
    time is still in the future (``expiration_time > unix_now()``), so a valid cached token is never
    reused and a new one is requested on every run.
    """

    def _fetch_token(self) -> OauthToken | None:
        """Load the cached token, treating anything that cannot be read as no token.

        Decrypting with a different key (changed credentials) does not always raise the
        ``EncryptionError`` that TIPCommon expects; it can also fail while unpadding or parsing.
        """
        try:
            return self._cred_storage.get_token()
        except Exception:
            return None

    def _token_is_expired(self) -> bool:
        """Return True when there is no usable cached token or it has reached its expiry time."""
        if self._token is None or not self._oauth_adapter.check_signer(self._token):
            return True
        return self._token.expiration_time <= unix_now()

    def __init__(
        self,
        oauth_adapter: OAuthAdapter,
        cred_storage: CredStorage,
        logger: InfoLogger | None = None,
    ) -> None:
        """Create the manager and load any cached token.

        Args:
            oauth_adapter: Adapter used to request new tokens.
            cred_storage: Encrypted storage holding the cached token.
            logger: Optional logger for the ``[OAuth]`` lifecycle messages.
        """
        self._logger = logger
        super().__init__(oauth_adapter, cred_storage)

    def _log(self, message: str) -> None:
        """Write an ``[OAuth]`` message to the logger, if one was given."""
        if self._logger is not None:
            self._logger.info(f"[OAuth] {message}")

    def get_access_token(self) -> str:
        """Return a valid access token, requesting and caching a new one only when needed."""
        if self._token is None:
            self._log("No usable cached access token found. Requesting a new one.")
            self.force_refresh()
        elif not self._oauth_adapter.check_signer(self._token):
            self._log("Cached access token belongs to a different Client ID. Requesting a new one.")
            self.force_refresh()
        elif self._token_is_expired():
            self._log("Cached access token has expired. Requesting a new one.")
            self.force_refresh()
        else:
            remaining = (self._token.expiration_time - unix_now()) // NUM_OF_MILLI_IN_SEC
            self._log(f"Reusing cached access token (valid for another {remaining}s).")
        return self._token.access_token

    def force_refresh(self) -> None:
        """Request a new access token and persist it."""
        try:
            self._refresh_token()
        except AuthenticationError as e:
            raise UnauthorizedErrorException(str(e))
        self.save_token()
        remaining = (self._token.expiration_time - unix_now()) // NUM_OF_MILLI_IN_SEC
        self._log(f"New access token obtained and stored (valid for {remaining}s).")


def build_oauth_manager(
    params: IntegrationParams,
    siemplify: ChronicleSOAR,
    logger: InfoLogger | None = None,
) -> CensysOAuthManager:
    """Create an OAuth manager backed by encrypted credential storage.

    Args:
        params: Integration configuration holding the Client ID, Client Secret,
            Organization ID and SSL setting.
        siemplify: SOAR object whose context store holds the encrypted token.
        logger: Optional logger for the ``[OAuth]`` lifecycle messages.

    Returns:
        CensysOAuthManager: Manager that returns a valid access token.
    """
    return CensysOAuthManager(
        oauth_adapter=CensysOAuthAdapter(params.client_id, params.client_secret, params.verify_ssl),
        cred_storage=CredStorage(
            encryption_password=generate_encryption_key(
                params.client_id,
                params.client_secret,
                params.organization_id,
            ),
            chronicle_soar=siemplify,
        ),
        logger=logger,
    )
