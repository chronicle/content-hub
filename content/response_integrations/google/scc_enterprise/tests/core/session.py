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

from scc_enterprise.tests.core.product import GoogleSecurityCommandCenter
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class GoogleSecurityCommandCenterSession(
    MockSession[MockRequest, MockResponse, GoogleSecurityCommandCenter]
):

    def get_routed_functions(self) -> list[RouteFunction]:
        return [
            self.get_sources,
            self.get_findings,
            self.patch_external_systems,
            self.get_oauth_token,
            self.add_config,
            self.delete_config,
            self.get_config,
            self.patch_config,
            self.get_default_service_account_email,
        ]

    @router.get(r"/v2/organizations/\d+/sources")
    def get_sources(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content={"sources": self._product.list_sources()}
        )

    @router.get(r"/v2/organizations/\d+/sources/-/locations/(\w|-)+/findings")
    def get_findings(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content={"listFindingsResults": self._product.list_findings()}
        )

    @router.patch(
        r"/v2/organizations/\d+/sources/\d+/locations/(\w|-)+/findings/(\w|-)+"
        r"/externalSystems"
    )
    def patch_external_systems(self, _: MockRequest) -> MockResponse:
        """Patch external systems object."""
        return MockResponse(content={})

    @router.post(r"/v2/organizations/\d+/locations/(\w|-)+/notificationConfigs")
    def add_config(self, request: MockRequest) -> MockResponse:
        """Add notifications config."""
        config_name: str = request.url.query.split("configId=")[-1]
        self._product.add_notifications_config(
            config_name=config_name,
            config_json=request.kwargs["json"]
        )
        return MockResponse(content=request.kwargs["json"])

    @router.get(r"/v2/organizations/\d+/locations/(\w|-)+/notificationConfigs/(\w|-)+")
    def get_config(self, request: MockRequest) -> MockResponse:
        """Get notifications config."""
        config_name: str = request.url.path.split("/")[-1]
        config = self._product.get_notifications_config(
           config_name=config_name
        )
        if config is not None:
            config.update({
                "name": request.url.path.split("v2/")[-1]
            })
            return MockResponse(content=config)

        return MockResponse(status_code=404)

    @router.patch(
        r"/v2/organizations/\d+/locations/(\w|-)+/notificationConfigs/(\w|-)+"
    )
    def patch_config(self, request: MockRequest) -> MockResponse:
        """Patch notifications config."""
        config_name: str = request.url.path.split("/")[-1]
        config = self._product.update_notifications_config(
            config_name=config_name,
            config_json=request.kwargs["json"]
        )
        if config is not None:
            config.update({
                "name": request.url.path.split("v2/")[-1]
            })
            return MockResponse(content=config)

        return MockResponse(status_code=404)

    @router.delete(r"/v1/organizations/\d+/notificationConfigs/(\w|-)+")
    def delete_config(self, _: MockRequest) -> MockResponse:
        return MockResponse(status_code=404)

    @router.post("/token")
    def get_oauth_token(self, request: MockRequest) -> MockResponse:
        """Get an OAuth token"""
        if (
            not isinstance(request.kwargs["data"], bytes)
            and "raise_error" in request.kwargs["data"].values()
        ):
            return MockResponse(
                content={
                    "error": "invalid_grant",
                    "error_description": "Invalid grant: account not found"
                },
                status_code=400,
            )

        return MockResponse(
            {
                "access_token": "xxxx.yyyy",
                "expires_in": 3599,
                "token_type": "Bearer"
            }
        )

    @router.get("/computeMetadata/v1/instance/service-accounts/default/email")
    def get_default_service_account_email(
        self,
        request: MockRequest,
        **_kwargs,
    ) -> MockResponse:
        return MockResponse(content="mock-sa@example.iam.gserviceaccount.com")
