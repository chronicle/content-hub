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

"""GCP-native Chronicle API client for the dev-env commands."""

from __future__ import annotations

import base64
import logging
import time
from typing import TYPE_CHECKING, Any

import google.auth
import requests
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
    from collections.abc import Callable
    from pathlib import Path

    from mp.core.custom_types import SingleJson


CLOUD_PLATFORM_SCOPE: str = "https://www.googleapis.com/auth/cloud-platform"
SERVICE_UNAVAILABLE_STATUS: int = 503
DEFAULT_TIMEOUT: int = 60
UPLOAD_TIMEOUT: int = 120


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
            location: Chronicle region (e.g. us, europe).
            instance: Chronicle instance UUID.
            credentials_file: Optional path to a GCP credentials JSON file.
            scopes: OAuth2 scopes to request.

        """
        self.location: str = location.lower()
        self.credentials_file: str | None = credentials_file
        self.scopes: list[str] = scopes or [CLOUD_PLATFORM_SCOPE]
        self.base_url: str = f"https://{self.location}-chronicle.googleapis.com"
        self.instance_name: str = (
            f"projects/{project}/locations/{self.location}/instances/{instance}"
        )
        self.session: requests.Session = self._build_authorized_session()

    def _build_authorized_session(self) -> requests.Session:
        try:
            if self.credentials_file:
                credentials: Any
                credentials, _ = google.auth.load_credentials_from_file(
                    self.credentials_file,
                    scopes=self.scopes,
                )
            else:
                credentials, _ = google.auth.default(scopes=self.scopes)
        except Exception as exc:
            logger.exception("Failed to resolve GCP credentials.")
            raise typer.Exit(1) from exc

        return AuthorizedSession(credentials)

    def _endpoint(
        self,
        suffix: str,
        *,
        version: str = "v1",
        upload: bool = False,
    ) -> str:
        prefix: str = "/upload" if upload else ""
        return f"{self.base_url}{prefix}/{version}/{self.instance_name}/{suffix}"

    def login(self) -> None:
        """Verify connectivity and credentials with an authenticated request."""
        url: str = self._endpoint("integrations")
        resp: requests.Response = self.session.get(
            url, params={"pageSize": 1}, timeout=DEFAULT_TIMEOUT
        )
        resp.raise_for_status()

    def list_integrations(self, *, max_pages: int = 100) -> list[Integration]:
        """List all integrations installed in the instance.

        Args:
            max_pages: Maximum number of pages to retrieve to prevent infinite loops.

        Returns:
            The list of Integration resources.

        """
        url: str = self._endpoint("integrations")
        params: SingleJson = {"pageSize": 1000}
        results: list[Integration] = []

        for _ in range(max_pages):
            resp: requests.Response = self.session.get(
                url, params=params, timeout=DEFAULT_TIMEOUT
            )
            resp.raise_for_status()
            page: ListIntegrationsResponse = ListIntegrationsResponse.model_validate(
                resp.json()
            )
            results.extend(page.integrations)
            if not page.next_page_token:
                return results
            params = {**params, "pageToken": page.next_page_token}

        logger.warning(
            "Reached maximum pagination limit (%d pages) while listing integrations.",
            max_pages,
        )
        return results

    def _resolve_integration_name(self, integration: str) -> str:
        target: str = integration.strip().lower()
        for item in self.list_integrations():
            if item.name and _matches_integration(item, target):
                return item.name

        logger.error(
            "Integration '%s' not found in instance %s.",
            integration,
            self.instance_name,
        )
        raise typer.Exit(1)

    def download_integration(self, integration_name: str) -> bytes:
        """Export an integration package and return raw ZIP bytes.

        Args:
            integration_name: The integration name or identifier to export.

        Returns:
            The integration package as raw ZIP bytes.

        """
        name: str = self._resolve_integration_name(integration_name)
        url: str = f"{self.base_url}/v1/{name}:export"
        resp: requests.Response = self.session.get(
            url, params={"alt": "media"}, timeout=DEFAULT_TIMEOUT
        )
        resp.raise_for_status()
        return _extract_zip_bytes(resp)

    def get_integration_details(
        self,
        zip_path: Path,
        *,
        is_staging: bool = False,
    ) -> SingleJson:
        """Parse an integration package and return metadata without importing.

        Args:
            zip_path: Path to the integration package ZIP.
            is_staging: Whether to inspect against staging.

        Returns:
            The parsed integration details from the backend.

        """
        url: str = self._endpoint(
            "integrations:extractIntegrationDetails",
            version="v1alpha",
            upload=True,
        )
        details: SingleJson = self._media_upload(
            url,
            zip_path,
            params={"staging": is_staging},
        )
        if isinstance(details, dict):
            identifier: Any = (
                details.get("integrationIdentifier") or details.get("identifier")
            )
            details.setdefault("identifier", identifier)
        return details

    def upload_integration(
        self,
        zip_path: Path,
        integration_id: str,
        *,
        is_staging: bool = False,
    ) -> SingleJson:
        """Import an integration package into the instance.

        Args:
            zip_path: Path to the integration package ZIP.
            integration_id: The integration identifier.
            is_staging: Whether to import in staging mode.

        Returns:
            The backend import response.

        Raises:
            requests.exceptions.HTTPError: If the upload fails and cannot be verified.

        """
        logger.debug(
            "Importing integration %s (staging=%s)",
            integration_id,
            is_staging,
        )
        url: str = self._endpoint(
            "integrations:import",
            version="v1alpha",
            upload=True,
        )
        try:
            return self._media_upload(url, zip_path, params={"staging": is_staging})
        except requests.exceptions.HTTPError as err:
            if err.response is not None and err.response.status_code == SERVICE_UNAVAILABLE_STATUS:
                logger.warning(
                    "Upload gateway timed out (503). Verifying if %s is installed on Chronicle...",
                    integration_id,
                )
                if self._wait_for_integration_installed(
                    integration_id, is_staging=is_staging
                ):
                    logger.info("Verified %s is successfully installed.", integration_id)
                    return {"integration": integration_id, "status": "installed"}
            raise

    def upload_playbook(self, zip_path: Path) -> SingleJson:
        """Import playbook definitions from a ZIP into the instance.

        Args:
            zip_path: Path to the playbook definitions ZIP.

        Returns:
            The backend import response.

        Raises:
            requests.exceptions.HTTPError: If the upload fails and cannot be verified.

        """
        url: str = self._endpoint(
            "legacyPlaybooks:legacyImportDefinitions",
            version="v1alpha",
            upload=True,
        )
        try:
            return self._media_upload(url, zip_path)
        except requests.exceptions.HTTPError as err:
            if err.response is not None and err.response.status_code == SERVICE_UNAVAILABLE_STATUS:
                name: str = zip_path.stem
                logger.warning(
                    "Upload gateway timed out (503). Verifying if playbook %s is installed on Chronicle...",
                    name,
                )
                if self._wait_for_playbook_installed(name):
                    logger.info("Verified playbook %s is successfully installed.", name)
                    return {"playbook": name, "status": "installed"}
            raise

    def _wait_for_integration_installed(
        self,
        integration_id: str,
        *,
        is_staging: bool = False,
    ) -> bool:
        target: str = integration_id.strip().lower()

        def _check() -> bool:
            return any(
                _matches_integration(item, target, is_staging=is_staging)
                for item in self.list_integrations()
            )

        return _poll_until(_check)

    def _wait_for_playbook_installed(
        self,
        playbook_name: str,
    ) -> bool:
        target: str = playbook_name.strip().lower()

        def _check() -> bool:
            return any(
                target in {
                    (card.get("name") or "").lower(),
                    (card.get("identifier") or "").lower(),
                }
                for card in self.list_playbooks()
            )

        return _poll_until(_check)

    def list_playbooks(self) -> list[SingleJson]:
        """List installed playbook and workflow menu cards.

        Returns:
            A list of dicts with name and identifier for each playbook.

        """
        url: str = self._endpoint(
            "legacyPlaybooks:legacyGetWorkflowMenuCardsWithEnvFilter",
            version="v1alpha",
        )
        payload: dict[str, list[str]] = {"legacyPayload": ["REGULAR", "NESTED"]}
        resp: requests.Response = self.session.post(
            url, json=payload, timeout=DEFAULT_TIMEOUT
        )
        resp.raise_for_status()
        cards: WorkflowMenuCardsResponse = (
            WorkflowMenuCardsResponse.model_validate(resp.json())
        )
        return [
            {"name": card.name, "identifier": card.identifier}
            for card in cards.payload
            if card.name and card.identifier
        ]

    def download_playbook(self, playbook_identifier: str) -> SingleJson:
        """Export a playbook definition by identifier.

        Args:
            playbook_identifier: The identifier of the playbook to export.

        Returns:
            A dict with a base64-encoded 'blob' of the exported definitions ZIP.

        """
        url: str = self._endpoint(
            "legacyPlaybooks:legacyExportDefinitions",
            version="v1alpha",
        )
        params: dict[str, str] = {
            "identifiers": playbook_identifier,
            "alt": "media",
        }
        resp: requests.Response = self.session.get(
            url, params=params, timeout=DEFAULT_TIMEOUT
        )
        resp.raise_for_status()
        encoded_blob: str = base64.b64encode(_extract_zip_bytes(resp)).decode()
        return {"blob": encoded_blob}

    def _media_upload(
        self,
        url: str,
        zip_path: Path,
        params: SingleJson | None = None,
    ) -> SingleJson:
        files: dict[str, tuple[str, bytes, str]] = {
            "file": (zip_path.name, zip_path.read_bytes(), "application/zip")
        }
        query: dict[str, str] = {
            key: str(value).lower() if isinstance(value, bool) else str(value)
            for key, value in (params or {}).items()
        }
        resp: requests.Response = self.session.post(
            url,
            params=query or None,
            files=files,
            timeout=UPLOAD_TIMEOUT,
        )
        resp.raise_for_status()
        data: SingleJson = resp.json()
        return data


def _matches_integration(
    item: Integration,
    target: str,
    *,
    is_staging: bool | None = None,
) -> bool:
    """Check if an integration matches the target name, identifier, or production identifier.

    Args:
        item: The Integration model to inspect.
        target: The target name or identifier in lowercase.
        is_staging: If specified, filter by whether the integration is staged.

    Returns:
        True if the integration matches the target, False otherwise.

    """
    if not item.name:
        return False
    if is_staging is not None and bool(item.staging) != is_staging:
        return False
    candidates: set[str] = {
        (item.display_name or "").lower(),
        (item.identifier or "").lower(),
        (item.production_identifier or "").lower(),
        item.name.rsplit("/", 1)[-1].lower(),
    }
    return target in candidates


def _poll_until(
    predicate: Callable[[], bool],
    *,
    max_attempts: int = 5,
    delay_seconds: float = 2.0,
) -> bool:
    """Poll a predicate function at intervals until it returns True or attempts are exhausted.

    Args:
        predicate: Zero-argument function returning True on success.
        max_attempts: Maximum number of polling attempts before giving up.
        delay_seconds: Interval in seconds between attempts.

    Returns:
        True if predicate returned True within max_attempts, False otherwise.

    """
    for attempt in range(max_attempts):
        time.sleep(delay_seconds)
        try:
            if predicate():
                return True
        except requests.RequestException:
            logger.debug("Polling attempt %d failed with request exception", attempt)
    return False


def _extract_zip_bytes(resp: requests.Response) -> bytes:
    """Extract raw ZIP bytes from an HTTP response or inline base64 JSON envelope.

    Args:
        resp: The HTTP response from the Chronicle export API.

    Returns:
        The decoded raw ZIP package bytes.

    Raises:
        typer.Exit: If the export response contains no inline media content.

    """
    content_type: str = resp.headers.get("Content-Type", "").lower()
    if "application/json" not in content_type:
        return resp.content

    envelope: ExportResponse = ExportResponse.model_validate(resp.json())
    if envelope.media and envelope.media.inline is not None:
        return envelope.media.inline

    logger.error("Export returned no inline media content.")
    raise typer.Exit(1)
