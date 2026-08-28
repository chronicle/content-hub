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
import pathlib

import json
from typing import Iterable

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction
from ...tests.core.zscaler import Zscaler


class ZscalerSession(MockSession[MockRequest, MockResponse, Zscaler]):
    """
    A mock object simulating the requests.Session for Zscaler using Tests.mocks.
    """

    def __init__(self, product: Zscaler) -> None:
        super().__init__(product)
        self._is_authenticated = False

    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            self.oauth_token,
            self.authenticated_session_post,
            self.authenticated_session_get,
            self.get_status,
            self.get_blacklist,
            self.get_whitelist,
            self.post_blacklist,
            self.url_lookup,
            self.activate_changes,
            self.put_security,
            self.delete_auth,
        ]

    @router.post("/oauth2/v1/token")
    def oauth_token(self, request: MockRequest) -> MockResponse:
        """Handle OAuth token generation."""
        data = (
            request.data
            if getattr(request, "data", None)
            else getattr(request, "kwargs", {}).get("data", {})
        )
        if data.get("client_id") == "test_client_id":
            self._is_authenticated = True
            return MockResponse(
                status_code=200,
                content={
                    "access_token": "mocked_oauth_token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        return MockResponse(
            status_code=401, content={"error": "Invalid client credentials"}
        )

    @router.post("/api/v1/authenticatedSession")
    def authenticated_session_post(self, request: MockRequest) -> MockResponse:
        """Handle legacy authentication session creation."""
        payload = (
            request.json
            if getattr(request, "json", None)
            else getattr(request, "kwargs", {}).get("json", {})
        )
        if payload.get("apiKey") == self._product.expected_api_key:
            self._is_authenticated = True
            return MockResponse(
                status_code=200,
                content=self._product.mock_data.get("authenticated_session"),
            )
        return MockResponse(status_code=401, content={"error": "Invalid credentials"})

    @router.get("/api/v1/authenticatedSession")
    def authenticated_session_get(self, _request: MockRequest) -> MockResponse:
        return MockResponse(status_code=200, content={"status": "authenticated"})

    @router.get("/api/v1/status")
    def get_status(self, _request: MockRequest) -> MockResponse:
        return MockResponse(status_code=200, content={"status": "success"})

    @router.get("/api/v1/security/advanced")
    def get_blacklist(self, _request: MockRequest) -> MockResponse:
        return MockResponse(
            status_code=200, content={"blacklistUrls": self._product.blacklist_urls}
        )

    @router.get("/api/v1/security")
    def get_whitelist(self, _request: MockRequest) -> MockResponse:
        return MockResponse(
            status_code=200, content={"whitelistUrls": self._product.whitelist_urls}
        )

    @router.post("/api/v1/security/advanced/blacklistUrls")
    def post_blacklist(self, request: MockRequest) -> MockResponse:
        """Handle adding or removing URLs from blacklist."""
        payload = request.kwargs.get("json")
        if payload is None:
            data = request.kwargs.get("data") or (
                request.args[0] if request.args else None
            )
            if data:
                if isinstance(data, str):
                    try:
                        payload = json.loads(data)
                    except json.JSONDecodeError:
                        pass
                elif isinstance(data, dict):
                    payload = data

        payload = payload or {}

        if "ADD_TO_LIST" in str(request.url):
            for item in payload.get("blacklistUrls", []):
                if item not in self._product.blacklist_urls:
                    self._product.blacklist_urls.append(item)
            return MockResponse(status_code=200, content={"status": "success"})
        if "REMOVE_FROM_LIST" in str(request.url):
            for item in payload.get("blacklistUrls", []):
                if item in self._product.blacklist_urls:
                    self._product.blacklist_urls.remove(item)
            return MockResponse(status_code=200, content={"status": "success"})
        return MockResponse(
            status_code=404, content={"error": f"Action not found in {request.url}"}
        )

    @router.post("/api/v1/urlLookup")
    def url_lookup(self, request: MockRequest) -> MockResponse:
        """Handle URL category lookup."""
        payload = (
            request.json
            if getattr(request, "json", None)
            else getattr(request, "kwargs", {}).get("json", {})
        )
        if payload == ["dhnconstrucciones.com.ar"]:
            return MockResponse(
                status_code=200,
                content=self._product.mock_data.get("url_lookup_success"),
            )
        return MockResponse(status_code=200, content=[])

    @router.post("/api/v1/status/activate")
    def activate_changes(self, _request: MockRequest) -> MockResponse:
        return MockResponse(
            status_code=200,
            content=self._product.mock_data.get("activate_status_success"),
        )

    @router.put("/api/v1/security")
    def put_security(self, request: MockRequest) -> MockResponse:
        """Handle updating whitelist URLs."""
        payload = (
            request.json
            if getattr(request, "json", None)
            else getattr(request, "kwargs", {}).get("json", {})
        )
        if "whitelistUrls" in payload:
            self._product.whitelist_urls = list(payload["whitelistUrls"])
            return MockResponse(
                status_code=200,
                content=self._product.mock_data.get("update_security_success"),
            )
        return MockResponse(status_code=404, content={"error": "Invalid payload"})

    @router.delete("/authenticatedSession")
    def delete_auth(self, _request: MockRequest) -> MockResponse:
        return MockResponse(status_code=204, content={})
