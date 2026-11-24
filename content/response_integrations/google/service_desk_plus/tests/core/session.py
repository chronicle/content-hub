from __future__ import annotations

from collections.abc import Iterable

from service_desk_plus.tests.common import ADD_REQUEST_MOCK, REQUEST
from service_desk_plus.tests.core.product import ServiceDeskPlus
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class ServiceDeskPlusSession(MockSession[MockRequest, MockResponse, ServiceDeskPlus]):
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [self.handle_request]

    @router.get(r"/sdpapi/request/")
    def handle_request(self, request: MockRequest) -> MockResponse:
        operation_name = request.kwargs.get("params", {}).get("OPERATION_NAME")
        requests = self._product.get_requests()

        if operation_name == "ADD_REQUEST":
            if "FailSubject" in str(
                request.kwargs.get("params", {}).get("INPUT_DATA", "")
            ):
                return MockResponse(
                    content={
                        "operation": {
                            "result": {"status": "Failed", "message": "Failed"}
                        }
                    }
                )
            return MockResponse(content=ADD_REQUEST_MOCK.to_json())

        if operation_name == "GET_REQUESTS":
            return MockResponse(
                content=requests[0].to_json() if requests else REQUEST.to_json()
            )

        return MockResponse(
            content={
                "operation": {
                    "result": {
                        "status": "Failed",
                        "message": f"Unknown operation {operation_name}",
                    }
                }
            },
            status_code=400,
        )
