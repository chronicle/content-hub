from __future__ import annotations

from typing import Iterable
from http import HTTPStatus
import re

from okta.tests.core.product import (
    Product,
)
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction
from okta.tests.responses.api.common import USER_RESPONSE


class Session(MockSession[MockRequest, MockResponse, Product]):
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            self.get_oauth_token,
            self.get_user,
            self.send_itp_signal,
            self.clear_user_sessions,
            self.get_user_by_id,
            self.list_user_groups,
            self.list_roles,
        ]

    @router.post("/oauth2/v1/token")
    def get_oauth_token(self, _: MockRequest) -> MockResponse:
        """Mocks the OAuth 2.0 token endpoint."""
        return MockResponse(
            content={"access_token": "mock_oauth_access_token"},
            status_code=HTTPStatus.OK,
        )

    @router.get("/api/v1/users/me")
    def get_user(self, _: MockRequest) -> MockResponse:
        return MockResponse(content=USER_RESPONSE, status_code=200)

    @router.post("/security/api/v1/security-events")
    def send_itp_signal(self, _: MockRequest) -> MockResponse:
        status_code = self._product.get_status()
        return MockResponse(content={}, status_code=status_code)

    @router.delete(r"/api/v1/users/(?P<user_id>[^/]+)/sessions")
    def clear_user_sessions(self, request: MockRequest) -> MockResponse:
        """Mock the API endpoint for clearing a user's sessions."""
        match = re.search(
            r"/api/v1/users/(?P<user_id>[^/]+)/sessions", request.url.path
        )
        user_id = match.group("user_id") if match else None
        status_code = self._product.get_clear_user_sessions_status(user_id)
        return MockResponse(content={}, status_code=status_code)

    @router.get(r"/api/v1/users/(?P<user_id>[^/]+)$")
    def get_user_by_id(self, request: MockRequest) -> MockResponse:
        """Mock the API endpoint for getting a user by their ID."""
        match = re.search(r"/api/v1/users/(?P<user_id>[^/]+)$", request.url.path)
        user_id = match.group("user_id") if match else None
        status, data = (
            self._product.get_get_user_response(user_id)
            if user_id
            else (HTTPStatus.NOT_FOUND, None)
        )
        return MockResponse(content=data, status_code=status)

    @router.get(r"/api/v1/users/(?P<user_id>[^/]+)/groups")
    def list_user_groups(self, request: MockRequest) -> MockResponse:
        """Mock the paginated API endpoint for listing a user's groups."""
        match = re.search(r"/api/v1/users/(?P<user_id>[^/]+)/groups", request.url.path)
        user_id = match.group("user_id") if match else None
        page_index = int(request.params.get("after", ["0"])[0])
        page = self._product.get_user_groups_page(user_id, page_index)
        return _build_paginated_response(request, page_index, page)

    @router.get(r"/api/v1/users/(?P<user_id>[^/]+)/roles")
    def list_roles(self, request: MockRequest) -> MockResponse:
        """Mock the API endpoint for listing a user's roles."""
        match = re.search(r"/api/v1/users/(?P<user_id>[^/]+)/roles", request.url.path)
        user_id = match.group("user_id") if match else None
        page_index = int(request.params.get("after", ["0"])[0])
        page = self._product.get_user_roles_page(user_id, page_index)
        return _build_paginated_response(request, page_index, page)


def _build_paginated_response(
    request: MockRequest,
    page_index: int,
    page: tuple[int, object, bool],
) -> MockResponse:
    """Build a MockResponse with a rel="next" Link header when more pages follow."""
    status, data, has_next = page
    headers: dict[str, str] = {}
    if has_next:
        page_url = f"{request.url.scheme}://{request.url.netloc}{request.url.path}"
        headers["link"] = (
            f'<{page_url}>; rel="self", <{page_url}?after={page_index + 1}>; rel="next"'
        )

    return MockResponse(content=data, status_code=status, headers=headers)
