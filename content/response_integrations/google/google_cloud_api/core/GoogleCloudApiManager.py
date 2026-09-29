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

import requests
from google.auth.transport.requests import AuthorizedSession

from TIPCommon.base.utils import NewLineLogger
from google_cloud_api.core import GoogleCloudApiConstants
from google_cloud_api.core.GoogleCloudApiDatamodels import IntegrationPlaceholders
from google_cloud_api.core import GoogleCloudApiUtils as Utils


class ApiManager:
    def __init__(
        self,
        session: AuthorizedSession,
        placeholders: IntegrationPlaceholders,
        logger: NewLineLogger,
    ) -> None:
        """Manager for handling API interactions

        This class provides functionality for managing API interactions

        Args:
            session (AuthorizedSession): Session object with corresponding headers
            logger (NewLineLogger): The logger object
        """
        self.session = session
        self.placeholders = placeholders
        self.logger = logger

    def test_connectivity(self, test_url: str) -> None:
        """Test connectivity.

        Args:
            test_url (str): URL to test connectivity with
        """
        response = self.execute_http_request(
            method="GET",
            url_path=test_url
        )
        Utils.validate_response(response)

    def execute_http_request(
        self,
        method: str,
        url_path: str,
        params: dict = None,
        headers: dict = None,
        cookies: dict = None,
        body_payload: str = None,
        follow_redirects: bool = True,
        timeout: int = GoogleCloudApiConstants.DEFAULT_REQUEST_TIMEOUT
    ) -> requests.Response:
        """Execute http request.

        Args:
            method (str): http method for request
            url_path (str): url path to send request to
            params (dict): request params
            headers (dict): request headers
            cookies (dict): request cookies
            body_payload (str): request body payload
            follow_redirects (bool): specifies if redirects should be followed
            timeout (int): request timeout

        Returns:
            requests.Response: request response
        """
        if headers and headers.get("Cookie") and cookies:
            del headers["Cookie"]

        args = {
            "method": method,
            "url": self.placeholders.apply_placeholders(url_path),
            "params": self.placeholders.apply_placeholders(params),
            "headers": self.placeholders.apply_placeholders(headers),
            "cookies": cookies,
            "timeout": timeout,
            "allow_redirects": follow_redirects,
            **(
                Utils.prepare_body_payload(body_payload, self.placeholders)
                if body_payload else {}
            )
        }

        return self.session.request(**args)
