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

from typing import Any
from urllib.parse import urlsplit

import google.auth.transport.requests
import google.oauth2.id_token
import requests

DEFAULT_TIMEOUT_SECONDS = 60
PING_TIMEOUT_SECONDS = 30


class SapErpAuthError(Exception):
    """Raised when generating a Google Cloud ID token fails."""


class SapErpManager:
    """Manager for SAP ERP interactions via the SAP RFC Gateway on Cloud Run."""

    def __init__(
        self,
        cloud_run_url: str,
        *,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        verify_ssl: bool = True,
    ) -> None:
        # Strip accidental whitespace and trailing slash.
        self.cloud_run_url = (cloud_run_url or "").strip().rstrip("/")
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
        self._id_token: str | None = None

    def _get_auth_headers(self) -> dict[str, str]:
        if not self._id_token:
            try:
                auth_req = google.auth.transport.requests.Request()
                self._id_token = google.oauth2.id_token.fetch_id_token(
                    auth_req, self.audience
                )
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


        """
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


        """
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
