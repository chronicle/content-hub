from __future__ import annotations

import json
from typing import Iterable

from integration_testing import router
from integration_testing.common import get_request_payload
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, Response, RouteFunction
from TIPCommon.types import SingleJson

from rubrik_security_cloud.tests.core.product import RubrikSecurityCloud


class RubrikSession(MockSession[MockRequest, MockResponse, RubrikSecurityCloud]):
    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        return [
            self.graphql_endpoint,
            self.token_endpoint,
        ]

    @router.post(r"/api/graphql")
    def graphql_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            payload: SingleJson = get_request_payload(request)

            # If get_request_payload didn't work, try to get data from kwargs
            if not payload and hasattr(request, "kwargs") and request.kwargs:
                if "data" in request.kwargs:
                    data_str = request.kwargs["data"]
                    payload = json.loads(data_str) if isinstance(data_str, str) else data_str
                elif "json" in request.kwargs:
                    payload = request.kwargs["json"]

            if not payload:
                return MockResponse(
                    content={"errors": [{"message": "Empty payload"}]}, status_code=400
                )

            query = payload.get("query", "")

            if "deploymentVersion" in query:
                return MockResponse(content=self._product.get_deployment_version(), status_code=200)
            elif "clusterConnection" in query and "geoLocation" in query:
                return MockResponse(
                    content=self._product.get_cdm_cluster_location(), status_code=200
                )
            elif "clusterConnection" in query and "connectionStatus" in query:
                return MockResponse(
                    content=self._product.get_cdm_cluster_connection_state(), status_code=200
                )
            elif "policyObjs" in query:
                return MockResponse(
                    content=self._product.get_sonar_policy_objects_list(), status_code=200
                )
            elif "policyObj" in query:
                return MockResponse(
                    content=self._product.get_sonar_object_detail(), status_code=200
                )
            elif "threatHuntDetailV2" in query or "threatHuntObjectMetrics" in query:
                return MockResponse(content=self._product.get_ioc_scan_results(), status_code=200)
            elif "startTurboThreatHunt" in query:
                return MockResponse(content=self._product.get_turbo_ioc_scan(), status_code=200)
            elif "activitySeriesConnection" in query:
                return MockResponse(content=self._product.get_list_events(), status_code=200)
            elif "snappableConnection" in query and "snapshotConnection" in query:
                return MockResponse(
                    content=self._product.get_list_object_snapshots(), status_code=200
                )
            elif "snapshotFilesDelta" in query:
                return MockResponse(
                    content=self._product.get_list_sonar_file_contexts(), status_code=200
                )
            elif "startBulkThreatHunt" in query:
                return MockResponse(content=self._product.get_advanced_ioc_scan(), status_code=200)

            return MockResponse(content={"data": {}}, status_code=200)
        except Exception as e:
            return MockResponse(content={"errors": [{"message": str(e)}]}, status_code=400)

    @router.post(r"/api/client_token")
    def token_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            token_data = self._product.get_token()
            return MockResponse(content=token_data, status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=401)
