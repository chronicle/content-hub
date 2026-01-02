from __future__ import annotations

from typing import Iterable

from integration_testing import router
from integration_testing.common import get_request_payload
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, Response, RouteFunction
from TIPCommon.types import SingleJson

from sample_integration.tests.core.product import VatComply


class VatComplySession(MockSession[MockRequest, MockResponse, VatComply]):
    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        return [
            self.get_rates,
            self.add_attachment,
            self.update_entities,
            self.get_case_details,
            self.get_case_id_by_filter,
            self.close_case,
        ]

    @router.get(r"/rates")
    def get_rates(self, request: MockRequest) -> MockResponse:
        try:
            params: SingleJson = get_request_payload(request)
            base: str | None = params.get("base")
            symbols: str | None = params.get("symbols")
            date: str | None = params.get("date")
            rates = self._product.get_rates(base, symbols, date)

            return MockResponse(content=rates)
        except ValueError as e:
            return MockResponse(content=str(e), status_code=422)

    @router.post(r"/api/external/v1/sdk/AddAttachment")
    def add_attachment(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={}, status_code=200)

    @router.post(r"/api/external/v1/sdk/UpdateEntities")
    def update_entities(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={}, status_code=200)

    @router.get(r"/api/external/v1/dynamic-cases/GetCaseDetails/[0-9]+")
    def get_case_details(self, request: MockRequest) -> MockResponse:
        case_id = request.url.path.split("/")[-1]
        case = self._product.get_case_details(int(case_id))
        tags = self._product.get_tags(int(case_id))
        if tags:
            self._product.add_tags_to_case(int(case_id), tags)

        return MockResponse(content=case, status_code=200)

    @router.post(r"/api/external/v1/sdk/GetCasesIdByFilter")
    def get_case_id_by_filter(self, request: MockRequest) -> MockResponse:
        case_ids = self._product.get_case_ids()
        if case_ids:
            return MockResponse(content=case_ids, status_code=200)

        return MockResponse(content=[], status_code=200)

    @router.post(r"/api/external/v1/sdk/Close")
    def close_case(self, request: MockRequest) -> MockResponse:
        return MockResponse(content={}, status_code=200)
