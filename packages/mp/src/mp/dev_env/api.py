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

import base64
from typing import TYPE_CHECKING, Any

import requests
import rich
import typer

if TYPE_CHECKING:
    from pathlib import Path


class BackendAPI:
    """Handles backend API operations for the dev environment."""

    def __init__(
        self,
        api_root: str,
        username: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
    ) -> None:
        """Initialize the BackendAPI with credentials and API root.

        Args:
            api_root: The API root URL.
            username: The username for authentication (required if using username/password auth).
            password: The password for authentication (required if using username/password auth).
            api_key: The API key for authentication (required if using API key auth).

        Raises:
            typer.Exit: Validations error.

        """
        self.api_root = api_root.rstrip("/")
        self.username = username
        self.password = password
        self.api_key = api_key
        self.session = requests.Session()
        self.token = None

        if api_key is not None:
            if username is not None or password is not None:
                rich.print("[red]Cannot use both API key and username/password[/red]")
                raise typer.Exit(1)

        elif username is None or password is None:
            rich.print("[red]You must provide username and password or api key[/red]")
            raise typer.Exit(1)

    def login(self) -> None:
        """Authenticate and store the session token or API key header."""
        if self.api_key is not None:
            self.session.headers.update({"AppKey": self.api_key})
            verify_url = f"{self.api_root}/api/external/v1/settings/GetSourceRepositorySettings"
            resp = self.session.get(verify_url)
            resp.raise_for_status()
        else:
            login_url = f"{self.api_root}/api/external/v1/accounts/Login?format=camel"
            login_payload = {"userName": self.username, "password": self.password}
            resp = self.session.post(login_url, json=login_payload)
            resp.raise_for_status()
            self.token = resp.json()["token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def get_integration_details(
        self,
        zip_path: Path,
        *,
        is_staging: bool = False,
    ) -> dict[str, Any]:
        """Get integration details from a zipped package.

        Args:
            zip_path: Path to the zipped integration package.
            is_staging: Push to staging or not.

        Returns:
            dict: The integration details as returned by the backend.

        """
        details_url = f"{self.api_root}/api/external/v1/ide/GetPackageDetails?format=camel"
        if is_staging:
            details_url += "&isStaging=true"

        data = base64.b64encode(zip_path.read_bytes()).decode()
        details_payload = {"data": data}
        resp = self.session.post(details_url, json=details_payload)
        resp.raise_for_status()
        return resp.json()

    def upload_integration(
        self,
        zip_path: Path,
        integration_id: str,
        *,
        is_staging: bool = False,
    ) -> dict[str, Any]:
        """Upload a zipped integration package to the backend.

        Args:
            zip_path: Path to the zipped integration package.
            integration_id: The identifier of the integration.
            is_staging: Push to staging or not.

        Returns:
            dict: The backend response after uploading the integration.

        """
        upload_url = f"{self.api_root}/api/external/v1/ide/ImportPackage?format=camel"
        if is_staging:
            upload_url += "&isStaging=true"

        data = base64.b64encode(zip_path.read_bytes()).decode()
        upload_payload = {
            "data": data,
            "integrationIdentifier": integration_id,
            "isCustom": False,
        }
        resp = self.session.post(upload_url, json=upload_payload)
        resp.raise_for_status()
        return resp.json()
