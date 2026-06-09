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

"""Client for interacting with Secret Manager."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

from .authentication import create_authorized_session, get_credentials
from .constants import (
    DEFAULT_SECRET_VERSION,
    SECRET_MANAGER_API_BASE,
)
from .exceptions import (
    ConnectivityError,
    InvalidConfigurationError,
    SecretAccessError,
    SecretManagerError,
)
from .utils import validate_response

if TYPE_CHECKING:
    import requests
    from google.auth.transport.requests import AuthorizedSession
    from TIPCommon.base.interfaces.logger import ScriptLogger


class SecretManagerClient:
    """Client for interacting with Secret Manager."""

    def __init__(
        self,
        service_account_json: str | None = None,
        project_id: str | None = None,
        workload_identity_email: str | None = None,
        *,
        logger: ScriptLogger,
        verify_ssl: bool = True,
    ) -> None:
        """Initialize the Secret Manager Client.

        Exactly one of ``service_account_json`` or ``workload_identity_email``
        must be provided.  When ``workload_identity_email`` is given, the client
        authenticates via Application Default Credentials (ADC) and then
        impersonates the specified service account, which avoids the need to
        store a long-lived JSON key.

        Args:
            service_account_json (str | None): The Service Account JSON key string.
            project_id (str | None): The Google Cloud Project ID.
            workload_identity_email (str | None): The service account email to
                impersonate when using Workload Identity / ADC authentication.
            logger (ScriptLogger): Logger instance for logging.
            verify_ssl (bool): Whether to verify the server's SSL certificate.
                Defaults to True.

        Raises:
            InvalidConfigurationError: If neither Service Account JSON nor Workload Identity
                email is provided, or if Project ID is missing.

        """
        self.logger: ScriptLogger = logger
        self.verify_ssl: bool = verify_ssl

        self.credentials, self.project_id = get_credentials(
            service_account_json=service_account_json,
            project_id=project_id,
            workload_identity_email=workload_identity_email,
        )

        if not self.project_id:
            msg = (
                "Project ID must be provided. When using Service Account JSON, "
                "ensure it contains a 'project_id' field or set the 'Project ID' "
                "parameter explicitly. When using Workload Identity, 'Project ID' "
                "must always be set explicitly as it cannot be inferred."
            )
            raise InvalidConfigurationError(msg)

        self._session: AuthorizedSession = create_authorized_session(
            credentials=self.credentials,
            verify_ssl=self.verify_ssl,
        )

    def _rest_get(self, path: str, params: dict | None = None) -> dict:
        """Make an authenticated GET request to the Secret Manager REST API.

        Args:
            path (str): API path relative to the base URL (e.g.
                ``projects/my-proj/secrets``).
            params (dict | None): Optional query parameters.

        Returns:
            dict: The parsed JSON response body.

        """
        url: str = f"{SECRET_MANAGER_API_BASE}/{path}"
        response: requests.Response = self._session.get(url, params=params)
        validate_response(response)

        return response.json()

    def test_connectivity(self) -> bool:
        """Test connectivity to Secret Manager.

        Returns:
            bool: True if connectivity is successful.

        Raises:
            SecretManagerError: If Secret Manager API returns an error.
            ConnectivityError: If the connectivity tests fail.

        """
        self.logger.info("Testing connectivity to Secret Manager.")
        try:
            self._rest_get(
                f"projects/{self.project_id}/secrets",
                params={"pageSize": "1"},
            )
        except SecretManagerError:
            raise
        except Exception as e:
            raise ConnectivityError(str(e)) from e

        self.logger.info("Successfully connected to Secret Manager.")
        return True

    def resolve_latest_enabled_version(self, secret_id: str) -> str:
        """Resolve the latest enabled version for a given secret.

        The ``list_secret_versions`` API does not guarantee any particular
        ordering, so we iterate **all** versions and pick the ENABLED one
        with the highest numeric version ID (version numbers are
        monotonically increasing integers in Secret Manager).

        Args:
            secret_id (str): The ID of the secret.

        Returns:
            str: The version ID of the latest enabled version, or
                DEFAULT_SECRET_VERSION if none are enabled.

        """
        parent = (
            secret_id
            if secret_id.startswith("projects/")
            else f"projects/{self.project_id}/secrets/{secret_id}"
        )
        self.logger.info(f"Resolving latest enabled version for secret {secret_id}.")

        try:
            data: dict = self._rest_get(f"{parent}/versions")
            versions = data.get("versions", [])
        except Exception as e:  # noqa: BLE001
            self.logger.warn(
                f"Failed to list secret versions for '{secret_id}' ({e}). "
                f"Falling back to default version '{DEFAULT_SECRET_VERSION}'."
            )
            return DEFAULT_SECRET_VERSION

        latest_version_number: int = -1
        latest_version_id: str | None = None

        for version in versions:
            if version.get("state") != "ENABLED":
                continue

            version_id = version["name"].split("/")[-1]

            try:
                version_number: int = int(version_id)
            except ValueError:
                continue

            if version_number > latest_version_number:
                latest_version_number = version_number
                latest_version_id = version_id

        if latest_version_id is not None:
            self.logger.info(f"Resolved latest enabled version for '{secret_id}' to '{latest_version_id}'.")
            return latest_version_id

        self.logger.warn(
            f"No enabled versions found for secret '{secret_id}'. "
            f"Falling back to default version '{DEFAULT_SECRET_VERSION}'."
        )
        return DEFAULT_SECRET_VERSION

    def get_secret_value(self, secret_id: str, version_id: str = DEFAULT_SECRET_VERSION) -> str:
        """Access a secret version.

        Args:
            secret_id (str): The ID of the secret.
            version_id (str): The version of the secret. Defaults to "latest".

        Returns:
            str: The secret payload data.

        Raises:
            SecretAccessError: If access to the secret version fails or the payload
                cannot be decoded.

        """
        if secret_id.startswith("projects/"):
            name = f"{secret_id}/versions/{version_id}"
        else:
            name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version_id}"
        self.logger.info(f"Accessing secret '{secret_id}' version '{version_id}'.")

        try:
            data: dict = self._rest_get(f"{name}:access")
            payload = base64.b64decode(data["payload"]["data"])
            self.logger.info(f"Successfully retrieved payload for secret '{secret_id}'.")
        except Exception as e:
            self.logger.exception(f"Failed to access secret '{secret_id}' version '{version_id}'.")
            raise SecretAccessError(str(e)) from e

        try:
            return payload.decode("UTF-8")
        except UnicodeDecodeError as e:
            msg = (
                f"Secret version '{version_id}' contains "
                f"non-UTF-8 data ({len(payload)} bytes). "
                f"This integration only supports "
                f"text-based secrets (UTF-8 encoded)."
            )
            self.logger.exception(f"Failed to decode secret '{secret_id}' version '{version_id}' as UTF-8.")
            raise SecretAccessError(msg) from e
