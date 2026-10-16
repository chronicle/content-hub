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

from typing import Any, Dict, Optional
from urllib.parse import urlsplit
import google.auth.transport.requests
import google.oauth2.id_token
import requests

DEFAULT_TIMEOUT_SECONDS = 60
PING_TIMEOUT_SECONDS = 30


class SapErpAuthError(Exception):
    """Raised when generating a Google Cloud ID token fails."""


class SapErpManager:
    """Manager for SAP ERP interactions."""

    def __init__(self, cloud_run_url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS):
        # Strip accidental whitespace and trailing slash
        self.cloud_run_url = (cloud_run_url or "").strip().rstrip("/")
        self.timeout = timeout

        # Extract root origin (https://<service>.run.app) for Cloud Run OIDC token audience
        parsed = urlsplit(self.cloud_run_url)
        self.audience = (
            f"{parsed.scheme}://{parsed.netloc}"
            if parsed.scheme and parsed.netloc
            else self.cloud_run_url
        )
        self._id_token: Optional[str] = None

    def _get_auth_headers(self) -> Dict[str, str]:
        if not self._id_token:
            try:
                auth_req = google.auth.transport.requests.Request()
                self._id_token = google.oauth2.id_token.fetch_id_token(
                    auth_req, self.audience
                )
            except Exception as e:
                raise SapErpAuthError(
                    f"Failed to generate Google Cloud authentication token: {e}"
                ) from e
        return {"Authorization": f"Bearer {self._id_token}"}

    def execute_function(
        self,
        function_id: str,
        sap_instance: str,
        sap_client: str,
        payload: Dict[str, Any],
    ) -> requests.Response:
        """Executes an SAP function via the Cloud Run proxy."""
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
        )

    def ping(self) -> requests.Response:
        """Pings the Cloud Run proxy to test connectivity."""
        headers = self._get_auth_headers()
        return requests.get(
            self.cloud_run_url,
            headers=headers,
            timeout=PING_TIMEOUT_SECONDS,
        )

    @staticmethod
    def extract_error_detail(response: requests.Response) -> str:
        """Extracts structured error text from a GatewayHttpHandler error response."""
        try:
            body = response.json()
            if isinstance(body, dict) and body.get("error"):
                return str(body["error"])
        except ValueError:
            pass
        return response.text or f"HTTP {response.status_code}"