from __future__ import annotations

from collections.abc import Iterable

from integration_testing import router
from integration_testing.common import get_request_payload
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, Response, RouteFunction

from .product import PortnoxCloud

NOT_FOUND_BODY = {"InternalError": "Object not found", "InternalErrorCode": 5357}


class PortnoxCloudSession(MockSession[MockRequest, MockResponse, PortnoxCloud]):
    """Routes the Portnox Cloud endpoints the actions call to the in-memory tenant."""

    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        return [
            self.device_list,
            self.device_block,
            self.account_block,
            self.account_move_to_group,
            self.sdk_ok,
        ]

    def _failure(self) -> MockResponse | None:
        # Compare the result with None: a requests.Response with an error status is falsy.
        if self._product.failure_status_code is None:
            return None
        return MockResponse(content={"Message": "Simulated failure"}, status_code=self._product.failure_status_code)

    @router.post(r".*/api/device/list")
    def device_list(self, request: MockRequest) -> MockResponse:
        if (failure := self._failure()) is not None:
            return failure
        query = get_request_payload(request)["Query"]
        response = self._product.list_devices(query["Filter"], query["PageNumber"], query["PageSize"])
        return MockResponse(content=response)

    @router.post(r".*/api/device/block")
    def device_block(self, request: MockRequest) -> MockResponse:
        if (failure := self._failure()) is not None:
            return failure
        body = get_request_payload(request)
        if not self._product.block_device(body["EntityId"], body["Reason"]):
            return MockResponse(content=NOT_FOUND_BODY, status_code=400)
        return MockResponse(content="")

    @router.post(r".*/api/account/block")
    def account_block(self, request: MockRequest) -> MockResponse:
        if (failure := self._failure()) is not None:
            return failure
        body = get_request_payload(request)
        if not self._product.block_account(body["EntityId"], body["Reason"]):
            return MockResponse(content=NOT_FOUND_BODY, status_code=400)
        return MockResponse(content="")

    @router.post(r".*/api/account/move-to-group")
    def account_move_to_group(self, request: MockRequest) -> MockResponse:
        if (failure := self._failure()) is not None:
            return failure
        body = get_request_payload(request)
        if not self._product.move_account_to_group(body["AccountId"], body["GroupName"]):
            return MockResponse(content=NOT_FOUND_BODY, status_code=400)
        return MockResponse(content="")

    @router.post(r"/api/external/v1/sdk/.+")
    def sdk_ok(self, _: MockRequest) -> MockResponse:
        """Accept the SDK's own platform calls (entity updates, insights)."""
        return MockResponse(content={})
