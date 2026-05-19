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

"""ThreatConnect V3 core API client."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from .api_utils import get_full_url, validate_response

if TYPE_CHECKING:
    from logging import Logger

    import requests


@dataclasses.dataclass(slots=True)
class ApiParameters:
    """ThreatConnect V3 API Configuration Parameters."""

    api_root: str
    verify_ssl: bool

    def __post_init__(self) -> None:
        """Normalize API configuration parameters."""
        api_root_clean = self.api_root.rstrip("/")
        if not api_root_clean.endswith("/api"):
            api_root_clean = f"{api_root_clean}/api"
        self.api_root = api_root_clean


class ThreatConnectApiClient:
    """ThreatConnect V3 API Client."""

    def __init__(
        self,
        session: requests.Session,
        parameters: ApiParameters,
        logger: Logger,
    ) -> None:
        self.session = session
        self.api_root = parameters.api_root
        self.verify_ssl = parameters.verify_ssl
        self.logger = logger

    def test_connectivity(self) -> None:
        """Verify connectivity by calling the securityLabels API endpoint."""
        url = get_full_url(self.api_root, "ping")
        self.logger.info(f"Testing connectivity via: {url}")  # noqa: G004

        params = {"resultLimit": 1}
        response = self.session.get(url, params=params, verify=self.verify_ssl)
        validate_response(response, error_msg="Failed to connect to the ThreatConnect server")

    def execute_request(  # noqa: PLR0913
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
        headers: dict | None = None,
        cookies: dict | None = None,
        data: str | None = None,
        verify: bool | None = None,
        timeout: int | None = None,
    ) -> requests.Response:
        """Execute an arbitrary HTTP request.

        Args:
            method (str): HTTP method.
            url (str): Full URL or path.
            params (dict, optional): Query parameters.
            headers (dict, optional): Headers.
            cookies (dict, optional): Cookies.
            data (str, optional): Body payload.
            verify (bool, optional): SSL verification.
            timeout (int, optional): Request timeout.

        Returns:
            requests.Response: The HTTP response.

        """
        if verify is None:
            verify = self.verify_ssl

        response = self.session.request(
            method=method,
            url=url,
            params=params,
            headers=headers,
            cookies=cookies,
            data=data,
            verify=verify,
            timeout=timeout,
        )
        validate_response(response, error_msg=f"Failed to execute {method} request to {url}")
        return response
