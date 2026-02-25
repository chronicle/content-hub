from __future__ import annotations

from typing import Iterable

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, Response, RouteFunction

from cyware_intel_exchange.tests.core.product import CywareIntelExchange


class CywareSession(MockSession[MockRequest, MockResponse, CywareIntelExchange]):
    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        return [
            self.ping_endpoint,
            self.bulk_lookup_endpoint,
            self.add_allowed_iocs_endpoint,
            self.remove_allowed_iocs_endpoint,
            self.get_allowed_iocs_endpoint,
            self.add_note_endpoint,
            self.create_intel_endpoint,
            self.quick_intel_status_endpoint,
            self.get_ioc_details_endpoint,
            self.create_tag_endpoint,
            self.add_tags_endpoint,
            self.remove_tags_endpoint,
            self.mark_false_positive_endpoint,
            self.create_task_endpoint,
            self.get_user_by_email_endpoint,
        ]

    @router.get(r"/ping/?")
    def ping_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content={"status": "ok"}, status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.post(r"/ingestion/openapi/bulk-lookup/.*")
    def bulk_lookup_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.get_bulk_lookup(), status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.post(r"/ingestion/threat-data/bulk-action/un_whitelist/?")
    def remove_allowed_iocs_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.get_remove_allowed_iocs(), status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.get(r"/conversion/allowed_indicators/?")
    def get_allowed_iocs_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.get_allowed_iocs(), status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.post(r"/conversion/allowed_indicators/?")
    def add_allowed_iocs_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.get_add_allowed_iocs(), status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.post(r"/ingestion/notes/?")
    def add_note_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.get_add_note(), status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.post(r"/conversion/quick-intel/create-stix/?")
    def create_intel_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.get_create_intel(), status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.get(r"/conversion/quick-intel/receive-report/.*")
    def quick_intel_status_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.get_quick_intel_status(), status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.get(r"/ingestion/tags/?")
    def get_ioc_details_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.get_ioc_details(), status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.post(r"/ingestion/tags/?")
    def create_tag_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content={"id": "tag_123", "name": "test_tag"}, status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.post(r"/ingestion/threat-data/bulk-action/add_tag/?")
    def add_tags_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.get_add_tags(), status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.post(r"/ingestion/threat-data/bulk-action/remove_tag/?")
    def remove_tags_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.get_remove_tags(), status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.post(r"/ingestion/threat-data/bulk-action/false_positive/?")
    def mark_false_positive_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.get_mark_false_positive(), status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.post(r"/ingestion/tasks/?")
    def create_task_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.get_create_task(), status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.get(r"/rest-auth/users/?")
    def get_user_by_email_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.get_user_by_email(), status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)
