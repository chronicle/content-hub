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

import pathlib
from collections.abc import Iterable

from ...tests import common
from ...tests.core.product import Zerofox
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class ZerofoxSession(MockSession[MockRequest, MockResponse, Zerofox]):
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            self.get_alerts,
            self.add_note_to_alert,
            self.close_alert,
            self.request_takedown,
            self.add_evidence_to_alert,
        ]

    @router.get(r".*/1.0/alerts/")
    def get_alerts(self, _: MockRequest) -> MockResponse:
        """Handle GET .*/1.0/alerts/ requests"""
        alerts = self._product.get_alerts()
        if alerts["alerts"][0]["id"] == common.INVALID_ALERT_ID:
            return MockResponse(content=common.INVALID_TOKEN, status_code=401)

        return MockResponse(content=alerts)

    @router.post(r".*/1.0/alerts/[0-9]+/append_notes/")
    def add_note_to_alert(self, request: MockRequest) -> MockResponse:
        """Handle POST .*/1.0/alerts/[0-9]+/append_notes/ requests"""
        alert_id = request.url.path.split("/")[-3]
        if alert_id == str(common.INVALID_ALERT_ID):
            return MockResponse(content=common.INVALID_ALERT, status_code=403)

        note = request.kwargs["json"]["notes"]
        self._product.add_note_to_alert(int(alert_id), note)

        return MockResponse(content={"notes": "Test Note"}, status_code=200)

    @router.post(r".*/1.0/alerts/[0-9]+/close/")
    def close_alert(self, request: MockRequest) -> MockResponse:
        """Handle POST .*/1.0/alerts/[0-9]+/close/ requests"""
        alert_id = request.url.path.split("/")[-3]
        if alert_id == str(common.INVALID_ALERT_ID):
            return MockResponse(content=common.INVALID_CLOSE_ALERT, status_code=403)
        self._product.get_alert(int(alert_id))["close"] = True

        return MockResponse(content="", status_code=200)

    @router.post(r".*/1.0/alerts/[0-9]+/request_takedown/")
    def request_takedown(self, request: MockRequest) -> MockResponse:
        """Handle POST .*/1.0/alerts/[0-9]+/request_takedown/ requests"""
        alert_id = request.url.path.split("/")[-3]
        if alert_id == str(common.INVALID_ALERT_ID):
            return MockResponse(content=common.INVALID_CLOSE_ALERT, status_code=403)
        self._product.get_alert(int(alert_id))["takedown"] = True

        return MockResponse(content="", status_code=200)

    @router.post(r".*/1.0/alerts/[0-9]+/attachments/")
    def add_evidence_to_alert(self, request: MockRequest) -> MockResponse:
        """Handle POST .*/1.0/alerts/[0-9]+/attachments/ requests"""
        alert_id = request.url.path.split("/")[-3]
        if alert_id == str(common.INVALID_ALERT_ID):
            return MockResponse(content=common.INVALID_ALERT, status_code=403)
        evidence = request.kwargs["files"]["file"]
        self._product.add_evidence_to_alert(int(alert_id), evidence)

        return MockResponse(content={}, status_code=201)
