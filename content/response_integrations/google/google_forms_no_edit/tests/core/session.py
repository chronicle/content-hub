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

from google_forms.core.datamodels import AlertResponse, FormResponse

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction

from google_forms.tests.core.product import GoogleForms


class GoogleFormsSession(MockSession[MockRequest, MockResponse, GoogleForms]):

    def get_routed_functions(self) -> list[RouteFunction]:
        return [
            self.get_forms,
            self.get_user,
            self.get_form_details,
            self.get_oauth_token,
            self.get_access_token,
        ]

    @router.get("/v1/forms/[a-zA-Z0-9]+/responses")
    def get_forms(self, _: MockRequest) -> MockResponse:
        """Route get_forms requests"""
        forms: list[AlertResponse] = self._product.get_forms()
        return MockResponse(content=forms)

    @router.get("/v1/forms/[a-zA-Z0-9]+")
    def get_form_details(self, _: MockRequest) -> MockResponse:
        """Route get_form_details"""
        details: FormResponse = self._product.get_form_details()
        return MockResponse(content=details.raw_data)

    @router.get("/admin/directory/v1/users")
    def get_user(self, _: MockRequest) -> MockResponse:
        """Route get_form_details"""
        users: dict = self._product.list_users()
        return MockResponse(content=users)

    @router.post("/token")
    def get_oauth_token(self, _: MockRequest) -> MockResponse:
        """Get an OAuth token"""
        return MockResponse(
            content={
                "access_token": "xxxx.yyyy",
                "expires_in": 3599,
                "token_type": "Bearer",
            }
        )

    @router.post(r"/v1/projects/-/serviceAccounts/(\w|-)+@([a-zA-Z]|-|\.)+com:signBlob")
    def get_access_token(self, _: MockRequest) -> MockResponse:
        """Mock get access token request."""
        return MockResponse(
            content={
                "keyId": "xxxxxxxxx",
                "signedBlob": "xxxxxxxxxxxxxxxxx",
            }
        )
