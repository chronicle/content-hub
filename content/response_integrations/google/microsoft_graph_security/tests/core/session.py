from __future__ import annotations

from TIPCommon.types import SingleJson

from core.datamodels import Incident
from tests.core.microsoft_graph_security import (
    MicrosoftGraphSecurity
)
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class MicrosoftGraphSecuritySession(
    MockSession[MockRequest, MockResponse, MicrosoftGraphSecurity]
):

    def get_routed_functions(self) -> list[RouteFunction]:
        return [
            self.add_comment_to_alert,
            self.get_incident,
            self.list_incidents,
            get_oauth_token,
        ]

    @router.post("/v1.0/security/alerts_v2/[a-zA-Z0-9-]+/comments")
    def add_comment_to_alert(self, request: MockRequest) -> MockResponse:
        """Adds a comment to an alert."""
        alert_id: str = request.url.path.split("/")[-2]
        parameters: SingleJson = request.kwargs["json"]
        comment: str = parameters.get("comment", "")
        return MockResponse(
            content={
                "@odata.context": f"{alert_id}",
                "value": [{
                    "comment": f"{comment}",
                    "createdByDisplayName": "MS Graph Mail",
                    "createdDateTime": "2024-11-15T08:34:52.8251214Z"
                }]
            },
            status_code=200,
        )

    @router.get("/v1.0/security/incidents/[a-zA-Z0-9-]+")
    def get_incident(self, request: MockRequest) -> MockResponse:
        """Get an incident from Microsoft Graph Security."""
        incident_id: str = request.url.path.split("/")[-1]
        incident: Incident = self._product.get_incident(incident_id)
        return MockResponse(content=incident.to_json())

    @router.get("/v1.0/security/incidents")
    def list_incidents(self, _) -> MockResponse:
        """Get incidents from Microsoft Graph Security."""
        incidents: Incident = self._product.list_incidents()
        return MockResponse(
            content={"value": [incident.to_json() for incident in incidents]}
        )


@router.post("/[a-zA-Z0-9]+/oauth2/v2.0/token")
def get_oauth_token(request: MockRequest) -> MockResponse:
    """Get an OAuth token"""
    if "raise_error" in request.kwargs["data"].values():
        return MockResponse(
            content={
                "message": "Failed to authenticate to MicrosoftGraphSecurity",
                "errors": [{"errorMessage": "Wrong Credentials!"}],
            },
            status_code=400,
        )

    return MockResponse(
        content={
            "access_token": "1000.ac445cfb678764b9da88ac5024b767c5.ac445cfb6724b76",
            "expires_in": 999_999_999_999,
            "token_type": "Bearer",
            "ext_expires_in": 999_999_999_999,
        },
        headers={"content-type": "application/json"}
    )
