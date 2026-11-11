from __future__ import annotations

from typing import Iterable

from TIPCommon.types import SingleJson
from google_threat_intelligence.tests.core.product import (
    GoogleThreatIntelligenceProduct,
    GoogleThreatIntelligenceSdkProduct,
)
from google_threat_intelligence.tests.responses.api import common_responses
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class GoogleThreatIntelligenceSession(
    MockSession[MockRequest, MockResponse, GoogleThreatIntelligenceProduct]
):
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            self.post_exchange_api_key,
            self.get_gti_documents_api,
            self.get_gti_alerts_api,
            self.search_gti_findings_api,
            self.get_gti_findings_api,
            self.get_asm_projects,
            self.post_asm_notes_issue,
            self.get_urls,
            self.get_private_urls,
            self.get_analyses,
            self.get_private_analyses,
            self.get_non_asm_ping_result,
            self.get_ip_addresses,
            self.get_search_query,
            self.get_ip_address_comments,
            self.download_file,
            self.get_url_address_comments,
            self.get_file_comments,
            self.get_file_hash,
            self.get_private_file_hash,
            self.get_domains,
            self.get_widget,
            self.get_widget_html,
            self.download_file,
            self.update_analysis_text,
            self.upload_attachments_to_an_alert_analysis,
            self.submit_private_url,
            self.get_dtm_alerts,
            self.get_dtm_monitors,
            self.get_dtm_alert,
            self.patch_dtm_alerts,
            self.get_urls_associations,
            self.get_files_associations,
            self.get_ip_addresses_associations,
            self.get_domains_associations,
            self.get_urls_reports_associations,
            self.get_files_reports_associations,
            self.get_ip_addresses_reports_associations,
            self.get_domains_reports_associations,
            self.get_ioc_stream,
            self.search_asm_issues,
            self.search_asm_entities,
            self.get_asm_issue,
        ]

    @router.post(".*exchange/api-key")
    def post_exchange_api_key(self, _: MockRequest) -> MockResponse:
        """Mock response for GTI token exchange API."""
        return MockResponse(
            content={"access_token": "mock_access_token_xyz"}, status_code=200
        )

    @router.get(".*v1beta/projects/.*/alerts/.*/documents/.*")
    def get_gti_documents_api(self, request: MockRequest) -> MockResponse:
        """Mock response for GTI alert documents API."""
        doc_id: str = request.real_url.split("/")[-1]
        return MockResponse(
            content={
                "name": (
                    f"projects/gti-comprehensive-project/alerts/"
                    f"mock_gti_comprehensive_301/documents/{doc_id}"
                ),
                "title": "Dark Web Credential Dump Document",
                "displayName": "Dark Web Credential Dump Document",
                "sourceUri": "https://darkweb.example.onion/dump/99",
                "author": "dark_threat_actor",
                "content": "Raw leaked document content...",
                "createTime": "2026-09-16T05:02:00Z",
                "translation": {
                    "translatedTitle": "Translated Dump Document",
                    "translatedContent": "Translated content...",
                },
            },
            status_code=200,
        )

    @router.get(".*v1beta/projects/.*/alerts.*")
    def get_gti_alerts_api(self, request: MockRequest) -> MockResponse:
        """Mock response for GTI alerts API."""
        if "gti-comprehensive-project" in request.real_url:
            return MockResponse(
                content=common_responses.GTI_ALERTS_COMPREHENSIVE_RESPONSE,
                status_code=200,
            )
        return MockResponse(
            content=common_responses.GTI_ALERTS_DEFAULT_RESPONSE,
            status_code=200,
        )

    @router.get(".*v1beta/projects/.*/findings:search.*")
    def search_gti_findings_api(self, request: MockRequest) -> MockResponse:
        """Mock response for GTI findings search API."""
        url_str: str = str(request.real_url)
        findings: list[SingleJson] = []
        if "gti_comprehensive_alert_301" in url_str:
            findings = [
                {
                    "name": "projects/gti-comprehensive-project/findings/mock_finding_c301_a",
                    "displayName": "Leaked Corporate Database Credentials Finding",
                    "provider": "GTI Dark Web Crawler",
                    "aiSummary": "Administrator credentials leaked for database server.",
                    "user": "db_admin@cymbalbank.com",
                    "IPs": ["198.51.100.45", "198.51.100.46"],
                    "UserNames": ["db_admin@cymbalbank.com", "sys_admin@cymbalbank.com"],
                    "Domains": ["db1.cymbalbank.com", "db2.cymbalbank.com"],
                    "audit": {"createTime": "2026-09-16T05:00:00Z"},
                },
                {
                    "name": "projects/gti-comprehensive-project/findings/mock_finding_c301_b",
                    "displayName": "Leaked SSL Certificate & Private Key Finding",
                    "provider": "GTI Certificate Intelligence",
                    "aiSummary": "Compromised SSL certificates detected.",
                    "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "filename": "cymbalbank_private_key.pem",
                    "url": "https://example.com/raw/leaked_key_99",
                    "threat_actor": "UNC2452",
                    "audit": {"createTime": "2026-09-16T05:01:00Z"},
                },
            ]
        elif "mock_gti_101" in url_str or "gti_alert_101" in url_str:
            findings = [
                {
                    "name": "projects/gti-test/findings/mock_finding_201",
                    "displayName": "Leaked Admin Credentials Finding",
                    "provider": "GTI Threat Engine",
                    "aiSummary": "User credentials found in dark web dump.",
                    "user": "secops_admin@cymbalbank.com",
                    "IPs": ["198.51.100.10", "198.51.100.11"],
                    "Domains": ["auth.cymbalbank.com"],
                    "audit": {"createTime": "2026-09-15T12:00:00Z"},
                }
            ]
        return MockResponse(content={"findings": findings}, status_code=200)

    @router.get(".*v1beta/projects/.*/findings/.*")
    def get_gti_findings_api(self, request: MockRequest) -> MockResponse:
        """Mock response for individual GTI finding retrieval API."""
        finding_id: str = request.real_url.split("/")[-1]
        if "mock_finding_c301_a" in finding_id:
            return MockResponse(
                content={
                    "name": "projects/gti-comprehensive-project/findings/mock_finding_c301_a",
                    "displayName": "Leaked Corporate Database Credentials Finding",
                    "provider": "GTI Dark Web Crawler",
                    "aiSummary": "Administrator credentials leaked for database server.",
                    "user": "db_admin@cymbalbank.com",
                    "IPs": ["198.51.100.45", "198.51.100.46"],
                    "UserNames": ["db_admin@cymbalbank.com", "sys_admin@cymbalbank.com"],
                    "Domains": ["db1.cymbalbank.com", "db2.cymbalbank.com"],
                    "audit": {"createTime": "2026-09-16T05:00:00Z"},
                },
                status_code=200,
            )
        if "mock_finding_c301_b" in finding_id:
            return MockResponse(
                content={
                    "name": "projects/gti-comprehensive-project/findings/mock_finding_c301_b",
                    "displayName": "Leaked SSL Certificate & Private Key Finding",
                    "provider": "GTI Certificate Intelligence",
                    "aiSummary": "Compromised SSL certificates detected.",
                    "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "filename": "cymbalbank_private_key.pem",
                    "url": "https://example.com/raw/leaked_key_99",
                    "threat_actor": "UNC2452",
                    "audit": {"createTime": "2026-09-16T05:01:00Z"},
                },
                status_code=200,
            )
        return MockResponse(
            content={
                "name": f"projects/gti-test/findings/{finding_id}",
                "displayName": "Leaked Admin Credentials Finding",
                "provider": "GTI Threat Engine",
                "aiSummary": "User credentials found in dark web dump.",
                "user": "secops_admin@cymbalbank.com",
                "IPs": ["198.51.100.10", "198.51.100.11"],
                "Domains": ["auth.cymbalbank.com"],
                "audit": {"createTime": "2026-09-15T12:00:00Z"},
            },
            status_code=200,
        )

    @router.get("/api/v3/ioc_stream")
    def get_ioc_stream(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content={"data": []}, status_code=200
        )

    @router.get("/api/v3/asm/projects")
    def get_asm_projects(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content={"result": [{"name": "TestProject", "id": 123456}]}, status_code=200
        )

    @router.get("/api/v3/asm/search/issues/.*")
    def search_asm_issues(self, request: MockRequest) -> MockResponse:
        """Mocks the ASM issues search endpoint (query string is part of the path)"""
        query: str = request.real_url.split("/api/v3/asm/search/issues/", 1)[1]
        return MockResponse(
            content=self._product.search_asm_issues(
                query=query,
                page=int(request.params.get("page", ["0"])[0]),
                page_size=int(request.params.get("page_size", ["100"])[0]),
            ),
            status_code=200,
        )

    @router.get("/api/v3/asm/search/entities/.*")
    def search_asm_entities(self, request: MockRequest) -> MockResponse:
        """Mocks the ASM entities search endpoint (query string is part of the path)"""
        return MockResponse(
            content=self._product.search_asm_entities(
                page=int(request.params.get("page", ["0"])[0]),
                page_size=int(request.params.get("page_size", ["100"])[0]),
            ),
            status_code=200,
        )

    @router.get("/api/v3/asm/issues/[^/]+")
    def get_asm_issue(self, request: MockRequest) -> MockResponse:
        """Mocks the ASM issue details endpoint"""
        issue_id: str = request.real_url.split("/")[-1]
        return MockResponse(
            content=self._product.get_asm_issue(issue_id), status_code=200
        )

    @router.post("/api/v3/asm/notes/issue/[a-zA-Z0-9]+")
    def post_asm_notes_issue(self, request: MockRequest) -> MockResponse:
        if request.real_url.endswith("successful"):
            return MockResponse(content={"success": True}, status_code=200)
        return MockResponse(content={"success": False}, status_code=400)

    @router.get("/api/v3/metadata")
    def get_non_asm_ping_result(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={}, status_code=200)

    @router.get("/api/v3/ip_addresses/[0-9.]+")
    def get_ip_addresses(self, request: MockRequest) -> MockResponse:
        """Return response for ip type requests"""
        ip_address: str = request.real_url.split("/")[-1]
        response: SingleJson = self._product.get_ip_ioc(ip_address)
        if response.get("data", {}):
            return MockResponse(content=response, status_code=200)
        return MockResponse(content=response, status_code=400)

    @router.get("/api/v3/urls/[a-zA-Z0-9]+")
    def get_urls(self, request: MockRequest) -> MockResponse:
        """Return response for url type requests"""
        encoded_url: str = request.real_url.split("/")[-1]
        response: SingleJson = self._product.get_url_ioc(encoded_url)
        if response.get("data", {}):
            return MockResponse(content=response, status_code=200)
        return MockResponse(content=response, status_code=404)

    @router.get("/api/v3/private/urls/[a-zA-Z0-9]+")
    def get_private_urls(self, request: MockRequest) -> MockResponse:
        """Return response for url type requests"""
        encoded_url: str = request.real_url.split("/")[-1]
        response: SingleJson = self._product.get_url_ioc(encoded_url)
        if response.get("data", {}):
            return MockResponse(content=response, status_code=200)
        return MockResponse(content=response, status_code=404)

    @router.get("/api/v3/analyses/[a-zA-Z0-9]+")
    def get_analyses(self, request: MockRequest) -> MockResponse:
        """Return response for public analysis requests."""
        analysis_id: str = request.real_url.split("/")[-1]
        response = self._product.get_analysis(analysis_id)
        if response:
            return MockResponse(content=response, status_code=200)
        return MockResponse(content={"data": {"attributes": {"status": "completed"}}}, status_code=200)

    @router.get("/api/v3/private/analyses/[a-zA-Z0-9]+")
    def get_private_analyses(self, request: MockRequest) -> MockResponse:
        """Return response for private analysis requests."""
        analysis_id: str = request.real_url.split("/")[-1]
        response = self._product.get_analysis(analysis_id)
        if response:
            return MockResponse(content=response, status_code=200)
        return MockResponse(content={"data": {"attributes": {"status": "completed"}}}, status_code=200)

    @router.get("/api/v3/files/[a-zA-Z0-9']+")
    def get_file_hash(self, request: MockRequest) -> MockResponse:
        """Return response for hash file type requests"""
        file_hash: str = request.real_url.split("/")[-1]
        response: SingleJson = self._product.get_file_hash_ioc(file_hash)
        if response.get("data", {}):
            return MockResponse(content=response, status_code=200)
        return MockResponse(content=response, status_code=404)

    @router.get("/api/v3/private/files/[0-9A-Za-z]+")
    def get_private_file_hash(self, request: MockRequest) -> MockResponse:
        """Return response for private hash file type requests."""
        file_hash: str = request.real_url.split("/")[-1]
        response: SingleJson = self._product.get_file_hash_ioc(file_hash)
        if response.get("data", {}):
            return MockResponse(content=response, status_code=200)
        return MockResponse(content=response, status_code=404)

    @router.get("/api/v3/domains/[a-zA-Z0-9.-]+")
    def get_domains(self, request: MockRequest) -> MockResponse:
        """Return response for domain type requests"""
        domain: str = request.real_url.split("/")[-1]
        response: SingleJson = self._product.get_domain_ioc(domain)
        if response.get("data", {}):
            return MockResponse(content=response, status_code=200)
        return MockResponse(content=response, status_code=400)

    @router.get("/api/v3/gtiwidget")
    def get_widget(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content=common_responses.WIDGET_URL_RESPONSE, status_code=200
        )

    @router.get("/api/v3/gtiwidget/[a-zA-Z0-9]+/summary")
    def get_widget_html(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content=common_responses.EMPTY_HTML_RESPONSE, status_code=200
        )

    def _get_comments_response(self, request):
        address = request.real_url.split("/")[-2]
        response = self._product.get_comments(ioc_identifier=address)
        if response is None:
            return MockResponse(content=common_responses.INVALID_FILE_HASH_RESPONSE, status_code=404)
        return MockResponse(content=response, status_code=200)

    @router.get("/api/v3/ip_addresses/[0-9.]+/comments")
    def get_ip_address_comments(self, request: MockRequest) -> MockResponse:
        return self._get_comments_response(request=request)

    @router.get("/api/v3/urls/[a-z0-9]+/comments")
    def get_url_address_comments(self, request: MockRequest) -> MockResponse:
        return self._get_comments_response(request=request)

    @router.get("/api/v3/files/[a-zA-Z0-9]+/comments")
    def get_file_comments(self, request: MockRequest) -> MockResponse:
        return self._get_comments_response(request=request)

    @router.get("/api/v3/ip_addresses/comments")
    def get_ip_addresses_comments(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={})

    @router.get("/api/v3/intelligence/search")
    def get_search_query(self, _: MockRequest) -> MockResponse:
        raw_data = self._product.get_search_response()
        return MockResponse(content=raw_data)

    @router.get("/api/v3/files/[0-9A-Za-z]+/download")
    def download_file(self, _: MockRequest) -> MockResponse:
        return MockResponse(content="This is a Test download file content")

    @router.put("/api/v3/dtm/alerts/[0-9a-z]+/analysis")
    def update_analysis_text(self, _: MockRequest) -> MockResponse:
        return MockResponse(status_code=204)

    @router.post("/api/v3/dtm/alerts/[0-9a-z]+/attachments")
    def upload_attachments_to_an_alert_analysis(self, _: MockRequest) -> MockResponse:
        """Mocks the endpoint for uploading attachments to an alert"""
        return MockResponse(status_code=200)

    @router.get("/api/v3/dtm/alerts")
    def get_dtm_alerts(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content=common_responses.DTM_ALERTS_RESPONSE, status_code=200
        )

    @router.get("/api/v3/dtm/alerts/[0-9a-z]+")
    def get_dtm_alert(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content=common_responses.DTM_ALERT_RESPONSE, status_code=200
        )

    @router.patch("/api/v3/dtm/alerts/[0-9a-z]+")
    def patch_dtm_alerts(self, request: MockRequest) -> MockResponse:
        """Mocks the endpoint for patching dtm alerts"""
        if request.real_url.endswith("successful"):
            return MockResponse(
                content=common_responses.DTM_ALERT_RESPONSE, status_code=200
            )
        return MockResponse(content={"success": False}, status_code=400)

    @router.get("/api/v3/dtm/monitors")
    def get_dtm_monitors(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content=common_responses.DTM_MONITOR_RESPONSE, status_code=200
        )

    @router.post("/api/v3/private/urls")
    def submit_private_url(self, _: MockRequest) -> MockResponse:
        """Mocks the endpoint for private url submit"""
        return MockResponse(content={"data": {"id": "test_id"}})

    @router.get("/api/v3/files/[0-9A-Za-z]+/associations")
    def get_files_associations(self, _: MockRequest) -> MockResponse:
        """Mocks the endpoint for getting file associations."""
        return MockResponse(
            content=common_responses.RELATED_ASSOCIATIONS_RESPONSE, status_code=200
        )

    @router.get("/api/v3/urls/[0-9A-Za-z]+/associations")
    def get_urls_associations(self, _: MockRequest) -> MockResponse:
        """Mocks the endpoint for getting URL associations."""
        return MockResponse(
            content=common_responses.RELATED_ASSOCIATIONS_RESPONSE, status_code=200
        )

    @router.get("/api/v3/domains/[0-9A-Za-z.-]+/associations")
    def get_domains_associations(self, _: MockRequest) -> MockResponse:
        """Mocks the endpoint for getting domain associations."""
        return MockResponse(
            content=common_responses.RELATED_ASSOCIATIONS_RESPONSE, status_code=200
        )

    @router.get("/api/v3/ip_addresses/[0-9.]+/associations")
    def get_ip_addresses_associations(self, _: MockRequest) -> MockResponse:
        """Mocks the endpoint for getting IP address associations."""
        return MockResponse(
            content=common_responses.RELATED_ASSOCIATIONS_RESPONSE, status_code=200
        )

    @router.get("/api/v3/files/[0-9A-Za-z]+/reports")
    def get_files_reports_associations(self, _: MockRequest) -> MockResponse:
        """Mocks the endpoint for getting file association reports."""
        return MockResponse(
            content=common_responses.RELATED_ASSOCIATIONS_REPORTS_RESPONSE,
            status_code=200,
        )

    @router.get("/api/v3/urls/[0-9A-Za-z]+/reports")
    def get_urls_reports_associations(self, _: MockRequest) -> MockResponse:
        """Mocks the endpoint for getting URL association reports."""
        return MockResponse(
            content=common_responses.RELATED_ASSOCIATIONS_REPORTS_RESPONSE,
            status_code=200,
        )

    @router.get("/api/v3/domains/[0-9A-Za-z.-]+/reports")
    def get_domains_reports_associations(self, _: MockRequest) -> MockResponse:
        """Mocks the endpoint for getting domain association reports."""
        return MockResponse(
            content=common_responses.RELATED_ASSOCIATIONS_REPORTS_RESPONSE,
            status_code=200,
        )

    @router.get("/api/v3/ip_addresses/[0-9.]+/reports")
    def get_ip_addresses_reports_associations(self, _: MockRequest) -> MockResponse:
        """Mocks the endpoint for getting IP address association reports."""
        return MockResponse(
            content=common_responses.RELATED_ASSOCIATIONS_REPORTS_RESPONSE,
            status_code=200,
        )


class GoogleThreatIntelligenceSdkSession(
    MockSession[MockRequest, MockResponse, GoogleThreatIntelligenceSdkProduct]
):
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            self.get_external_update_entities,
            self.alert_details,
            self.case_meta_data,
            self.create_entity,
            self.extend_graph,
        ]

    @router.post("/api/external/v1/sdk/UpdateEntities")
    def get_external_update_entities(self, _: MockRequest) -> MockResponse:
        """Mocks the endpoint for updating external entities."""
        return MockResponse(content={})

    @router.post("/api/external/v1/sdk/CreateEntity")
    def create_entity(self, _: MockRequest) -> MockResponse:
        """Mocks the endpoint for creating an entity."""
        return MockResponse("Successfully Created Entity", status_code=200)

    @router.post("/api/external/v1/investigator/ExtendCaseGraph")
    def extend_graph(self, _: MockRequest) -> MockResponse:
        """Mocks the endpoint for extending a case graph."""
        return MockResponse(status_code=200)

    @router.post("/api/external/v1/sdk/AlertFullDetails")
    def alert_details(self, _) -> MockResponse:
        """Mocks the endpoint for getting full alert details."""
        return MockResponse(
            content=common_responses.SDK_MOCK_DATA["full_alert_data"], status_code=200
        )

    @router.get("/api/external/v1/sdk/CaseMetadata/[0-1]+")
    def case_meta_data(self, _) -> MockResponse:
        """Mocks the endpoint for getting case metadata."""
        return MockResponse(
            content=common_responses.SDK_MOCK_DATA["case_meta_data"], status_code=200
        )
