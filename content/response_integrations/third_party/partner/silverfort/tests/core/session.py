"""Mock session for Silverfort integration tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from integration_testing import router  # type: ignore[import-not-found]
from integration_testing.common import get_request_payload  # type: ignore[import-not-found]
from integration_testing.request import MockRequest  # type: ignore[import-not-found]
from integration_testing.requests.response import MockResponse  # type: ignore[import-not-found]
from integration_testing.requests.session import (  # type: ignore[import-not-found]
    MockSession,
    Response,
    RouteFunction,
)

from silverfort.tests.core.product import MockSilverfort

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson  # type: ignore[import-not-found]


class SilverfortSession(MockSession[MockRequest, MockResponse, MockSilverfort]):
    """Mock session for Silverfort API requests."""

    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        """Get all routed functions for this session."""
        return [
            # Risk API
            self.get_entity_risk,
            self.update_entity_risk,
            # Service Account API
            self.get_service_account,
            self.list_service_accounts,
            self.get_sa_policy,
            self.update_sa_policy,
            # Policy API
            self.get_policy,
            self.list_policies,
            self.update_policy,
            self.change_policy_state,
            self.get_rules_names_and_ids,
        ]

    # Risk API routes
    @router.get(r"/v1/public/getEntityRisk")
    def get_entity_risk(self, request: MockRequest) -> MockResponse:
        """Handle get entity risk requests."""
        try:
            params: SingleJson = get_request_payload(request)
            user_principal_name = params.get("user_principal_name")
            resource_name = params.get("resource_name")

            result = self._product.get_entity_risk(user_principal_name, resource_name)
            return MockResponse(content=result, status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.post(r"/v1/public/updateEntityRisk")
    def update_entity_risk(self, request: MockRequest) -> MockResponse:
        """Handle update entity risk requests."""
        try:
            payload: SingleJson = get_request_payload(request)
            user_principal_name = payload.get("user_principal_name", "")
            risks = payload.get("risks", {})

            result = self._product.update_entity_risk(user_principal_name, risks)
            return MockResponse(content=result, status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    # Service Account API routes
    @router.get(r"/v1/public/serviceAccounts/[a-f0-9-]+$")
    def get_service_account(self, request: MockRequest) -> MockResponse:
        """Handle get service account requests."""
        try:
            guid = request.url.path.split("/")[-1]
            result = self._product.get_service_account(guid)
            return MockResponse(content=result, status_code=200)
        except ValueError as e:
            return MockResponse(content={"error": str(e)}, status_code=404)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.post(r"/v1/public/serviceAccounts/index")
    def list_service_accounts(self, request: MockRequest) -> MockResponse:
        """Handle list service accounts requests."""
        try:
            payload: SingleJson = get_request_payload(request)
            page_size = payload.get("page_size", 50)
            page_number = payload.get("page_number", 1)
            fields = payload.get("fields")

            result = self._product.list_service_accounts(page_size, page_number, fields)
            return MockResponse(content=result, status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.get(r"/v1/public/serviceAccounts/policy/[a-f0-9-]+")
    def get_sa_policy(self, request: MockRequest) -> MockResponse:
        """Handle get service account policy requests."""
        try:
            guid = request.url.path.split("/")[-1]
            result = self._product.get_sa_policy(guid)
            return MockResponse(content=result, status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.post(r"/v1/public/serviceAccounts/policy/[a-f0-9-]+")
    def update_sa_policy(self, request: MockRequest) -> MockResponse:
        """Handle update service account policy requests."""
        try:
            guid = request.url.path.split("/")[-1]
            payload: SingleJson = get_request_payload(request)

            result = self._product.update_sa_policy(guid, payload)
            return MockResponse(content=result, status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    # Policy API routes
    @router.get(r"/v2/public/policies/\d+")
    def get_policy(self, request: MockRequest) -> MockResponse:
        """Handle get policy requests."""
        try:
            policy_id = request.url.path.split("/")[-1]
            result = self._product.get_policy(policy_id)
            return MockResponse(content=result, status_code=200)
        except ValueError as e:
            return MockResponse(content={"error": str(e)}, status_code=404)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.post(r"/v2/public/policies/index")
    def list_policies(self, request: MockRequest) -> MockResponse:
        """Handle list policies requests."""
        try:
            payload: SingleJson = get_request_payload(request)
            fields = payload.get("fields")

            result = self._product.list_policies(fields)
            return MockResponse(content=result, status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.patch(r"/v2/public/policies/\d+")
    def update_policy(self, request: MockRequest) -> MockResponse:
        """Handle update policy requests."""
        try:
            policy_id = request.url.path.split("/")[-1]
            payload: SingleJson = get_request_payload(request)

            result = self._product.update_policy(policy_id, payload)
            return MockResponse(content=result, status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.post(r"/v1/public/changePolicyState")
    def change_policy_state(self, request: MockRequest) -> MockResponse:
        """Handle change policy state requests."""
        try:
            payload: SingleJson = get_request_payload(request)
            policy_id = payload.get("policy_id", "")
            state = payload.get("state", "").lower() == "true"

            result = self._product.change_policy_state(policy_id, state)
            return MockResponse(content=result, status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.get(r"/v1/public/getRulesNamesAndIds")
    def get_rules_names_and_ids(self, request: MockRequest) -> MockResponse:
        """Handle get rules names and IDs requests."""
        try:
            result = self._product.get_rules_names_and_ids()
            return MockResponse(content=result, status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)
