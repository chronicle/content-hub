from __future__ import annotations

from typing import Iterable

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, Response, RouteFunction
from TIPCommon.types import SingleJson

from goqr.tests.core.product import GOQR


class GOQRSession(MockSession[MockRequest, MockResponse, GOQR]):
    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        return [
            self.scan_qr_code,
            self.generate_qr_code,
            self.save_evidence,
        ]

    @router.post(r"/v1/read-qr-code/")
    def scan_qr_code(self, request: MockRequest) -> MockResponse:
        try:
            if "invalid" in request.url.netloc:
                return MockResponse(content="Invalid QR Code", status_code=422)

            scan_qr_result: list[SingleJson] = self._product.get_scanned_qr()[0]

            return MockResponse(content=scan_qr_result)

        except ValueError as e:
            return MockResponse(content=str(e), status_code=422)

    @router.get(r"/v1/create-qr-code/")
    def generate_qr_code(self, request: MockRequest) -> MockResponse:
        try:
            data = request.kwargs.get("params", {}).get("data", "")
            if "invalid" in data:
                return MockResponse(content="Unable to generate QR code", status_code=422)

            generated_qr_result: bytes = self._product.get_generated_qr()
            if "invalid" in request.url.netloc:
                return MockResponse(content="Invalid QR Code", status_code=422)

            return MockResponse(content=str(generated_qr_result), status_code=200)

        except ValueError as e:
            return MockResponse(content=str(e), status_code=422)

    @router.post("/api/external/v1/sdk/AddAttachment")
    def save_evidence(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content="{}",
            status_code=200,
        )
