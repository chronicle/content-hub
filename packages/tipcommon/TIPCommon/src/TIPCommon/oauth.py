# Copyright 2025 Google LLC
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

import abc
import dataclasses
import json

from httpx import Client, Response

from .consts import GLOBAL_CONTEXT_SCOPE
from .encryption import decrypt, encrypt
from .smp_time import unix_now
from .types import ChronicleSOAR, JsonString, SingleJson

DB_TOKEN_KEY = "OAUTH_TOKEN"


class AuthorizedOauthClient(Client):
    """This class represents an authorized client for API calls."""

    def __init__(self, oauth_manager: OauthManager, *args, **kwargs) -> None:
        self.oauth_manager = oauth_manager
        super().__init__(*args, **kwargs)

        token_expired = self.oauth_manager.refresh_if_expired(self)
        if not token_expired:
            self.oauth_manager.prepare_authorized_client(self)

    def request(self, *args, **kwargs) -> Response:
        """Overwrite to support automatic credential refresh.

        The method will check if credentials are expired before executing request.
        It will also validate the response to check if it indicates expired creds,
        if that's the case, it will execute the request again with refreshed token.
        """
        self.oauth_manager.refresh_if_expired(self)
        response = super().request(*args, **kwargs)

        if self.oauth_manager.refresh_if_bad_credentials(self, response):
            response = super().request(*args, **kwargs)

        return response

    def close(self) -> None:
        """Saves the token and closes client session."""
        self.oauth_manager.save_token()
        super().close()

    def __exit__(self, *args, **kwargs) -> None:
        self.oauth_manager.save_token()
        super().__exit__(*args, **kwargs)


class OauthManager:
    def __init__(self, oauth_adapter: OAuthAdapter, cred_storage: CredStorage) -> None:
        self._oauth_adapter = oauth_adapter
        self._cred_storage = cred_storage
        self._token = self._fetch_token()

    def _fetch_token(self) -> OauthToken | None:
        try:
            return self._cred_storage.get_token()
        except EncryptionError:
            # The token cannot be decrypted, invalidate it
            return None

    def _refresh_token(self) -> None:
        token = self._oauth_adapter.refresh_token()
        self._token = token

    def _token_is_expired(self) -> bool:
        return (
            self._token is None
            or not self._oauth_adapter.check_signer(self._token)
            or self._token.expiration_time > unix_now()
        )

    def save_token(self) -> None:
        if self._token is None:
            return

        self._cred_storage.set_token(self._token)

    def prepare_authorized_client(
        self,
        auth_client: AuthorizedOauthClient,
    ) -> AuthorizedOauthClient:
        return self._oauth_adapter.prepare_authorized_client(self._token, auth_client)

    def refresh_if_bad_credentials(
        self,
        auth_client: AuthorizedOauthClient,
        response: Response,
    ) -> bool:
        """If the response indicates bad credentials, token will be refreshed."""
        try:
            self._oauth_adapter.validate_bad_credentials(response)
        except AuthenticationError:
            self._refresh_token()
            self.prepare_authorized_client(auth_client)
            return True

        return False

    def refresh_if_expired(self, auth_client: AuthorizedOauthClient) -> bool:
        """Refreshes the token if it's expired."""
        if not self._token_is_expired():
            return False

        self._refresh_token()
        self.prepare_authorized_client(auth_client=auth_client)
        return True


class OAuthAdapter(abc.ABC):
    @abc.abstractmethod
    def check_signer(self, token: OauthToken) -> bool:
        """Returns True if signer is valid, false otherwise."""

    @abc.abstractmethod
    def refresh_token(self) -> OauthToken:
        """Refreshes the token and returns OauthToken data model."""

    @staticmethod
    @abc.abstractmethod
    def validate_bad_credentials(response: Response) -> bool:
        """Checks if the response indicates expired credentials.

        Raises:
            AuthenticationError - if the response indicates expired credentials

        """

    @abc.abstractmethod
    def prepare_authorized_client(
        self,
        token: OauthToken,
        auth_client: AuthorizedOauthClient,
    ) -> AuthorizedOauthClient:
        """Sets headers of whatever is needed for the client."""


@dataclasses.dataclass
class OauthToken:
    access_token: str
    expiration_time: int
    refresh_token: str = None
    signer: str = None
    additional_data: SingleJson = dataclasses.field(default_factory=dict)

    def to_cache(self) -> JsonString:
        return json.dumps({
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "signer": self.signer,
            "expiration_time": self.expiration_time,
            "additional_data": self.additional_data,
        })

    @classmethod
    def from_cache(cls, raw_data: JsonString) -> OauthToken:
        return cls(**json.loads(raw_data))


class CredStorage:
    def __init__(
        self,
        encryption_password: str,
        chronicle_soar: ChronicleSOAR,
    ) -> None:
        self.encryption_password = encryption_password
        self.chronicle_soar = chronicle_soar

    def get_instance_identifier(self) -> str:
        """Get SOAR instance identifier, either of connector or integration."""
        if hasattr(self.chronicle_soar, "integration_identifier"):
            return self.chronicle_soar.integration_instance

        if hasattr(self.chronicle_soar, "context"):
            return self.chronicle_soar.context.connector_info.identifier

        raise AuthenticationError("Can't extract instance identifier from ChronicleSOAR context.")

    def get_token(self) -> OauthToken | None:
        """Extract ad decrypt a token from context database."""
        encrypted_data = self.chronicle_soar.get_context_property(
            context_type=GLOBAL_CONTEXT_SCOPE,
            identifier=self.get_instance_identifier(),
            property_key=DB_TOKEN_KEY,
        )
        if encrypted_data is None:
            return None

        token_data = self._decrypt(encrypted_data.encode())
        return OauthToken.from_cache(token_data)

    def set_token(self, token: OauthToken) -> None:
        """Encrypt ad save a token into context database."""
        encrypted_data = self._encrypt(token.to_cache())
        self.chronicle_soar.set_context_property(
            context_type=GLOBAL_CONTEXT_SCOPE,
            identifier=self.get_instance_identifier(),
            property_key=DB_TOKEN_KEY,
            property_value=encrypted_data.decode(),
        )

    def _decrypt(self, encrypted_data: bytes) -> str:
        try:
            return decrypt(encrypted_data, key=self.encryption_password)
        except UnicodeError as err:
            raise EncryptionError("Can't decrypt token from ChronicleSOAR context.") from err

    def _encrypt(self, raw_data: str) -> bytes:
        return encrypt(raw_data, key=self.encryption_password)


class EncryptionError(Exception):
    """Generic exception for Encryption errors."""


class AuthenticationError(Exception):
    """Generic exception for AuthenticationErrors."""
