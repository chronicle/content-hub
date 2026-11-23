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

from typing import TYPE_CHECKING, NamedTuple

import requests

from TIPCommon.base.interfaces import Apiable

from .constants import DEFAULT_REQUEST_TIMEOUT
from .data_models import ExecuteHTTPRequestParams
from . import utils

if TYPE_CHECKING:
    from TIPCommon.base.interfaces.logger import ScriptLogger
    from TIPCommon.types import SingleJson

    from .auth import AuthenticatedSession
    from .data_models import IntegrationPlaceholders


class ApiParameters(NamedTuple):
    api_root: str
    tenant_id: str


class AzureApiClient(Apiable):
    def __init__(
        self,
        authenticated_session: AuthenticatedSession,
        configuration: ApiParameters,
        placeholders: IntegrationPlaceholders,
        logger: ScriptLogger,
    ) -> None:
        super().__init__(
            authenticated_session=authenticated_session,
            configuration=configuration,
        )
        self.logger: ScriptLogger = logger
        self.api_root: str = configuration.api_root
        self.tenant_id: str = configuration.tenant_id
        self.placeholders: IntegrationPlaceholders = placeholders

    def test_connectivity(self, test_url: str) -> None:
        """Test connectivity to API."""
        http_request_data = ExecuteHTTPRequestParams(
            method="GET",
            url_path=test_url,
        )
        self.execute_http_request(http_request_data)

    def execute_http_request(
        self,
        http_request_data: ExecuteHTTPRequestParams,
    ) -> requests.Response:
        """Execute http request.

        Args:
            http_request_data: ExecuteHTTPRequestParams: http request parameters

        Returns:
            requests.Response: request response
        """
        if (
            http_request_data.headers
            and http_request_data.headers.get("Cookie")
            and http_request_data.cookies
        ):
            del http_request_data.headers["Cookie"]

        args: SingleJson = {
            "method": http_request_data.method,
            "url": self.placeholders.apply_placeholders(http_request_data.url_path),
            "params": self.placeholders.apply_placeholders(http_request_data.params),
            "headers": self.placeholders.apply_placeholders(http_request_data.headers),
            "cookies": http_request_data.cookies,
            "timeout": http_request_data.timeout or DEFAULT_REQUEST_TIMEOUT,
            "allow_redirects": http_request_data.follow_redirects,
            **(
                utils.prepare_body_payload(
                    http_request_data.body_payload, self.placeholders
                )
                if http_request_data.body_payload
                else {}
            ),
        }

        return self.session.request(**args)
