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

import re
import uuid
from typing import Any
from urllib.parse import urlparse, parse_qs

from tenable_io.tests.core.product import TenableIOProduct
from tenable_io.tests.core.response import MockResponse


class TenableIOSession:
    """A mock object simulating the requests.Session for Tenable.io tests.

    This class intercepts HTTP requests made during tests and returns mock
    responses based on the state of the TenableIOProduct mock database. It
    uses a routing mechanism to map URL patterns to handler methods.
    """

    def __init__(self, product: TenableIOProduct, mock_data: dict[str, Any]):
        """Initializes the mock session.

        Args:
            product: The mock product instance (the "database").
            mock_data: A dictionary of static mock data.
        """
        self._product = product
        self._mock_data = mock_data
        self.verify = False
        self.headers = {}
        self.export_jobs = {}

        self._get_routes = {
            r"/assets/export/([^/]+)/status": self._get_export_status,
            r"/assets/export/([^/]+)/chunks/(\d+)": self._get_export_chunk,
            r"/workbenches/assets/([^/]+)/vulnerabilities":
                self._get_asset_vulnerabilities,
            r"/assets/([^/]+)$": self._get_asset_by_id,
            r"/policies$": self._get_policies,
            r"/scanners$": self._get_scanners,
            r"/scans/([^/]+)/latest-status": self._get_scan_status,
            r"/scans/([^/]+)$": self._get_scan_details,
        }
        self._post_routes = {
            r"/assets/v2/export$": self._post_initiate_export,
            r"/scans$": self._post_create_scan,
            r"/scans/([^/]+)/launch$": self._post_launch_scan,
        }

    def get(self, url: str, **_kwargs: Any) -> MockResponse:
        """Handles GET requests by routing them to the appropriate handler.

        Args:
            url: The URL being requested.
            **_kwargs: Additional keyword arguments (ignored).

        Returns:
            A MockResponse object with the appropriate data or an error.
        """
        parsed_url = urlparse(url)
        for pattern, handler in self._get_routes.items():
            match = re.search(pattern, parsed_url.path)
            if match:
                query_params = parse_qs(parsed_url.query)
                return handler(query_params, *match.groups())
        return MockResponse(
            {"error": f"GET route not found for {url}"},
            404,
        )

    def post(
        self, url: str, payload: dict | None = None, **_kwargs: Any
    ) -> MockResponse:
        """Handles POST requests by routing them to the appropriate handler.

        Args:
            url: The URL being requested.
            payload: The JSON payload sent with the request.
            **_kwargs: Additional keyword arguments (ignored).

        Returns:
            A MockResponse object with the appropriate data or an error.
        """
        parsed_url = urlparse(url)
        for pattern, handler in self._post_routes.items():
            match = re.search(pattern, parsed_url.path)
            if match:
                return handler(payload or {}, *match.groups())
        return MockResponse(
            {"error": f"POST route not found for {url}"},
            404,
        )

    def _get_export_status(
        self, _: dict, export_uuid: str
    ) -> MockResponse:
        status = self.export_jobs.get(export_uuid, "ERROR")

        if status == "PROCESSING":
            self.export_jobs[export_uuid] = "FINISHED"

        response_data = self._mock_data["export_statuses"].get(
            status,
            {"status": "ERROR", "chunks_available": []}
        )
        return MockResponse(response_data)

    def _get_export_chunk(
        self, _: dict, _export_uuid: str, chunk_id: str
    ) -> MockResponse:
        if str(chunk_id) == "1":
            return MockResponse(self._product.get_all_assets())
        return MockResponse([])

    def _get_asset_vulnerabilities(
        self, query_params: dict, asset_id: str
    ) -> MockResponse:
        allowed_severities = []
        for key, values in query_params.items():
            if key.startswith("filter.") and key.endswith(".value"):
                parts = key.split(".")
                if len(parts) == 3 and query_params.get(
                    f"filter.{parts[1]}.filter"
                ) == [
                    "severity"
                ]:
                    allowed_severities.extend(values)

        all_vulns = self._product.get_vulnerabilities(asset_id)
        filtered = (
            [
                v
                for v in all_vulns
                if str(v.get("severity")).lower() in allowed_severities
            ]
            if allowed_severities
            else all_vulns
        )
        return MockResponse({"vulnerabilities": filtered})

    def _get_asset_by_id(self, _: dict, asset_id: str) -> MockResponse:
        asset = self._product.get_asset_by_id(asset_id)
        return MockResponse(asset) if asset else MockResponse(
            {"error": "Asset not found"},
            404
        )

    def _get_policies(self, *_: Any) -> MockResponse:
        return MockResponse({"policies": self._product.get_policies()})

    def _get_scanners(self, *_: Any) -> MockResponse:
        return MockResponse({"scanners": self._product.get_scanners()})

    def _get_scan_status(self, _: dict, scan_id: str) -> MockResponse:
        scan = self._product.get_scan(scan_id)
        if scan:
            return MockResponse({"status": scan.get("status")})
        return MockResponse({"error": "Scan not found"}, 404)

    def _get_scan_details(self, _: dict, scan_id: str) -> MockResponse:
        scan = self._product.get_scan(scan_id)
        if scan:
            if scan.get("status") == "completed":
                return MockResponse(self._mock_data.get("scan_results", {}))
            return MockResponse(scan)
        return MockResponse({"error": "Scan not found"}, 404)

    def _post_initiate_export(self, *_: Any) -> MockResponse:
        export_uuid = str(uuid.uuid4())
        self.export_jobs[export_uuid] = "PROCESSING"
        return MockResponse({"export_uuid": export_uuid})

    def _post_create_scan(self, payload: dict, *_: Any) -> MockResponse:
        scan_id = self._product.create_scan(payload)
        return MockResponse({"scan": {"id": scan_id}})

    def _post_launch_scan(self, _: dict, scan_id: str) -> MockResponse:
        self._product.update_scan_status(scan_id, "running")
        return MockResponse({"scan_uuid": scan_id})
