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
API (``{location}-chronicle.googleapis.com``), covering integration and playbook listing,
export, and import.
"""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING, Any

import google.auth
import typer
from google.auth.transport.requests import AuthorizedSession

from mp.dev_env.chronicle_models import (
    ExportResponse,
    Integration,
    ListIntegrationsResponse,
    WorkflowMenuCardsResponse,
)
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
            credentials_file: Optional path to a GCP credentials JSON file (e.g. for CI).
                When ``None``, ADC is resolved via ``google.auth.default``.
            scopes: OAuth2 scopes to request. Defaults to the ``cloud-platform`` scope.

        """
        self.location: str = location.lower()
        self.credentials_file: str | None = credentials_file
        self.scopes: list[str] = scopes or [CLOUD_PLATFORM_SCOPE]
        self.base_url: str = f"https://{self.location}-chronicle.googleapis.com"
        self.instance_name: str = f"projects/{project}/locations/{self.location}/instances/{instance}"
        self.session: requests.Session = self._build_authorized_session()

    def _build_authorized_session(self) -> requests.Session:
        """Resolve GCP credentials and wrap them in an auto-refreshing session.

        Returns:
            An ``AuthorizedSession`` that attaches and refreshes an OAuth2 Bearer token.

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

    def _endpoint(self, suffix: str, *, version: str = "v1", upload: bool = False) -> str:
        """Build an instance-scoped Chronicle API URL.

        Args:
            suffix: Path after the instance name (e.g. ``integrations:import``).
            version: API version segment (``v1`` or ``v1alpha``).
            upload: Whether to target the media-upload path.

        Returns:
            The full request URL.

        """
        prefix: str = "/upload" if upload else ""
        return f"{self.base_url}{prefix}/{version}/{self.instance_name}/{suffix}"

    def login(self) -> None:
        """Verify connectivity and credentials with a cheap authenticated request."""
        resp = self.session.get(self._endpoint("integrations"), params={"pageSize": 1})
        resp.raise_for_status()

    def list_integrations(self) -> list[Integration]:
        """List all integrations installed in the instance, following pagination.

        Reference: https://docs.cloud.google.com/chronicle/docs/reference/rest/v1/projects.locations.instances.integrations/list

        Returns:
            The list of ``Integration`` resources.

        """
        url: str = self._endpoint("integrations")
        params: dict[str, Any] = {"pageSize": 1000}
        results: list[Integration] = []

        while True:
            resp = self.session.get(url, params=params)
            resp.raise_for_status()
            page = ListIntegrationsResponse.model_validate(resp.json())
            results.extend(page.integrations)
            if not page.next_page_token:
                return results
            params = {**params, "pageToken": page.next_page_token}

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
            if item.name and target in {
                (item.display_name or "").lower(),
                (item.identifier or "").lower(),
                item.name.rsplit("/", 1)[-1].lower(),
            }:
                return item.name

        logger.error("Integration '%s' not found in instance %s.", integration, self.instance_name)
        raise typer.Exit(1)

    def download_integration(self, integration_name: str) -> bytes:
        """Export an integration package and return the raw ZIP bytes.

        Reference: https://docs.cloud.google.com/chronicle/docs/reference/rest/v1/projects.locations.instances.integrations/download

        Args:
            integration_name: The integration name/identifier to export.

        Returns:
            The integration package as raw ZIP bytes.

        """
        name: str = self._resolve_integration_name(integration_name)
        resp = self.session.get(f"{self.base_url}/v1/{name}:export", params={"alt": "media"})
        resp.raise_for_status()
        return _extract_zip_bytes(resp)

    def get_integration_details(self, zip_path: Path, *, is_staging: bool = False) -> dict[str, Any]:
        """Parse an integration package and return its items/metadata without importing.

        Reference: https://docs.cloud.google.com/chronicle/docs/reference/rest/v1alpha/projects.locations.instances.integrations/upload

        Args:
            zip_path: Path to the integration package ZIP.
            is_staging: Whether to compare against staging.

        Returns:
            The parsed integration details returned by the backend.

        """
        url: str = self._endpoint("integrations:extractIntegrationDetails", version="v1alpha", upload=True)
        return self._media_upload(url, zip_path, params={"staging": is_staging})

    def upload_integration(self, zip_path: Path, integration_id: str, *, is_staging: bool = False) -> dict[str, Any]:
        """Import an integration package into the instance.

        Reference: https://docs.cloud.google.com/chronicle/docs/reference/rest/v1alpha/projects.locations.instances.integrations/import

        Args:
            zip_path: Path to the integration package ZIP.
            integration_id: The integration identifier (the package itself is authoritative).
            is_staging: Whether to import in staging mode.

        Returns:
            The backend response (imported integration id/version and failed dependencies).

        """
        logger.debug("Importing integration %s (staging=%s)", integration_id, is_staging)
        url: str = self._endpoint("integrations:import", version="v1alpha", upload=True)
        return self._media_upload(url, zip_path, params={"staging": is_staging})

    def upload_playbook(self, zip_path: Path) -> dict[str, Any]:
        """Import playbook definitions from a ZIP into the instance.

        Reference: https://docs.cloud.google.com/chronicle/docs/reference/rest/v1alpha/projects.locations.instances.legacyPlaybooks/exportWorkflowWithBlocksByIdentifier

        Args:
            zip_path: Path to the playbook definitions ZIP.

        Returns:
            The backend response (imported workflow identifiers).

        """
        url: str = self._endpoint("legacyPlaybooks:legacyImportDefinitions", version="v1alpha", upload=True)
        return self._media_upload(url, zip_path)

    def list_playbooks(self) -> list[dict[str, Any]]:
        """List installed playbook/workflow menu cards.

        Reference: https://docs.cloud.google.com/chronicle/docs/reference/rest/v1alpha/projects.locations.instances.legacyPlaybooks/legacyGetWorkflowMenuCardsWithEnvFilter

        Returns:
            A list of dicts with 'name' and 'identifier' for each playbook.

        """
        url: str = self._endpoint("legacyPlaybooks:legacyGetWorkflowMenuCardsWithEnvFilter", version="v1alpha")
        resp = self.session.post(url, json={"legacyPayload": ["REGULAR", "NESTED"]})
        resp.raise_for_status()
        cards = WorkflowMenuCardsResponse.model_validate(resp.json())
        return [
            {"name": card.name, "identifier": card.identifier}
            for card in cards.payload
            if card.name and card.identifier
        ]

    def download_playbook(self, playbook_identifier: str) -> dict[str, Any]:
        """Export a playbook definition by identifier.

        Reference: https://docs.cloud.google.com/chronicle/docs/reference/rest/v1alpha/projects.locations.instances.legacyPlaybooks/download

        Args:
            playbook_identifier: The identifier of the playbook to export.

        Returns:
            A dict with a base64-encoded 'blob' of the exported definitions ZIP.

        """
        url: str = self._endpoint("legacyPlaybooks:legacyExportDefinitions", version="v1alpha")
        resp = self.session.get(url, params={"identifiers": playbook_identifier, "alt": "media"})
        resp.raise_for_status()
        return {"blob": base64.b64encode(_extract_zip_bytes(resp)).decode()}

    def _media_upload(self, url: str, zip_path: Path, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Upload a ZIP as a multipart/form-data ``file`` part and return the JSON response.

        Non-media scalar fields (e.g. ``{"staging": False}``) are sent as query parameters,
        booleans lowercased to ``true``/``false``.

        Args:
            url: The upload endpoint URL.
            zip_path: Path to the ZIP to upload.
            params: Optional non-media scalar fields, sent as query parameters.

        Returns:
            The parsed JSON response body.

        """
        files = {"file": (zip_path.name, zip_path.read_bytes(), "application/zip")}
        query: dict[str, str] = {
            key: str(value).lower() if isinstance(value, bool) else str(value) for key, value in (params or {}).items()
        }
        resp = self.session.post(url, params=query or None, files=files)
        resp.raise_for_status()
        return resp.json()


def _extract_zip_bytes(resp: requests.Response) -> bytes:
    """Return the ZIP bytes from an export response.

    The export streams the raw ZIP (typically via a redirect to a ``/download`` URL); a
    JSON ``{"media": {"inline": ...}}`` envelope with base64 content is also handled.

    Args:
        resp: The HTTP response from the export request.

    Returns:
        The ZIP payload as raw bytes.

    Raises:
        typer.Exit: If a JSON envelope carries no inline media content.

    """
    if "application/json" not in resp.headers.get("Content-Type", "").lower():
        return resp.content

    envelope: ExportResponse = ExportResponse.model_validate(resp.json())
    if envelope.media and envelope.media.inline is not None:
        return envelope.media.inline

    logger.error("Export returned no inline media content; cannot extract the package ZIP.")
    raise typer.Exit(1)
