from __future__ import annotations

from typing import Iterable

from integration_testing import router
from integration_testing.common import get_request_payload
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, Response, RouteFunction
from TIPCommon.types import SingleJson

from .product import PagerDuty


class PagerDutySession(MockSession[MockRequest, MockResponse, PagerDuty]):
    """Mock session for PagerDuty integration tests, handling routing."""

    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        """Get the list of routed functions."""
        return [
            self.list_incidents,
            self.test_connectivity,
            self.get_incident_by_key,
            self.list_users,
            self.snooze_incident,
            self.get_incident_by_id,
            self.resolve_incident_by_id,
            self.add_incident_note,
        ]

    @router.get(r"/incidents")
    def list_incidents(self, request: MockRequest) -> MockResponse:
        """Mock for listing incidents."""
        auth_header = request.headers.get("Authorization", "")
        if "invalid_key" in auth_header:
            return MockResponse(
                status_code=500, content={"error": {"message": "Internal Server Error"}}
            )
        params: SingleJson = get_request_payload(request)
        return MockResponse(content=self._product.get_incidents(params))

    @router.get(r"/abilities")
    def test_connectivity(self, request: MockRequest) -> MockResponse:
        """Mock for the connectivity test endpoint."""
        auth_header = request.headers.get("Authorization", "")
        if "invalid_key" in auth_header:
            return MockResponse(
                status_code=401, content={"error": {"message": "Unauthorized"}}
            )
        return MockResponse(content={"abilities": ["test_ability"]})

    @router.get(r"/incidents")
    def get_incident_by_key(self, request: MockRequest) -> MockResponse:
        """Mock for getting a single incident by key."""
        params: SingleJson = get_request_payload(request)
        incident_key = params.get("user_ids[]")
        if incident_key:
            filtered_incidents = [
                inc
                for inc in self._product.incidents.get("incidents", [])
                if inc.get("incident_key") == incident_key
            ]
            if filtered_incidents:
                return MockResponse(content={"incidents": filtered_incidents})
            else:
                return MockResponse(content={"incidents": []})

        return MockResponse(content=self._product.get_incidents(params))

    @router.get(r"/users")
    def list_users(self, request: MockRequest) -> MockResponse:
        """Mock for listing users."""
        auth_header = request.headers.get("Authorization", "")
        if "invalid_key" in auth_header:
            return MockResponse(
                status_code=401, content={"error": {"message": "Unauthorized"}}
            )
        return MockResponse(content=self._product.get_users())

    @router.post(r"/incidents/(?P<incident_id>[^/]+)/snooze")
    def snooze_incident(self, request: MockRequest) -> MockResponse:
        """Mock for snoozing an incident."""
        auth_header = request.headers.get("Authorization", "")
        from_header = request.headers.get("From", "")
        incident_id = request.url.path.split("/")[-2]

        if "invalid_key" in auth_header:
            return MockResponse(
                status_code=401, content={"error": {"message": "Unauthorized"}}
            )
        if not from_header:
            return MockResponse(
                status_code=400, content={"error": {"message": "Missing From header"}}
            )

        incident_exists = any(
            inc.get("id") == incident_id 
            for inc in self._product.incidents.get("incidents", [])
            )
        if not incident_exists:
            return MockResponse(
                status_code=404, content={"error": {"message": "Incident not found"}}
                )

        return MockResponse(content=self._product.snooze_incident(incident_id))

    @router.get(r"/incidents/(?P<incident_id>[^/]+)")
    def get_incident_by_id(self, request: MockRequest) -> MockResponse:
        """Mock for getting a single incident by ID."""
        incident_id = request.url.path.split("/")[-1]
        incident = self._product.get_incident(incident_id)
        if incident:
            return MockResponse(content={"incident": incident})
        return MockResponse(status_code=404, content={"error": {"message": "Incident not found"}})

    @router.put(r"/incidents/(?P<incident_id>[^/]+)")
    def resolve_incident_by_id(self, request: MockRequest) -> MockResponse:
        """Mock for resolving an incident."""
        incident_id = request.url.path.split("/")[-1]
        res = self._product.resolve_incident(incident_id)
        if res:
            return MockResponse(content=res)
        return MockResponse(status_code=404, content={"error": {"message": "Incident not found"}})

    @router.post(r"/incidents/(?P<incident_id>[^/]+)/notes")
    def add_incident_note(self, request: MockRequest) -> MockResponse:
        """Mock for adding a note to an incident."""
        incident_id = request.url.path.split("/")[-2]
        payload = get_request_payload(request)
        content = payload.get("note", {}).get("content", "")
        res = self._product.add_incident_note(incident_id, content)
        return MockResponse(content=res)
