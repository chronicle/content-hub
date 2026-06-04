# Copyright 2025 Google LLC
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

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction

from file_utilities.tests.common import MOCK_CASE_IDENTIFIER
from file_utilities.tests.core.product import FileUtilitiesProduct


class FileUtilitiesMockSession(
    MockSession[MockRequest, MockResponse, FileUtilitiesProduct]
):
    """Mock outgoing REST session matching universal test framework standards."""

    def get_routed_functions(self) -> list[RouteFunction]:
        """Provide list of active routing handlers mapped within the session.

        Returns:
            List of bound routing handler functions.
        """
        return [
            self.get_case_metadata,
            self.get_alerts_full_details,
            self.get_attachments_metadata,
            self.get_attachment_data,
        ]

    @router.get(r"/api/external/v1/sdk/CaseMetadata/\S+")
    def get_case_metadata(self, _: MockRequest) -> MockResponse:
        """Intercept SDK metadata resolution endpoint calls.

        Returns:
            Simulated successful HTTP response containing case metadata.
        """
        return MockResponse(content=self._product.get_case_metadata(MOCK_CASE_IDENTIFIER))

    @router.get(r"/api/external/v1/sdk/AlertsFullDetails/\S+")
    def get_alerts_full_details(self, _: MockRequest) -> MockResponse:
        """Intercept SDK full details alert retrieval queries.

        Returns:
            Simulated successful HTTP response containing full alerts array.
        """
        return MockResponse(
            content=self._product.get_alerts_full_details(MOCK_CASE_IDENTIFIER)
        )

    @router.get(r".*/GetCaseFullDetails/\S+|.*/caseComments.*|.*/Attachments/\S+")
    def get_attachments_metadata(self, _: MockRequest) -> MockResponse:
        """Intercept SDK attachment metadata resolution endpoint queries.

        Returns:
            Simulated successful HTTP response containing comprehensive attachment records.
        """
        records = []
        for rec in self._product._metadata_records:
            item = dict(rec)
            item["evidence_name"] = rec.get("evidenceName")
            item["evidence_id"] = rec.get("evidenceId")
            item["file_type"] = rec.get("fileType")
            item["comment"] = rec.get("description")
            records.append(item)

        return MockResponse(
            content={
                "wall_data": records,
                "caseComments": records,
                "Attachments": records,
            }
        )

    @router.get(r".*/AttachmentData.*")
    def get_attachment_data(self, request: MockRequest) -> MockResponse:
        """Intercept SDK attachment binary stream retrieval requests.

        Returns:
            Simulated successful HTTP response containing raw file bytes payload.
        """
        path_str: str = getattr(request.url, "path", "")
        query_str: str = getattr(request.url, "query", "")
        full_url: str = str(request.url)

        if not path_str:
            if "path=" in full_url:
                path_str = full_url.split("path=")[1].split(",")[0].strip("'\"")
            else:
                path_str = full_url.split("?")[0]

        if not query_str:
            if "query=" in full_url:
                query_str = full_url.split("query=")[1].split(",")[0].strip("'\"")
            elif "?" in full_url:
                query_str = full_url.split("?")[1]

        evidence_id: str = "4"
        if "attachmentId=" in query_str:
            evidence_id = query_str.split("attachmentId=")[1].split("&")[0]
        else:
            parts: list[str] = [p for p in path_str.split("/") if p]
            if parts and parts[-1] != "AttachmentData":
                evidence_id = parts[-1]

        res: MockResponse = MockResponse()
        res._content = self._product.get_attachment_blob(evidence_id)
        return res
