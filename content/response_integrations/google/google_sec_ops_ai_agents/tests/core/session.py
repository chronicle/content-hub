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
import re
from typing import Iterable, TYPE_CHECKING
from google_sec_ops_ai_agents.tests.mocks.siemplify.common import FULL_ALERT_DATA
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction

if TYPE_CHECKING:
  from google_sec_ops_ai_agents.tests.core.product import (
      GoogleSecOpsAiAgents,
  )

INVESTIGATION_REGEX = r".*/investigations/([a-zA-Z0-9_-]+)"


class GoogleSecOpsAiAgentsSession(
    MockSession[MockRequest, MockResponse, "GoogleSecOpsAiAgents"]
):
  """GoogleSecOpsAiAgents mock session"""

  def get_routed_functions(self) -> Iterable[RouteFunction]:
    return [
        self.list_investigations,
        self.trigger_investigation,
        self.get_investigation_status,
        self.get_full_details,
    ]

  @router.get(".*/investigations")
  def list_investigations(self, request: MockRequest) -> MockResponse:
    """Route list_investigations requests"""
    if request.kwargs and "params" in request.kwargs:
      params = request.kwargs["params"]
      if "filter" in params:
        try:
          alert_id = params["filter"].split("'")[1]
          investigations = self._product.get_investigations(alert_id)
          return MockResponse(content={"investigations": investigations})
        except (IndexError, AttributeError):
          pass

    return MockResponse(content={"investigations": []})

  @router.post(".*/investigations:trigger")
  def trigger_investigation(self, request: MockRequest) -> MockResponse:
    """Route trigger_investigation requests"""
    alert_id = request.kwargs.get("json", {}).get("alertId")
    if alert_id:
      investigation = self._product.trigger_investigation(alert_id)
      return MockResponse(content=investigation)
    return MockResponse(content={}, status_code=400)

  @router.get(INVESTIGATION_REGEX)
  def get_investigation_status(self, request: MockRequest) -> MockResponse:
    """Route get_investigation_status requests"""
    match = re.search(INVESTIGATION_REGEX, request.url.path)
    if match:
      investigation_name = match.group(1)
      status = self._product.get_investigation_status("investigations/" + investigation_name)
      if status:
        return MockResponse(content=status)
    return MockResponse(content={}, status_code=404)

  @router.post("/api/external/v1/sdk/AlertFullDetails")
  def get_full_details(self, _: MockRequest) -> MockResponse:
    FULL_ALERT_DATA["additional_properties"]["SiemAlertId"] = "alert-123"
    return MockResponse(content=FULL_ALERT_DATA)
