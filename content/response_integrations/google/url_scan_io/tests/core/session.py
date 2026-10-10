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

from typing import Any

from url_scan_io.tests.core.response import MockResponse
from url_scan_io.tests.core.url_scan_io import UrlScanIo


class UrlScanIoSession:
    """
    A mock object simulating the requests.Session for UrlScanIo.
    """

    def __init__(self, product: UrlScanIo, mock_data: dict[str, Any]) -> None:
        self._product: UrlScanIo = product
        self._mock_data: dict[str, Any] = mock_data
        self.headers: dict[str, str] = {}
        self.verify: bool = True

    def get(self, url: str, params: dict | None = None, **_kwargs: Any) -> MockResponse:
        """Handles GET requests."""
        if "api/v1/search" in url:
            return self._handle_search(params)

        if "user/quotas" in url:
            return MockResponse(200, {})

        if "screenshots" in url:
            return MockResponse(200, content=b"fake_image_content")

        if "api/v1/result" in url:
            return self._handle_result(url)

        return MockResponse(404, {"error": f"GET route not found for {url}"})

    def post(self, url: str, json: dict | None = None, **_kwargs: Any) -> MockResponse:
        """Handles POST requests."""
        _ = json
        if "api/v1/scan" in url:
            return MockResponse(
                200, {"uuid": "test-uuid", "message": "Submission successful"}
            )

        return MockResponse(404, {"error": f"POST route not found for {url}"})

    def _handle_result(self, url: str) -> MockResponse:
        """Simulates the result endpoint."""
        parts = url.split("/")
        scan_id = parts[-1] if parts[-1] else parts[-2]

        for scan in self._product.scans:
            if scan.get("task", {}).get("uuid") == scan_id:
                return MockResponse(200, scan)

        return MockResponse(404, {"error": f"Scan {scan_id} not found"})

    def _handle_search(self, params: dict | None) -> MockResponse:
        """Simulates the search endpoint."""
        query = params.get("q") if params else ""

        # In our mock, if the product has scans matching the query, we return them.
        # The _mock_data["search_results"] structure contains a list of results.
        # We will construct a response based on what's in the product.

        matching_scans = self._product.search_scans(query)

        response_data = {
            "results": matching_scans,
            "total": len(matching_scans),
            "took": 100,
            "has_more": False,
        }

        return MockResponse(200, response_data)
