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

import dataclasses

import requests
from urllib3.util import parse_url

from TIPCommon.base.interfaces import ScriptLogger
from . import api_utils
from . import constants
from .exceptions import HTTPV2DomainMismatchException


@dataclasses.dataclass
class ApiParameters:
    test_url: str = None
    auth_method: str = None
    restrict_domain: bool = None


class ApiManager:
    def __init__(
        self,
        session: requests.Session,
        api_params: ApiParameters,
        logger: ScriptLogger,
    ) -> None:
        """Manager for handling API interactions

        This class provides functionality for managing API interactions

        Args:
            session (requests.Session): Session object with corresponding headers
            api_params (ApiParameters): The parameters for the API
            logger (ScriptLogger): The logger object
        """
        self.session = session
        self.test_url = api_params.test_url
        self.auth_method = api_params.auth_method
        self.restrict_domain = api_params.restrict_domain
        self.logger = logger

    def test_connectivity(self) -> None:
        """Test connectivity"""
        if (
            self.test_url is not None
            and self.auth_method != constants.AUTH_METHOD.get("ACCESS_TOKEN")
        ):
            response = self.session.request(
                method=constants.API_REQUEST_METHODS_MAPPING.get("GET"),
                url=self.test_url,
            )
            api_utils.validate_response(response)

    def execute_http_request(
        self,
        method: str,
        url_path: str,
        params: dict = None,
        headers: dict = None,
        cookies: dict = None,
        body_payload: str = None,
        follow_redirects: bool = True,
        timeout: int = constants.DEFAULT_REQUEST_TIMEOUT,
    ) -> requests.Response:
        """Execute http request

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

        if self.restrict_domain:
            url_domain = parse_url(url_path).host
            test_url_domain = parse_url(self.test_url).host
            if url_domain != test_url_domain:
                raise HTTPV2DomainMismatchException

        args = {
            "method": method,
            "url": url_path,
            "params": params,
            "headers": headers,
            "cookies": cookies,
            "timeout": timeout,
            "allow_redirects": follow_redirects,
            **(
                api_utils.prepare_body_payload(body_payload, headers)
                if body_payload
                else {}
            ),
        }

        return self.session.request(**args)
