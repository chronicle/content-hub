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

from typing import TYPE_CHECKING, Any

import requests
from integration_testing import router
from integration_testing.common import get_request_payload
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, Response, RouteFunction

from proof_point_ps.tests.core.product import ProofPointPSProduct

if TYPE_CHECKING:
    from collections.abc import Iterable


class ProofPointPSSession(MockSession[MockRequest, MockResponse, ProofPointPSProduct]):
    """Mock session class for Proofpoint PS API calls."""

    def request(
        self,
        method: str,
        url: str,
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> MockResponse:
        """Override request to raise ConnectionError for unmatched external URLs."""
        try:
            return super().request(method, url, *args, **kwargs)
        except ValueError as e:
            if "doesn't match with any of the other" in str(e):
                err_msg = f"Mocked connection failure to unmatched URL: {url}"
                raise requests.exceptions.ConnectionError(err_msg) from e
            raise

    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        """Return the routed mock methods."""
        return [
            self.handle_get_quarantine,
            self.handle_post_quarantine,
            self.add_attachment,
            self.update_entities,
        ]

    @router.get(r"/rest/v1/quarantine")
    def handle_get_quarantine(self, request: MockRequest) -> MockResponse:
        """Route GET requests to search or download."""
        params = get_request_payload(request)

        # If it's a download (has guid, no sender/recipient/subject filters)
        if "guid" in params and "from" not in params and "rcpt" not in params:
            guid = params["guid"]
            if not self._product.search_records(guid=guid):
                return MockResponse(
                    content={"error": "Message not found"}, status_code=404
                )
            content = self._product.get_email_content(guid)
            return MockResponse(
                content=content.decode("latin1"),
                encoding="latin1",
                headers={"Content-Type": "application/octet-stream"},
                status_code=200,
            )

        # Otherwise it's a search
        records = self._product.search_records(
            sender=params.get("from"),
            recipient=params.get("rcpt"),
            subject=params.get("subject"),
            folder=params.get("folder"),
            guid=params.get("guid"),
            msgid=params.get("msgid"),
        )
        return MockResponse(content={"records": records}, status_code=200)

    @router.post(r"/rest/v1/quarantine")
    def handle_post_quarantine(self, request: MockRequest) -> MockResponse:
        """Route POST requests to execute action."""
        payload = get_request_payload(request)
        self._product.execute_action(payload)
        return MockResponse(content={}, status_code=200)

    @router.post(r"/api/external/v1/sdk/AddAttachment")
    def add_attachment(self, _: MockRequest) -> MockResponse:
        """Mock SecOps SOAR SDK AddAttachment."""
        return MockResponse(content={}, status_code=200)

    @router.post(r"/api/external/v1/sdk/UpdateEntities")
    def update_entities(self, _: MockRequest) -> MockResponse:
        """Mock SecOps SOAR SDK UpdateEntities."""
        return MockResponse(content={}, status_code=200)
