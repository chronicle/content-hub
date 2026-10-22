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
from typing import Any
from urllib.parse import urlsplit

import google.auth
import google.auth.impersonated_credentials
import google.auth.transport.requests
import google.oauth2.id_token
import google.oauth2.service_account
import requests

from .constants import (
    CLOUD_PLATFORM_SCOPE,
    DEFAULT_TIMEOUT_SECONDS,
    PING_TIMEOUT_SECONDS,
)
from .exceptions import SapErpAuthError


class SapErpManager:
    """Manager for SAP ERP interactions via the SAP RFC Gateway on Cloud Run."""

    def __init__(
        self,
        cloud_run_url: str,
        *,
        service_account_json: str | None = None,
        workload_identity_email: str | None = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        verify_ssl: bool = True,
    ) -> None:
        # Strip accidental whitespace and trailing slash.
        self.cloud_run_url = (cloud_run_url or "").strip().rstrip("/")
        self.service_account_json = (service_account_json or "").strip() or None
        self.workload_identity_email = (workload_identity_email or "").strip() or None
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        # Cloud Run ID tokens must be minted for the service origin
        # (https://<service>.run.app), not for a path under it.
        parsed = urlsplit(self.cloud_run_url)
        self.audience = (
            f"{parsed.scheme}://{parsed.netloc}"
            if parsed.scheme and parsed.netloc
            else self.cloud_run_url
        )
        # Cached for the manager's lifetime without an expiry check. This is
        # safe for short-lived SOAR actions; do not reuse a manager instance in
        # a long-running job or connector where the 1-hour ID token may expire.
        self._id_token: str | None = None

    def _prepare_auth_request(self) -> google.auth.transport.requests.Request:
        """Build an HTTP transport request respecting ``self.verify_ssl``.

        Returns:
            Configured Google Auth transport Request.

        """
        session = requests.Session()
        session.verify = self.verify_ssl
        return google.auth.transport.requests.Request(session=session)

    def _mint_id_token(self) -> str:
        """Mint a Google-signed ID token for ``self.audience``.

        Uses ``service_account_json`` when provided, otherwise impersonates
        ``workload_identity_email`` via Application Default Credentials, and
        falls back to ``google.oauth2.id_token.fetch_id_token`` only when
        neither credential parameter is configured.

        Returns:
            The signed ID token string.

        Raises:
            ValueError: If ``service_account_json`` does not decode to a dict.

        """
        auth_req = self._prepare_auth_request()

        if self.service_account_json:
            info = json.loads(self.service_account_json)
            if not isinstance(info, dict):
                msg = "Invalid Service Account JSON: expected a JSON object."
                raise ValueError(msg)
            sa_creds = (
                google.oauth2.service_account.IDTokenCredentials.from_service_account_info(
                    info,
                    target_audience=self.audience,
                )
            )
            sa_creds.refresh(auth_req)
            return str(sa_creds.token)

        if self.workload_identity_email:
            source_creds, _ = google.auth.default(scopes=[CLOUD_PLATFORM_SCOPE])
            impersonated_creds = google.auth.impersonated_credentials.Credentials(
                source_credentials=source_creds,
                target_principal=self.workload_identity_email,
                target_scopes=[CLOUD_PLATFORM_SCOPE],
            )
            id_creds = google.auth.impersonated_credentials.IDTokenCredentials(
                impersonated_creds,
                target_audience=self.audience,
                include_email=True,
            )
            id_creds.refresh(auth_req)
            return str(id_creds.token)

        return str(google.oauth2.id_token.fetch_id_token(auth_req, self.audience))

    def _get_auth_headers(self) -> dict[str, str]:
        if not self._id_token:
            try:
                self._id_token = self._mint_id_token()
            except Exception as e:
                msg = f"Failed to generate Google Cloud authentication token: {e}"
                raise SapErpAuthError(msg) from e
        return {"Authorization": f"Bearer {self._id_token}"}

    def execute_function(
        self,
        function_id: str,
        sap_instance: str,
        sap_client: str,
        payload: dict[str, Any],
    ) -> requests.Response:
        """Execute an SAP RFC function through the Cloud Run gateway.

        Args:
            function_id: Gateway function ID, e.g. ``USER_LOCK``.
            sap_instance: Name of the SAP instance configured in the gateway.
            sap_client: SAP client number.
            payload: Function-specific parameters.

        Returns:
            The raw HTTP response from the gateway.

        Raises:
            SapErpAuthError: If generating the Google Cloud ID token fails.
            requests.RequestException: If the HTTP request to the gateway fails.

        """  # ruff: ignore[docstring-extraneous-exception]
        envelope_payload = {
            "functionId": function_id,
            "sap_instance": sap_instance,
            "client": sap_client,
            "payload": payload,
        }
        headers = self._get_auth_headers()
        return requests.post(
            self.cloud_run_url,
            json=envelope_payload,
            headers=headers,
            timeout=self.timeout,
            verify=self.verify_ssl,
        )

    def ping(self) -> requests.Response:
        """Send an authenticated GET to the gateway to test connectivity.

        Returns:
            The raw HTTP response from the gateway.

        Raises:
            SapErpAuthError: If generating the Google Cloud ID token fails.
            requests.RequestException: If the HTTP request to the gateway fails.

        """  # ruff: ignore[docstring-extraneous-exception]
        headers = self._get_auth_headers()
        return requests.get(
            self.cloud_run_url,
            headers=headers,
            timeout=PING_TIMEOUT_SECONDS,
            verify=self.verify_ssl,
        )

    @staticmethod
    def extract_error_detail(response: requests.Response) -> str:
        """Extract readable error text from a gateway error response.

        Args:
            response: The gateway HTTP response.

        Returns:
            The ``error`` field of a JSON body if present, otherwise the raw
            body text, otherwise ``HTTP <status>``.

        """
        try:
            body = response.json()
            if isinstance(body, dict) and body.get("error"):
                return str(body["error"])
        except ValueError:
            pass
        return response.text or f"HTTP {response.status_code}"
