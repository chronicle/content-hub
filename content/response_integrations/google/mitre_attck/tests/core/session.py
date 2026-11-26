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

from mitre_attck.tests.core.product import MitreAttckProduct
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class MitreAttckSession(MockSession[MockRequest, MockResponse, MitreAttckProduct]):
    """HTTP interceptor that routes all MITRE ATT&CK requests to the product mock."""

    def get_routed_functions(self) -> list[RouteFunction]:
        return [
            self.get_attack_data,
        ]

    @router.get(r".*/enterprise-attack\.json")
    def get_attack_data(self, _request: MockRequest) -> MockResponse:
        """Return the STIX bundle stored in the product mock.

        The manager calls ``session.get(api_root)`` where api_root is the full
        URL of the enterprise-attack JSON file.  The path always ends with
        ``enterprise-attack.json``, so we match on that suffix.
        """
        try:
            data = self._product.get_attack_data()
            return MockResponse(content=data, status_code=200)
        except Exception:
            return MockResponse(content={"error": "Simulated failure"}, status_code=500)
