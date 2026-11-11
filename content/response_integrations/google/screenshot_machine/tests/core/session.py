from __future__ import annotations

from typing import Iterable

from screenshot_machine.tests.core.product import ScreenshotMachine
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


MOCK_ERROR_MSG: str = "Mock Error"


class ScreenshotMachineSession(
    MockSession[MockRequest, MockResponse, ScreenshotMachine]
):

    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [self.screenshot_machine]

    @router.get("/")
    def screenshot_machine(self, request: MockRequest) -> MockResponse:
        """Handle the root '/' request"""
        request_params: dict[str, str | int] = request.kwargs["params"]
        if "raise_error" in request_params.values():
            return MockResponse(content=MOCK_ERROR_MSG, status_code=404)

        screenshot: str = self._product.take_screenshot(
            api_key=request_params["key"],
            url=request_params["url"],
            image_format=request_params["format"],
            device=request_params["device"],
            dimension=request_params["dimension"],
            cache_limit=request_params["cacheLimit"],
            delay=request_params["delay"],
        )
        return MockResponse(content=screenshot)
