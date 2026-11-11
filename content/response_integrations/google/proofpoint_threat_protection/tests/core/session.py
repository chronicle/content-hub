from __future__ import annotations

from collections.abc import Iterable

from TIPCommon.types import SingleJson
from proofpoint_threat_protection.tests.common import (
    OAUTH_TOKEN_JSON,
)
from proofpoint_threat_protection.tests.core.product import (
    ProofpointThreatProtection,
)
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class ProofpointThreatProtectionSession(
    MockSession[MockRequest, MockResponse, ProofpointThreatProtection]
):
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            get_oauth_token,
            self.get_allow_list_entries_handler,
            self.add_allow_list_entry_handler,
            self.add_block_list_entry_handler,
            self.get_block_list_entries_handler,
        ]

    @router.get(".*/api/v1/emailProtection/modules/spam/orgSafeList")
    def get_allow_list_entries_handler(self, request: MockRequest) -> MockResponse:
        """Handle get allow list entries requests."""
        _ = request
        entries: list[SingleJson] = self._product.get_allow_list_entries()
        return MockResponse(
            status_code=200,
            content={"entries": entries},
        )

    @router.post(".*/api/v1/emailProtection/modules/spam/orgSafeList")
    def add_allow_list_entry_handler(self, request: MockRequest) -> MockResponse:
        """Handle add allow list entry requests."""
        cluster_id: str | None = request.kwargs.get("params", {}).get("clusterId")
        if cluster_id == "invalid_cluster":
            return MockResponse(
                status_code=403,
                content={"errorMessage": "Invalid cluster ID"},
            )
        payload: SingleJson = request.kwargs.get("json", {})

        if payload.get("action") == "delete":
            if not self._product.remove_allow_list_entry(payload):
                return MockResponse(
                    status_code=400,
                    content={
                        "errorCode": 400,
                        "errorMessage": "error.api.emailprotection.lists.invalid.entry",
                    },
                )
        elif payload.get("action") == "add":
            if not self._product.add_allow_list_entries([payload]):
                return MockResponse(
                    status_code=500,
                    content={"errorMessage": "Internal Server Error"},
                )
        return MockResponse(
            status_code=200,
        )

    @router.post(".*/api/v1/emailProtection/modules/spam/orgBlockList")
    def add_block_list_entry_handler(self, request: MockRequest) -> MockResponse:
        """Handle add block list entry requests."""
        cluster_id: str | None = request.kwargs.get("params", {}).get("clusterId")
        if cluster_id == "invalid_cluster":
            return MockResponse(
                status_code=403,
                content={"errorMessage": "Invalid cluster ID"},
            )

        payload: SingleJson = request.kwargs.get("json", {})
        if payload.get("action") == "delete":
            if not self._product.remove_block_list_entry(payload):
                return MockResponse(
                    status_code=400,
                    content={
                        "errorCode": 400,
                        "errorMessage": "error.api.emailprotection.lists.invalid.entry",
                    },
                )
        elif payload.get("action") == "add":
            if not self._product.add_block_list_entries([payload]):
                return MockResponse(
                    status_code=500,
                    content={"errorMessage": "Internal Server Error"},
                )

        return MockResponse(
            status_code=200,
        )

    @router.get(".*/api/v1/emailProtection/modules/spam/orgBlockList")
    def get_block_list_entries_handler(self, request: MockRequest) -> MockResponse:
        """Handle get block list entries requests."""
        _ = request
        entries: list[SingleJson] = self._product.get_block_list_entries()
        return MockResponse(
            status_code=200,
            content={"entries": entries},
        )


@router.post("/v1/token")
def get_oauth_token(request: MockRequest) -> MockResponse:
    """Get an OAuth token"""
    if request.kwargs.get("data", {}).get("client_secret") == "invalid client secret":
        return MockResponse(
            content={
                "error": {
                    "message": (
                        "Failed to authenticate to Proofpoint Cloud Threat " "Response"
                    ),
                    "errors": [{"errorMessage": "Wrong Credentials!"}],
                }
            },
            status_code=400,
        )

    return MockResponse(OAUTH_TOKEN_JSON)
