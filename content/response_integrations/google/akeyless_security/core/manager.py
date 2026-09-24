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

"""Akeyless API client manager."""

from __future__ import annotations

import os
import threading
from typing import TYPE_CHECKING

import akeyless
import urllib3

from .constants import (
    ACCESS_KEY_TYPE,
    DEFAULT_MAX_RETRIES,
    DEFAULT_SECRET_VERSION,
)
from .exceptions import (
    ConnectivityError,
    InvalidConfigurationError,
    SecretAccessError,
)
from .utils import mask_id, validate_response

if TYPE_CHECKING:
    from TIPCommon.base.interfaces import ScriptLogger
    from TIPCommon.types import SingleJson

    from .datamodels import AkeylessClientConfig


class AkeylessClient:
    """Client for interacting with Akeyless."""

    def __init__(
        self,
        config: AkeylessClientConfig,
        logger: ScriptLogger | None = None,
    ) -> None:
        """Initialize the Akeyless Client.

        Args:
            config: Client configuration containing credentials and gateway settings.
            logger: Optional logger instance for diagnostic messages.

        Raises:
            InvalidConfigurationError: If Access ID or Access Key is not provided.

        """
        if not config.access_id or not config.access_key:
            msg = "Both Access ID and Access Key must be provided."
            raise InvalidConfigurationError(msg)

        self.config: AkeylessClientConfig = config
        self.logger: ScriptLogger | None = logger

        self.configuration: akeyless.Configuration = akeyless.Configuration()
        self.configuration.host = self.config.api_gateway_url
        self.configuration.verify_ssl = self.config.verify_ssl
        self.configuration.retries = DEFAULT_MAX_RETRIES
        if not self.config.verify_ssl:
            self.configuration.assert_hostname = False
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        proxy_url: str | None = (
            os.environ.get("https_proxy")
            or os.environ.get("HTTPS_PROXY")
            or os.environ.get("http_proxy")
            or os.environ.get("HTTP_PROXY")
        )
        if proxy_url:
            self.configuration.proxy = proxy_url

        self.api_client: akeyless.ApiClient = akeyless.ApiClient(self.configuration)
        self.api: akeyless.V2Api = akeyless.V2Api(self.api_client)
        self._token: str | None = None
        self._token_lock: threading.Lock = threading.Lock()

    def get_token(self) -> str:
        """Authenticate and return the active token.

        If a token is already cached for this client instance, returns it.
        Otherwise, authenticates and caches a new token using Access ID and Access Key.

        Returns:
            The active authentication token.

        Raises:
            ConnectivityError: If authentication fails or no token is returned.

        """
        if self._token:
            return self._token

        with self._token_lock:
            if self._token:
                return self._token

            try:
                auth_body: akeyless.Auth = akeyless.Auth(
                    access_id=self.config.access_id,
                    access_key=self.config.access_key,
                    access_type=ACCESS_KEY_TYPE,
                )
                auth_res: object = self.api.auth(auth_body)
            except Exception as e:
                validate_response(e, exception_cls=ConnectivityError)
                raise ConnectivityError(str(e)) from e

            token: str | None = getattr(auth_res, "token", None)
            if not token:
                msg = "Authentication succeeded but no token was returned by Akeyless."
                raise ConnectivityError(msg)

            self._token = str(token)
            return self._token

    def test_connectivity(self) -> bool:
        """Test connectivity to Akeyless by authenticating.

        Returns:
            True if connection is successful.

        """
        self.get_token()

        return True

    def get_secret_value(self, secret_id: str, version_id: str = DEFAULT_SECRET_VERSION) -> str:
        """Access a secret version.

        Args:
            secret_id: The ID of the secret.
            version_id: The version of the secret. Defaults to "latest".

        Returns:
            The secret payload data.

        Raises:
            InvalidConfigurationError: If version_id is not a positive integer or 'latest'.
            SecretAccessError: If access to the secret fails.

        """
        token: str = self.get_token()

        kwargs: SingleJson = {
            "names": [secret_id],
            "token": token,
        }
        if version_id and version_id != DEFAULT_SECRET_VERSION:
            try:
                version_num: int = int(version_id)
            except ValueError as e:
                msg = (
                    f"Invalid version '{version_id}' for secret '{mask_id(secret_id)}'. "
                    f"Version must be a positive integer or '{DEFAULT_SECRET_VERSION}'."
                )
                raise InvalidConfigurationError(msg) from e

            if version_num <= 0:
                msg = (
                    f"Invalid version '{version_id}' for secret '{mask_id(secret_id)}'. "
                    f"Version must be a positive integer or '{DEFAULT_SECRET_VERSION}'."
                )
                raise InvalidConfigurationError(msg)

            kwargs["version"] = version_num

        secret_body: akeyless.GetSecretValue = akeyless.GetSecretValue(**kwargs)
        try:
            response: object = self.api.get_secret_value(secret_body)
        except Exception as e:
            validate_response(e, exception_cls=SecretAccessError)
            raise SecretAccessError(str(e)) from e

        secret_val: object = (
            response.get(secret_id)
            if isinstance(response, dict)
            else getattr(response, secret_id, None)
        )

        if secret_val is None:
            msg = f"Secret '{mask_id(secret_id)}' not found in Akeyless response."
            raise SecretAccessError(msg)

        return str(secret_val)
