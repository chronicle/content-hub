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

from ...tests.core.google_gmail import (
    GoogleGmail
)
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class GoogleGmailSession(
    MockSession[MockRequest, MockResponse, GoogleGmail]
):

    def get_routed_functions(self) -> list[RouteFunction]:
        return [
            self.add_evidence,
            self.get_default_service_account,
            self.get_default_service_account_email,
            self.get_service_account_token,
            self.get_oauth_token,
            self.sign_blob_invalid,
            self.sign_blob
        ]

    @router.post("/api/external/v1/cases/AddEvidence/")
    def add_evidence(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={})

    @router.get("/computeMetadata/v1/instance/service-accounts/default/")
    def get_default_service_account(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content={
                "email": "default@domain.com",
                "scopes": ["test-scope"],
                "aliases": ["default"]
            },
            headers={
                "content-type": "application/json"
            }
        )

    @router.get("/computeMetadata/v1/instance/service-accounts/default/email")
    def get_default_service_account_email(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content="default@domain.com",
            headers={
                "content-type": "application/text"
            }
        )

    @router.get(
        r"/computeMetadata/v1/instance/service-accounts/\w+@[a-zA-Z]+\.com/token"
    )
    def get_service_account_token(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            {
                "access_token": "xxxx.yyyy",
                "expires_in": 3599,
                "token_type": "Bearer"
            },
            headers={
                "content-type": "application/json"
            }
        )

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

    @router.post(
        r"/v1/projects/-/serviceAccounts/invalid-sa@domain.com:signBlob"
    )
    def sign_blob_invalid(self, _: MockRequest) -> MockResponse:
        """Get an OAuth token with invalid email."""
        return MockResponse(
            content={
                "error": {
                    "code": 404,
                    "message": (
                        "Not found; Gaia id not found for email invalid-sa@domain.com"
                    ),
                    "status": "NOT_FOUND",
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.DebugInfo",
                            "detail": (
                                "Was unable to extract resource containers for Chemist "
                                "from the incoming request. Error message during "
                                "extraction: Not found; Gaia id not found for email "
                                "invalid-sa@domain.com"
                            )
                        }
                    ]
                }
            },
            status_code=404
        )

    @router.post(r"/v1/projects/-/serviceAccounts/(\w|-|@|\.)+:signBlob")
    def sign_blob(self, _: MockRequest) -> MockResponse:
        """Get an OAuth token"""
        return MockResponse(
            {
                "keyId": "xxxx",
                "signedBlob": "dG9rZW4=",
            }
        )
