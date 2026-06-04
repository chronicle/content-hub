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

import logging
import time

import akeyless

from .constants import (
    DEFAULT_SECRET_VERSION,
    TOKEN_TTL_SECONDS,
)
from .exceptions import (
    ConnectivityError,
    InvalidConfigurationError,
    SecretAccessError,
)


class AkeylessClient:
    """Client for interacting with Akeyless."""

    def __init__(
        self,
        access_id: str,
        access_key: str | None = None,
        access_type: str = "gcp",
        api_gateway_url: str = "https://api.akeyless.io",
    ) -> None:
        """Initialize the Akeyless Client.

        Args:
            access_id (str): The Akeyless Access ID.
            access_key (str | None): The Akeyless Access Key.
            access_type (str): The Access Type. Defaults to "gcp".
            api_gateway_url (str): The Akeyless API Gateway URL. Defaults to "https://api.akeyless.io".

        """
        if not access_id:
            raise InvalidConfigurationError("Access ID must be provided.")

        self.access_id = access_id
        self.access_key = access_key
        self.access_type = access_type
        self.api_gateway_url = api_gateway_url

        self.configuration = akeyless.Configuration()
        self.configuration.host = self.api_gateway_url
        self.api_client = akeyless.ApiClient(self.configuration)
        self.api = akeyless.V2Api(self.api_client)
        self._token: str | None = None
        self._token_issued_at: float = 0.0
        self._logger = logging.getLogger(__name__)

    def _fetch_gcp_id_token(self, audience: str) -> str:
        """Fetch Google ID token from the GCP Metadata Server.

        Args:
            audience (str): The audience to request the token for (typically the Access ID).

        Returns:
            str: The Google ID token.

        """
        import urllib.request

        url = f"http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience={audience}"
        req = urllib.request.Request(url)
        req.add_header("Metadata-Flavor", "Google")
        try:
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.read().decode("utf-8")
        except Exception as e:
            raise RuntimeError(f"GCP Metadata server not reachable or token request failed: {e}")

    def _is_token_expired(self) -> bool:
        """Check whether the cached token has exceeded its TTL."""
        if not self._token:
            return True
        return (time.monotonic() - self._token_issued_at) >= TOKEN_TTL_SECONDS

    def _set_token(self, token: str) -> None:
        """Cache a token and record its issue time."""
        self._token = token
        self._token_issued_at = time.monotonic()

    def _clear_token(self) -> None:
        """Invalidate the cached token."""
        self._token = None
        self._token_issued_at = 0.0

    def get_token(self) -> str:
        """Authenticate and return the active token.

        If a valid (non-expired) token is already cached, returns it.
        Otherwise, authenticates and caches a new token.
        Supports GCP IAM Authentication (primary) and API Key Authentication (fallback).
        """
        if self._token and not self._is_token_expired():
            return self._token

        # Clear stale token before re-authenticating
        self._clear_token()

        if self.access_type == "gcp":
            try:
                gcp_token = self._fetch_gcp_id_token(self.access_id)
                auth_body = akeyless.Auth(
                    access_id=self.access_id,
                    access_type="gcp",
                    gcp_token=gcp_token,
                )
                auth_res = self.api.auth(auth_body)
                self._set_token(auth_res.token)
                return self._token
            except Exception as gcp_err:
                # Fall back to API Key auth if an Access Key is provided
                if self.access_key:
                    pass
                else:
                    raise ConnectivityError(
                        f"Failed to authenticate with Akeyless using GCP IAM: {gcp_err}"
                    ) from gcp_err

        try:
            auth_body = akeyless.Auth(
                access_id=self.access_id,
                access_key=self.access_key,
                access_type="access_key",
            )
            auth_res = self.api.auth(auth_body)
            self._set_token(auth_res.token)
            return self._token
        except Exception as e:
            raise ConnectivityError(f"Failed to authenticate with Akeyless: {e}") from e

    def test_connectivity(self) -> bool:
        """Test connectivity to Akeyless by authenticating."""
        try:
            self.get_token()
            return True
        except Exception as e:
            raise ConnectivityError(f"Failed to connect to Akeyless: {e}") from e

    def resolve_latest_enabled_version(self, secret_id: str) -> str:
        """Resolve the latest enabled version for a given secret.

        Akeyless natively handles version resolution to the latest version when no version
        is specified or when "latest" is used.
        """
        return DEFAULT_SECRET_VERSION

    def get_secret_value(self, secret_id: str, version_id: str = DEFAULT_SECRET_VERSION) -> str:
        """Access a secret version.

        Args:
            secret_id (str): The ID of the secret.
            version_id (str): The version of the secret. Defaults to "latest".

        Returns:
            str: The secret payload data.

        """
        token = self.get_token()

        try:
            kwargs: dict[str, object] = {
                "names": [secret_id],
                "token": token,
            }
            if version_id and version_id != DEFAULT_SECRET_VERSION:
                try:
                    kwargs["version"] = int(version_id)
                except ValueError:
                    self._logger.warn(
                        f"Invalid version '{version_id}' for secret '{secret_id}' "
                        f"— not an integer. Falling back to latest."
                    )

            secret_body = akeyless.GetSecretValue(**kwargs)
            response = self.api.get_secret_value(secret_body)

            if isinstance(response, dict):
                secret_val = response.get(secret_id)
            else:
                secret_val = getattr(response, secret_id, None)

            if secret_val is None:
                raise SecretAccessError(f"Secret '{secret_id}' not found in Akeyless response.")

            return str(secret_val)
        except SecretAccessError:
            raise
        except Exception as e:
            raise SecretAccessError(f"Failed to access secret version '{version_id}': {e}") from e
