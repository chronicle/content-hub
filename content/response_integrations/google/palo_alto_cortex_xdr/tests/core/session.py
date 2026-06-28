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

from TIPCommon.data_models import CaseDataStatus, CasePriority, SLA
from TIPCommon.types import SingleJson
from palo_alto_cortex_xdr.core.datamodels import (
    IncidentInfo,
    IncidentExtraData,
)

from palo_alto_cortex_xdr.tests import common
from palo_alto_cortex_xdr.tests.core.product import PaloAltoCortexXDR
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class PaloAltoCortexXDRSession(
    MockSession[MockRequest, MockResponse, PaloAltoCortexXDR],
):
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            self.get_incident,
            self.get_incidents,
            self.add_comment_to_incident,
            self.ping,
            self.start_xql_query,
            self.get_xql_query_results,
            self.get_endpoint,
            self.scan_endpoints,
            self.get_action_status,
        ]

    @router.post(r".*/public_api/v1/incidents/get_incident_extra_data/?")
    def get_incident(self, request: MockRequest) -> MockResponse:
        """Handle GET .*/public_api/v1/incidents/get_incident_extra_data requests"""
        incident_id: str = (
            request.kwargs.get("json", {})
            .get("request_data", "")
            .get("incident_id", "")
        )
        if int(incident_id) == common.CONNECTOR_INCIDENT_ID:
            extra_data: IncidentExtraData = self._product.get_incident_extra_data()
            response_json: SingleJson = {"reply": extra_data.to_json()}

            return MockResponse(content=response_json, status_code=200)

        if int(incident_id) == common.INVALID_INCIDENT_ID:
            return MockResponse(content=common.INVALID_INCIDENT, status_code=400)

        incident = self._product.get_incident(incident_id)

        return MockResponse(
            content={"reply": incident.to_json()}, status_code=200
        )

    @router.post(r".*/public_api/v1/incidents/update_incident/")
    def add_comment_to_incident(self, request: MockRequest) -> MockResponse:
        """Handle POST requests for adding a comment to an incident.
        This mock requests to the .*/public_api/v1/incidents/update_incident/ endpoint.
        """
        request_data = request.kwargs.get("json", {}).get("request_data", {})
        incident_id: str = request_data.get("incident_id", "")

        if int(incident_id) == common.INVALID_INCIDENT_ID:
            return MockResponse(content=common.INVALID_INCIDENT, status_code=404)

        return MockResponse(content={"reply": True}, status_code=200)

    @router.post(r"/api_keys/validate/")
    def ping(self, request: MockRequest) -> MockResponse:
        """Handle POST /api_keys/validate/ requests"""
        api_key_id = request.kwargs.get("headers", {}).get("x-xdr-auth-id")
        if api_key_id is not None and int(api_key_id) == common.INVALID_API_KEY_ID:
            return MockResponse(content=common.INVALID_TOKEN, status_code=401)

        return MockResponse(content={"reply": {"valid": True}}, status_code=200)

    @router.post(r".*/public_api/v1/xql/start_xql_query")
    def start_xql_query(self, _: MockRequest) -> MockResponse:
        """Handle POST .*/public_api/v1/xql/start_xql_query requests"""
        return MockResponse(
            content={"reply": common.EXECUTE_XQL_SEARCH.to_json()}, status_code=200
        )

    @router.post(r".*/public_api/v1/xql/get_query_results")
    def get_xql_query_results(self, request: MockRequest) -> MockResponse:
        """Handle POST .*/public_api/v1/xql/get_xql_query_results requests"""
        query_id: str = (
            request.kwargs.get("json", {}).get("request_data", {}).get("query_id", "")
        )
        if query_id == common.INVALID_INCIDENT_ID:
            return MockResponse(content=common.INVALID_INCIDENT, status_code=400)

        return MockResponse(
            content={"reply": common.EXECUTE_XQL_SEARCH_RESULT.to_json()},
            status_code=200,
        )

    @router.post(r".*/public_api/v1/endpoints/get_endpoint/")
    def get_endpoint(self, request: MockRequest) -> MockResponse:
        """Handle POST .*/public_api/v1/endpoints/get_endpoint/ requests"""
        filters = request.kwargs.get(
            "json", {}).get("request_data", {}).get("filters", [])
        endpoint = None

        for f in filters:
            if f["field"] == "ip_list":
                ip = f["value"][0]
                endpoint = self._product.get_endpoint_by_ip(ip)
            elif f["field"] == "hostname":
                hostname = f["value"][0]
                endpoint = self._product.get_endpoint_by_hostname(hostname)

        if endpoint:
            return MockResponse(
                content={"reply": {"endpoints": [endpoint]}}, status_code=200
            )

        return MockResponse(content={"reply": {"endpoints": []}}, status_code=200)

    @router.post(r".*/public_api/v1/endpoints/scan/")
    def scan_endpoints(self, request: MockRequest) -> MockResponse:
        """Handle POST .*/public_api/v1/endpoints/scan/ requests"""
        request_data = request.kwargs.get("json", {}).get("request_data", {})
        filters = request_data.get("filters", [])
        endpoint_ids = []
        for f in filters:
            if f["field"] == "endpoint_id_list":
                endpoint_ids = f["value"]

        action_id = self._product.add_scan(endpoint_ids)

        return MockResponse(
            content={
                "reply": {
                    "action_id": action_id,
                    "endpoints_count": len(endpoint_ids),
                }
            },
            status_code=200,
        )

    @router.post(r".*/public_api/v1/actions/get_action_status/")
    def get_action_status(self, request: MockRequest) -> MockResponse:
        """Handle POST .*/public_api/v1/actions/get_action_status/ requests"""
        request_data = request.kwargs.get("json", {}).get("request_data", {})
        action_id = request_data.get("group_action_id")

        status = self._product.get_scan_status(action_id)

        if status:
            return MockResponse(content={"reply": status}, status_code=200)

        return MockResponse(content={"reply": {}}, status_code=200)

    @router.post(r".*/public_api/v1/incidents/get_incidents/")
    def get_incidents(self, _: MockRequest) -> MockResponse:
        """Handle POST .*/public_api/v1/incidents/get_incidents/ requests"""
        incidents: list[IncidentInfo] = self._product.get_incidents()
        response_json: SingleJson = {
            "reply": {
                "total_count": len(incidents),
                "result_count": len(incidents),
                "incidents": [incident.to_json() for incident in incidents],
            }
        }

        return MockResponse(content=response_json, status_code=200)


class PaloAltoCortexXDRSOARSession(
    MockSession[MockRequest, MockResponse, PaloAltoCortexXDR],
):
    """PaloAltoCortexXDRSOARSession for Chronicle SOAR API mocks."""
    def __init__(self, product: PaloAltoCortexXDR):
        super().__init__(product)
        self.request_history = []

    def get_routed_functions(self) -> list[RouteFunction]:
        """Returns a list of all routed functions for the mock SOAR session."""
        return [
            self.get_case_overview_details,
        ]

    @router.get(r"/api/external/v1/dynamic-cases/GetCaseDetails/[^/]+")
    def get_case_overview_details(self, request: MockRequest) -> MockResponse:
        """Mocks the SOAR API for fetching case details."""
        case_id = request.url.path.split("/")[-1]

        case_object = self._product.get_case_overview_details(case_id)

        if isinstance(case_object.priority, int):
            case_object.priority = CasePriority(case_object.priority)

        if isinstance(case_object.status, int):
            case_object.status = CaseDataStatus(case_object.status)

        for sla_field in ("sla", "stage_sla", "alerts_sla"):
            if not isinstance(getattr(case_object, sla_field, None), SLA):
                setattr(case_object, sla_field, SLA.from_json({}))

        return MockResponse(content=case_object.to_json(), status_code=200)
