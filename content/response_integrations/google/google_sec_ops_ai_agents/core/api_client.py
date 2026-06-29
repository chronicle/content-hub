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
from google_sec_ops_ai_agents.core import consts
from google_sec_ops_ai_agents.core import exceptions
import requests
from google_sec_ops_ai_agents.core.data_models import ApiParameters

if TYPE_CHECKING:
    from google.auth.transport.requests import AuthorizedSession
    from TIPCommon.base.interfaces.logger import ScriptLogger
    import TIPCommon.types


MAX_PAGE_SIZE = 1000


class ChronicleInvestigationApiClient:
    """Chronicle Investigation API client."""

    def __init__(
        self,
        api_params: ApiParameters,
        logger: ScriptLogger,
        authenticated_session: AuthorizedSession,
    ) -> None:
        """Initialize a new ChronicleInvestigationApiClient.

        Args:
            api_params: The API parameters.
            logger: The logger.
            authenticated_session: The authenticated session.
        """
        self.api_params = api_params
        self.logger = logger
        self.session = authenticated_session

    def test_connectivity(self) -> None:
        """Test connectivity to the Chronicle API."""
        try:
            self.list_investigations(
                alert_id="siemplify-connectivity-test",
                page_size=1,
            )
        except exceptions.ChronicleInvestigationManagerError as e:
            raise exceptions.ChronicleInvestigationManagerError(
                exceptions.UNABLE_TO_CONNECT_ERROR % e,
            ) from e

    def trigger_investigation(self, alert_id: str) -> TIPCommon.types.SingleJson:
        """Trigger an investigation.

        Args:
            alert_id: The alert ID.

        Returns:
            The investigation data.
        """
        url = f"{self.api_params.api_root}/investigations:trigger"
        payload = {"alertId": alert_id}
        self.logger.info(f"Triggering investigation at: {url}")
        response = self.session.post(url, json=payload)
        validate_response(response, "Failed to trigger investigation")
        return response.json()

    def get_investigation_status(self, investigation_name: str) -> TIPCommon.types.SingleJson:
        """Get the status of an investigation.

        Args:
            investigation_name: The investigation name.

        Returns:
            The investigation status.
        """
        if "/v1alpha" in self.api_params.api_root:
            base_url = self.api_params.api_root.split("/v1alpha")[0] + "/v1alpha"
        else:
            base_url = self.api_params.api_root.rstrip("/")
        url = f"{base_url}/{investigation_name}"
        self.logger.info(f"Checking status for: {url}")
        response = self.session.get(url)
        validate_response(response, "Failed to get investigation status")
        return response.json()

    def list_investigations(
        self,
        alert_id: str,
        page_size: int = MAX_PAGE_SIZE,
    ) -> TIPCommon.types.SingleJson:
        """List investigations.

        Args:
            alert_id: The alert ID.
            page_size: The page size.

        Returns:
            The list of investigations.
        """
        url = f"{self.api_params.api_root}/investigations"
        params = {"pageSize": page_size, "filter": f"alert_id='{alert_id}'"}
        self.logger.info(f"Listing investigations from: {url}")
        response = self.session.get(url, params=params)
        validate_response(response, "Failed to list investigations")
        return response.json().get("investigations", [])


def validate_response(response: requests.Response, error_msg: str = "An error occurred") -> None:
    """Validate a response.

    Args:
        response: The response.
        error_msg: The error message.
    """
    try:
        if response.status_code == consts.API_LIMIT_ERROR:
            raise exceptions.GoogleChronicleAPILimitError(
                exceptions.API_LIMIT_ERROR_MESSAGE,
            )
        response.raise_for_status()
    except requests.HTTPError as error:
        try:
            response.json()
            error_content = (
                response.json().get("error", {}).get("message", response.content)
            )
            error_message = f"{error_msg}: {error} {error_content}"
            raise exceptions.ChronicleInvestigationManagerError(
                error_message,
            ) from error
        except json.JSONDecodeError as e:
            error_message = f"{error_msg}: {error} {response.content}"
            raise exceptions.ChronicleInvestigationManagerError(
                error_message,
            ) from e
