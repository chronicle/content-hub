"""MockSession routing fake HTTP requests to the Abnormal product fixture."""

from __future__ import annotations

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction

from .product import Abnormal


class AbnormalSession(MockSession[MockRequest, MockResponse, Abnormal]):
    def get_routed_functions(self) -> list[RouteFunction]:
        return [
            self.list_threats,
            self.get_threat,
            self.post_threat_action,
            self.list_cases,
            self.get_case,
            self.post_case_action,
            self.search_messages,
            self.remediate_messages,
            self.get_activity_status,
        ]

    @router.get(r"/v1/threats/?$")
    def list_threats(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.list_threats())
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)

    @router.get(r"/v1/threats/[^/]+/?$")
    def get_threat(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.get_threat())
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)

    @router.post(r"/v1/threats/[^/]+/actions/[^/]+/?$")
    def post_threat_action(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.post_threat_action())
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)

    @router.get(r"/v1/cases/?$")
    def list_cases(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.list_cases())
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)

    @router.get(r"/v1/cases/[^/]+/?$")
    def get_case(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.get_case())
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)

    @router.post(r"/v1/cases/[^/]+/actions/[^/]+/?$")
    def post_case_action(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.post_case_action())
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)

    @router.post(r"/v1/search/?$")
    def search_messages(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.search_messages())
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)

    @router.post(r"/v1/search/remediate/?$")
    def remediate_messages(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.remediate_messages())
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)

    @router.get(r"/v1/search/activities/[^/]+/status/?$")
    def get_activity_status(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.get_activity_status())
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)
