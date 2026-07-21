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

"""GCP-native Chronicle API client for the dev-env commands.

Authenticates with Google Application Default Credentials (ADC) and talks to the Chronicle
API (``{location}-chronicle.googleapis.com``). Implements integration listing and export
(pull). Integration import (push) and playbook operations are not implemented yet.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import google.auth
import typer
from google.auth.transport.requests import AuthorizedSession

from mp.dev_env.chronicle_models import ExportResponse, Integration, ListIntegrationsResponse
from mp.dev_env.interfaces import DevEnvClient

logger: logging.Logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from pathlib import Path

    import requests


CLOUD_PLATFORM_SCOPE: str = "https://www.googleapis.com/auth/cloud-platform"


class ChronicleClient(DevEnvClient):
    """Talks to the Chronicle API using GCP Application Default Credentials."""

    def __init__(
        self,
        project: str,
        location: str,
        instance: str,
        credentials_file: str | None = None,
        scopes: list[str] | None = None,
    ) -> None:
        """Initialize the Chronicle client.

        Args:
            project: GCP project ID that owns the Chronicle instance.
            location: Chronicle region (e.g. ``us``, ``europe``); drives the API hostname.
            instance: Chronicle instance UUID (the SecOps ``customer_id``).
            credentials_file: Optional path to a GCP credentials JSON file (service account
                or external account). When ``None``, Application Default Credentials are
                resolved automatically via ``google.auth.default``.
            scopes: OAuth2 scopes to request. Defaults to the ``cloud-platform`` scope.

        """
        self.project: str = project
        self.location: str = location.lower()
        self.instance: str = instance
        self.credentials_file: str | None = credentials_file
        self.scopes: list[str] = scopes or [CLOUD_PLATFORM_SCOPE]
        self.base_url: str = f"https://{self.location}-chronicle.googleapis.com"
        self.instance_name: str = f"projects/{project}/locations/{self.location}/instances/{instance}"
        self.session: requests.Session = self._build_authorized_session()

    def _build_authorized_session(self) -> requests.Session:
        """Resolve GCP credentials and wrap them in an auto-refreshing session.

        Returns:
            An ``AuthorizedSession`` that attaches (and refreshes) an OAuth2 Bearer token
            on every request.

        Raises:
            typer.Exit: If credentials cannot be resolved.

        """
        try:
            if self.credentials_file:
                credentials, _ = google.auth.load_credentials_from_file(self.credentials_file, scopes=self.scopes)
            else:
                credentials, _ = google.auth.default(scopes=self.scopes)
        except Exception as exc:
            logger.exception(
                "Failed to resolve GCP credentials. Run 'gcloud auth application-default login' "
                "or pass --credentials-file."
            )
            raise typer.Exit(1) from exc

        return AuthorizedSession(credentials)

    def login(self) -> None:
        """Verify connectivity and credentials with a cheap authenticated request."""
        url: str = f"{self.base_url}/v1/{self.instance_name}/integrations"
        resp = self.session.get(url, params={"pageSize": 1})
        resp.raise_for_status()

    def list_integrations(self) -> list[Integration]:
        """List all integrations installed in the instance (handles pagination).

        Returns:
            The list of ``Integration`` resources.

        """
        url: str = f"{self.base_url}/v1/{self.instance_name}/integrations"
        params: dict[str, Any] = {"pageSize": 1000}
        results: list[Integration] = []

        while True:
            resp = self.session.get(url, params=params)
            resp.raise_for_status()
            page: ListIntegrationsResponse = ListIntegrationsResponse.model_validate(resp.json())
            results.extend(page.integrations)
            if not page.next_page_token:
                break
            params = {**params, "pageToken": page.next_page_token}

        return results

    def _resolve_integration_name(self, integration: str) -> str:
        """Resolve a user-supplied integration name to its full Chronicle resource name.

        Matches (case-insensitively) against the ``displayName``, ``identifier``, or the
        trailing segment of the resource ``name``.

        Args:
            integration: The integration name/identifier as the user refers to it.

        Returns:
            The full resource name ``projects/.../instances/.../integrations/{id}``.

        Raises:
            typer.Exit: If no matching integration is found.

        """
        target: str = integration.strip().lower()
        for item in self.list_integrations():
            if not item.name:
                continue
            candidates: set[str] = {
                (item.display_name or "").lower(),
                (item.identifier or "").lower(),
                item.name.rsplit("/", 1)[-1].lower(),
            }
            if target in candidates:
                return item.name

        logger.error("Integration '%s' not found in instance %s.", integration, self.instance_name)
        raise typer.Exit(1)

    def download_integration(self, integration_name: str) -> bytes:
        """Export an integration package and return the raw ZIP bytes.

        Args:
            integration_name: The integration name/identifier to export.

        Returns:
            The integration package as raw ZIP bytes.

        """
        name: str = self._resolve_integration_name(integration_name)
        url: str = f"{self.base_url}/v1/{name}:export"
        resp = self.session.get(url, params={"alt": "media"})
        resp.raise_for_status()
        return _extract_zip_bytes(resp)

    def get_integration_details(self, zip_path: Path, *, is_staging: bool = False) -> dict[str, Any]:
        """Inspect an integration package via the Chronicle API (not implemented yet)."""
        raise NotImplementedError

    def upload_integration(self, zip_path: Path, integration_id: str, *, is_staging: bool = False) -> dict[str, Any]:
        """Push an integration via the Chronicle API (not implemented yet)."""
        raise NotImplementedError

    def upload_playbook(self, zip_path: Path) -> dict[str, Any]:
        """Push a playbook via the Chronicle API (not implemented yet)."""
        raise NotImplementedError

    def list_playbooks(self) -> list[dict[str, Any]]:
        """List playbooks via the Chronicle API (not implemented yet)."""
        raise NotImplementedError

    def download_playbook(self, playbook_identifier: str) -> dict[str, Any]:
        """Pull a playbook via the Chronicle API (not implemented yet)."""
        raise NotImplementedError


def _extract_zip_bytes(resp: requests.Response) -> bytes:
    """Normalize an integration ``:export`` response into raw ZIP bytes.

    ``:export?alt=media`` normally streams the raw ZIP (possibly via a redirect to a
    ``/download`` URL). Some deployments may instead return a JSON envelope carrying the
    bytes inline as base64. Both are handled.

    Args:
        resp: The HTTP response from the export request.

    Returns:
        The ZIP payload as raw bytes.

    Raises:
        typer.Exit: If a JSON envelope carries no inline media content.

    """
    content_type: str = resp.headers.get("Content-Type", "").lower()
    if "application/json" not in content_type:
        return resp.content

    envelope: ExportResponse = ExportResponse.model_validate(resp.json())
    if envelope.media and envelope.media.inline:
        return envelope.media.inline

    logger.error("Integration export returned no inline media content; cannot extract the package ZIP.")
    raise typer.Exit(1)
