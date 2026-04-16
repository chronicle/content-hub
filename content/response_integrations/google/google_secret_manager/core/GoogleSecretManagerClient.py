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
import google.auth
import google.auth.impersonated_credentials
from google.oauth2 import service_account
from google.cloud import secretmanager

from .GoogleSecretManagerExceptions import (
    ConnectivityError,
    GoogleSecretManagerError,
    InvalidConfigurationError,
    SecretAccessError,
)
from .GoogleSecretManagerConstants import (
    DEFAULT_SECRET_VERSION,
)

if TYPE_CHECKING:
    from google.cloud.secretmanager_v1.services.secret_manager_service import (
        SecretManagerServiceClient
    )


class GoogleSecretManagerClient:
    """Client for interacting with Google Secret Manager."""

    # OAuth2 scope required to access the Secret Manager API.
    _SECRET_MANAGER_SCOPE = "https://www.googleapis.com/auth/cloud-platform"

    def __init__(
        self,
        service_account_json: str | None = None,
        project_id: str | None = None,
        workload_identity_email: str | None = None,
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
        """
        if workload_identity_email:
            self.credentials = self._build_impersonated_credentials(workload_identity_email)
            self.project_id = project_id
        elif service_account_json:
            self.credentials, self.project_id = self._build_sa_credentials(
                service_account_json,
                project_id,
            )
        else:
            raise InvalidConfigurationError(
                "Either 'Service Account JSON' or 'Workload Identity Email' "
                "must be provided to authenticate with Google Secret Manager."
            )

        if not self.project_id:
            raise InvalidConfigurationError(
                "Project ID must be provided. When using Service Account JSON, "
                "ensure it contains a 'project_id' field or set the 'Project ID' "
                "parameter explicitly. When using Workload Identity, 'Project ID' "
                "must always be set explicitly as it cannot be inferred."
            )

        self._service_client: SecretManagerServiceClient = (
            secretmanager.SecretManagerServiceClient(credentials=self.credentials)
        )

    def _build_sa_credentials(
        self,
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
            info = json.loads(service_account_json)
        except json.JSONDecodeError as e:
            raise InvalidConfigurationError(
                f"Invalid Service Account JSON provided: {e}"
            ) from e

        credentials = service_account.Credentials.from_service_account_info(info)
        resolved_project_id = project_id or info.get("project_id")

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
            source_credentials, _ = google.auth.default(
                scopes=[self._SECRET_MANAGER_SCOPE]
            )
        except google.auth.exceptions.DefaultCredentialsError as e:
            raise InvalidConfigurationError(
                f"Could not resolve Application Default Credentials for Workload "
                f"Identity impersonation: {e}"
            ) from e

        return google.auth.impersonated_credentials.Credentials(
            source_credentials=source_credentials,
            target_principal=target_service_account,
            target_scopes=[self._SECRET_MANAGER_SCOPE],
        )

    def test_connectivity(self) -> bool:
        """Test connectivity to Google Secret Manager.

        Returns:
            bool: True if connectivity is successful.
        """
        parent = f"projects/{self.project_id}"
        # We just want to check if we can list secrets.
        # page_size=1 is sufficient to verify permissions and connectivity.
        try:
            results = self._service_client.list_secrets(
                request={"parent": parent, "page_size": 1}
            )
            # Attempt to iterate to trigger the API call
            next(iter(results), None)
            return True
        except GoogleSecretManagerError:
            raise
        except Exception as e:
            raise ConnectivityError(
                f"Failed to connect to Google Secret Manager: {e}"
            ) from e

    def resolve_latest_enabled_version(self, secret_id: str) -> str:
        """Resolve the latest enabled version for a given secret.

        Args:
            secret_id (str): The ID of the secret.

        Returns:
            str: The version ID of the latest enabled version, or DEFAULT_SECRET_VERSION if none
                enabled.
        """
        parent = f"projects/{self.project_id}/secrets/{secret_id}"

        try:
            results = self._service_client.list_secret_versions(
                request={"parent": parent}
            )
            for version in results:
                if version.state == secretmanager.SecretVersion.State.ENABLED:
                    return version.name.split("/")[-1]

        except Exception:
            # If we fail to list versions (e.g., permission issue), log or pass.
            # We fallback to DEFAULT_SECRET_VERSION, and the subsequent
            # get_secret_value call will crash with a proper SecretAccessError.
            pass

        return DEFAULT_SECRET_VERSION

    def get_secret_value(self, secret_id: str, version_id: str = DEFAULT_SECRET_VERSION) -> str:
        """Access a secret version.

        Args:
            secret_id (str): The ID of the secret.
            version_id (str): The version of the secret. Defaults to "latest".

        Returns:
            str: The secret payload data.
        """
        name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version_id}"

        try:
            response = self._service_client.access_secret_version(request={"name": name})
        except Exception as e:
            raise SecretAccessError(
                f"Failed to access secret '{secret_id}' version '{version_id}': {e}"
            ) from e

        return response.payload.data.decode("UTF-8")
