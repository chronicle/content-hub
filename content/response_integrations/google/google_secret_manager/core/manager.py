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

import base64
import logging
from typing import TYPE_CHECKING

import google.auth
import google.auth.impersonated_credentials
import requests
import yaml
from google.auth.transport.requests import AuthorizedSession
from google.cloud import secretmanager
from google.oauth2 import service_account

from .constants import (
    DEFAULT_SECRET_VERSION,
)
from .exceptions import (
    ConnectivityError,
    GoogleSecretManagerError,
    InvalidConfigurationError,
    SecretAccessError,
)

if TYPE_CHECKING:
    from google.cloud.secretmanager_v1.services.secret_manager_service import (
        SecretManagerServiceClient,
    )
    from google.cloud.secretmanager_v1.types import AccessSecretVersionResponse

_SECRET_MANAGER_API_BASE: str = "https://secretmanager.googleapis.com/v1"


class GoogleSecretManagerClient:
    """Client for interacting with Google Secret Manager."""

    # OAuth2 scope required to access the Secret Manager API.
    _SECRET_MANAGER_SCOPE: str = "https://www.googleapis.com/auth/cloud-platform"

    def __init__(
        self,
        service_account_json: str | None = None,
        project_id: str | None = None,
        workload_identity_email: str | None = None,
        logger: logging.Logger | None = None,
        *,
        verify_ssl: bool = True,
    ) -> None:
        """Initialize the Google Secret Manager Client.

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
            logger (logging.Logger | None): Optional logger instance for logging.
            verify_ssl (bool): Whether to verify the server's SSL certificate.
                Defaults to True.

        Raises:
            InvalidConfigurationError: If neither Service Account JSON nor Workload Identity
                email is provided, or if Project ID is missing.

        """
        self.logger: logging.Logger | None = logger
        self.verify_ssl: bool = verify_ssl
        self.project_id: str | None
        if workload_identity_email:
            self.credentials: (
                service_account.Credentials | google.auth.impersonated_credentials.Credentials
            ) = self._build_impersonated_credentials(workload_identity_email)
            self.project_id = project_id
        elif service_account_json:
            self.credentials, self.project_id = self._build_sa_credentials(
                service_account_json,
                project_id,
            )
        else:
            msg: str = (
                "Either 'Service Account JSON' or 'Workload Identity Email' "
                "must be provided to authenticate with Google Secret Manager."
            )
            raise InvalidConfigurationError(msg)

        if not self.project_id:
            msg = (
                "Project ID must be provided. When using Service Account JSON, "
                "ensure it contains a 'project_id' field or set the 'Project ID' "
                "parameter explicitly. When using Workload Identity, 'Project ID' "
                "must always be set explicitly as it cannot be inferred."
            )
            raise InvalidConfigurationError(msg)

        self._service_client: SecretManagerServiceClient | None = None
        self._session: AuthorizedSession | None = None

        if self.verify_ssl:
            if self.logger:
                self.logger.info("Initializing Google Secret Manager client with gRPC transport.")
            self._service_client = secretmanager.SecretManagerServiceClient(
                credentials=self.credentials,
            )
        else:
            if self.logger:
                self.logger.info(
                    "Initializing Google Secret Manager client with direct REST transport "
                    "(verify_ssl=False)."
                )
            # gRPC does not support disabling SSL verification, and the
            # library's REST transport has protobuf/proto-plus compatibility
            # issues in some environments.  Fall back to calling the Secret
            # Manager REST API directly via ``AuthorizedSession`` (a
            # ``requests.Session`` subclass) with ``verify=False`` —
            # consistent with every other integration in this repository.
            self._session = AuthorizedSession(self.credentials)
            self._session.verify = False

    @staticmethod
    def _build_sa_credentials(
        service_account_json: str,
        project_id: str | None,
    ) -> tuple[service_account.Credentials, str | None]:
        """Build credentials from a Service Account JSON key string.

        Args:
            service_account_json (str): The JSON key string.
            project_id (str | None): Explicit project ID, or None to infer.

        Returns:
            A (credentials, project_id) tuple.

        Raises:
            InvalidConfigurationError: If the JSON is malformed.

        """
        try:
            info: dict = yaml.safe_load(service_account_json)
            if not isinstance(info, dict):
                msg: str = "Invalid Service Account: JSON is empty or invalid."
                raise InvalidConfigurationError(msg)
        except yaml.YAMLError as e:
            msg = f"Invalid Service Account YAML/JSON provided: {e}"
            raise InvalidConfigurationError(msg) from e

        credentials: service_account.Credentials = (
            service_account.Credentials.from_service_account_info(info)
        )
        resolved_project_id: str | None = project_id or info.get("project_id")

        return credentials, resolved_project_id

    def _build_impersonated_credentials(
        self,
        target_service_account: str,
    ) -> google.auth.impersonated_credentials.Credentials:
        """Build impersonated credentials using Application Default Credentials.

        Args:
            target_service_account (str): The service account email to impersonate.

        Returns:
            Impersonated credentials scoped for Secret Manager.

        Raises:
            InvalidConfigurationError: If ADC cannot be resolved.

        """
        try:
            source_credentials, _ = google.auth.default(scopes=[self._SECRET_MANAGER_SCOPE])
        except google.auth.exceptions.DefaultCredentialsError as e:
            msg: str = (
                f"Could not resolve Application Default Credentials for Workload "
                f"Identity impersonation: {e}"
            )
            raise InvalidConfigurationError(msg) from e

        return google.auth.impersonated_credentials.Credentials(
            source_credentials=source_credentials,
            target_principal=target_service_account,
            target_scopes=[self._SECRET_MANAGER_SCOPE],
        )

    # ------------------------------------------------------------------
    # REST API helpers (used when verify_ssl=False)
    # ------------------------------------------------------------------

    def _rest_get(self, path: str, params: dict | None = None) -> dict:
        """Make an authenticated GET request to the Secret Manager REST API.

        Args:
            path (str): API path relative to the base URL (e.g.
                ``projects/my-proj/secrets``).
            params (dict | None): Optional query parameters.

        Returns:
            dict: The parsed JSON response body.

        Raises:
            requests.HTTPError: If the response status is not 2xx.

        """
        assert self._session is not None  # noqa: S101
        url: str = f"{_SECRET_MANAGER_API_BASE}/{path}"
        response: requests.Response = self._session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def test_connectivity(self) -> bool:
        """Test connectivity to Google Secret Manager.

        Returns:
            bool: True if connectivity is successful.

        Raises:
            GoogleSecretManagerError: If Secret Manager API returns an error.
            ConnectivityError: If the connectivity tests fail.

        """
        if self.logger:
            self.logger.info("Testing connectivity to Google Secret Manager.")
        try:
            if self._service_client:
                parent: str = f"projects/{self.project_id}"
                results = self._service_client.list_secrets(
                    request={"parent": parent, "page_size": 1},
                )
                # Attempt to iterate to trigger the API call
                next(iter(results), None)
            else:
                self._rest_get(
                    f"projects/{self.project_id}/secrets",
                    params={"pageSize": "1"},
                )
        except GoogleSecretManagerError as e:
            if self.logger:
                self.logger.error("Failed to connect to Google Secret Manager: %s", e)
            raise
        except Exception as e:
            msg: str = f"Failed to connect to Google Secret Manager: {e}"
            if self.logger:
                self.logger.error(msg)
            raise ConnectivityError(msg) from e
        else:
            if self.logger:
                self.logger.info("Successfully connected to Google Secret Manager.")
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
        parent: str = f"projects/{self.project_id}/secrets/{secret_id}"
        if self.logger:
            self.logger.info("Resolving latest enabled version for secret '%s'.", secret_id)

        try:
            if self._service_client:
                versions = list(
                    self._service_client.list_secret_versions(request={"parent": parent}),
                )
            else:
                data: dict = self._rest_get(f"{parent}/versions")
                versions = data.get("versions", [])
        except Exception as e:  # noqa: BLE001
            # If we fail to list versions (e.g., permission issue), fall
            # through.  The subsequent get_secret_value call will raise a
            # proper SecretAccessError.
            if self.logger:
                self.logger.warning(
                    "Failed to list secret versions for '%s' (%s). Falling back to default version '%s'.",
                    secret_id,
                    e,
                    DEFAULT_SECRET_VERSION,
                )
            return DEFAULT_SECRET_VERSION

        latest_version_number: int = -1
        latest_version_id: str | None = None

        for version in versions:
            # gRPC client returns protobuf objects with .state enum;
            # REST API returns dicts with "state" string.
            if self._service_client:
                if version.state != secretmanager.SecretVersion.State.ENABLED:
                    continue
                version_id: str = version.name.split("/")[-1]
            else:
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
            if self.logger:
                self.logger.info(
                    "Resolved latest enabled version for '%s' to '%s'.",
                    secret_id,
                    latest_version_id,
                )
            return latest_version_id

        if self.logger:
            self.logger.warning(
                "No enabled versions found for secret '%s'. Falling back to default version '%s'.",
                secret_id,
                DEFAULT_SECRET_VERSION,
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
        name: str = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version_id}"
        if self.logger:
            self.logger.info("Accessing secret '%s' version '%s'.", secret_id, version_id)

        try:
            if self._service_client:
                response: AccessSecretVersionResponse = (
                    self._service_client.access_secret_version(request={"name": name})
                )
                payload: bytes = response.payload.data
            else:
                data: dict = self._rest_get(f"{name}:access")
                # REST API returns payload.data as a base64-encoded string.
                payload = base64.b64decode(data["payload"]["data"])
            if self.logger:
                self.logger.info("Successfully retrieved payload for secret '%s'.", secret_id)
        except Exception as e:
            msg: str = f"Failed to access secret version '{version_id}': {e}"
            if self.logger:
                self.logger.error("Failed to access secret '%s' version '%s': %s", secret_id, version_id, e)
            raise SecretAccessError(msg) from e

        try:
            return payload.decode("UTF-8")
        except UnicodeDecodeError as e:
            msg = (
                f"Secret version '{version_id}' contains "
                f"non-UTF-8 data ({len(payload)} bytes). "
                f"This integration only supports "
                f"text-based secrets (UTF-8 encoded)."
            )
            if self.logger:
                self.logger.error(
                    "Failed to decode secret '%s' version '%s' as UTF-8.",
                    secret_id,
                    version_id,
                )
            raise SecretAccessError(msg) from e

