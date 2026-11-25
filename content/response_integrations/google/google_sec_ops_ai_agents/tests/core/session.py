from __future__ import annotations
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
        self.list_remediation_plans,
        self.generate_remediation_plan,
        self.list_remediation_action_executions,
        self.get_remediation_plan,
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

  @router.get(r".*/remediationPlans")
  def list_remediation_plans(self, request: MockRequest) -> MockResponse:
    """Route list_remediation_plans requests"""
    if request.kwargs and "params" in request.kwargs:
      params = request.kwargs["params"]
      if "filter" in params:
        match = re.search(r'["\']([^"\']+)["\']', params["filter"])
        if match:
          alert_id = match.group(1)
          plans = self._product.get_remediation_plans(alert_id)
          return MockResponse(
              content={"remediation_plans": plans, "remediationPlans": plans}
          )
    return MockResponse(content={"remediation_plans": [], "remediationPlans": []})

  @router.post(r".*/remediationPlans(?:/|:):?generate")
  def generate_remediation_plan(self, request: MockRequest) -> MockResponse:
    """Route generate_remediation_plan requests"""
    body = request.kwargs.get("json", {})
    alert_id = (
        body.get("siemAlertId")
        or body.get("siem_alert_id")
        or body.get("alertId")
        or body.get("alert_id")
    )
    if alert_id:
      plan = self._product.get_generated_remediation_plan(alert_id)
      if plan:
        return MockResponse(content=plan)
    return MockResponse(content={}, status_code=400)

  @router.get(r".*/remediationPlans/[^/]+/remediationActions/-/remediationActionExecutions")
  def list_remediation_action_executions(self, request: MockRequest) -> MockResponse:
    """Route list_remediation_action_executions requests"""
    match = re.search(
        r".*/remediationPlans/([^/]+)/remediationActions/-/remediationActionExecutions",
        request.url.path,
    )
    if match:
      plan_id = match.group(1)
      executions = self._product.get_remediation_action_executions(plan_id)
      return MockResponse(
          content={
              "remediation_action_executions": executions,
              "remediationActionExecutions": executions,
          }
      )
    return MockResponse(
        content={
            "remediation_action_executions": [],
            "remediationActionExecutions": [],
        }
    )

  @router.get(r".*/remediationPlans/[^/:]+")
  def get_remediation_plan(self, request: MockRequest) -> MockResponse:
    """Route get_remediation_plan requests"""
    match = re.search(r".*/remediationPlans/([^/:]+)", request.url.path)
    if match:
      plan_id = match.group(1)
      plan = self._product.get_remediation_plan_details(plan_id)
      if plan:
        return MockResponse(content=plan)
    return MockResponse(content={}, status_code=404)

  @router.post("/api/external/v1/sdk/AlertFullDetails")
  def get_full_details(self, _: MockRequest) -> MockResponse:
    FULL_ALERT_DATA["additional_properties"]["SiemAlertId"] = "alert-123"
    return MockResponse(content=FULL_ALERT_DATA)
