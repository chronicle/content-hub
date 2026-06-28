# Copyright 2026 Google LLC
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
import pathlib

import io
import json
from collections.abc import Iterable

from splunk.tests.common import (
    EventIdNotFoundError,
    create_error_content,
    MOCK_DATA,
)
from splunk.tests.core.product import Splunk
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class SplunkSession(MockSession[MockRequest, MockResponse, Splunk]):

    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            self.get_notable_events,
            self.notable_update,
            self.get_job,
            self.delete_job,
            self.get_job_results,
            self.submit_event,
            self.execute_query_search_job_for_query,
        ]

    @router.post(r".*/?services/search/v2/jobs/export")
    def get_notable_events(self, request: MockRequest) -> MockResponse:
        """Handle POST .*/?services/search/v2/jobs/export requests"""
        if request.url.netloc in ["example.com", "unicode_error.com"]:
            content = (
                create_error_content("Unable to authenticate.")
                if request.url.netloc == "example.com"
                else "Unicode Error Occurred."
            )
            return MockResponse(
                content=content,
                status_code=404,
            )

        stream: io.StringIO = io.StringIO()
        for event in self._product.list_notable_events():
            stram_line: str = json.dumps({"result": event.to_json(), "preview": "mock"})
            stream.write(stram_line)
            stream.write("\n")

        return MockResponse(content=stream.getvalue())

    @router.post("/services/notable_update")
    def notable_update(self, request: MockRequest) -> MockResponse:
        """Handle POST /services/notable_update requests"""
        event_ids: list[str] = request.kwargs["data"].get("ruleUIDs[]")
        status: str | None = request.kwargs["data"].get("status")
        urgency: str | None = request.kwargs["data"].get("urgency")
        new_owner: str | None = request.kwargs["data"].get("newOwner")
        comment: str | None = request.kwargs["data"].get("comment")
        disposition: str | None = request.kwargs["data"].get("disposition")

        if status == "__mock_raise_400_error__":
            return MockResponse(content=create_error_content("error"), status_code=400)

        if "test_manager" in request.url.netloc:
            return MockResponse(content=MOCK_DATA.get("update_notable_events"))

        for event_id in event_ids:
            try:
                self._product.update_notable_event(
                    event_id=event_id,
                    status=status,
                    urgency=urgency,
                    new_owner=new_owner,
                    comments=comment,
                    disposition=disposition,
                )
            except EventIdNotFoundError:
                return MockResponse(
                    status_code=400,
                    content=create_error_content(f"event {event_id} not found"),
                )

        return MockResponse(content={"message": "success"})

    @router.get(r".*/?services/search/jobs/\d{10}\.\d{6}+")
    def get_job(self, request: MockRequest) -> MockResponse:
        r"""Handle GET /services/search/jobs/\d{10}\.\d{6}+ requests"""
        if "test_manager" in request.url.netloc:
            return MockResponse(
                status_code=200,
                content=MOCK_DATA.get("splunk_query_execute_is_job_done"),
            )
        return None

    @router.get(r".*/?services/search/jobs/\d{10}\.\d{6}/results")
    def get_job_results(self, request: MockRequest) -> MockResponse:
        r"""Handle GET /services/search/jobs/\d{10}\.\d{6}/results requests"""
        if "test_manager" in request.url.netloc:
            return MockResponse(
                status_code=200,
                content=MOCK_DATA.get("splunk_execute_get_job_results"),
            )
        return None

    @router.delete(r".*/?services/search/jobs/\d{10}\.\d{6}")
    def delete_job(self, request: MockRequest) -> MockResponse:
        r"""Handle GET /services/search/jobs/\d{10}\.\d{6}/results requests"""
        if "test_manager" in request.url.netloc:
            return MockResponse(
                status_code=200,
                content=MOCK_DATA.get("splunk_query_execute_delete_job"),
            )
        return None

    @router.post(".*/?services/search/jobs")
    def execute_query_search_job_for_query(self, request: MockRequest) -> MockResponse:
        """Handle POST /services/search/jobs requests"""
        if "test_manager" in request.url.netloc:
            return MockResponse(
                status_code=200,
                content=MOCK_DATA.get("splunk_execute_search_job_for_query"),
            )
        return None

    @router.post(".*/?services/receivers/simple")
    def submit_event(self, request: MockRequest) -> MockResponse:
        """Handle POST /services/receivers/simple requests"""
        if "test_manager" in request.url.netloc:
            return MockResponse(
                status_code=200,
                content=MOCK_DATA.get("submit_events"),
            )
        return None
