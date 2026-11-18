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

import datetime
import dataclasses
import pathlib

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import (
    MockSession,
    RouteFunction,
)
from integration_testing.common import get_def_file_content

MOCK_DATA_PATH = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA = get_def_file_content(MOCK_DATA_PATH)


@dataclasses.dataclass(frozen=True)
class HistoryRecord:
    __slots__ = ("request", "response")

    request: MockRequest
    response: MockResponse


class HistoryRecordsList(list[HistoryRecord]):
    def __init__(self, *history_records: HistoryRecord):
        super().__init__(history_records)

    def __copy__(self):
        return HistoryRecordsList(*self)

    def __getitem__(self, subscript) -> HistoryRecordsList | HistoryRecord:
        result = super().__getitem__(subscript)
        if isinstance(subscript, slice):
            return HistoryRecordsList(*result)
        return result

    def assert_url_path(
        self,
        path: str,
        netloc: str,
    ) -> None:
        """
        Assert that the request history contains a request with
        the given path and netloc.
        """

        assert any(hr.request.url.path == path for hr in self)
        assert any(hr.request.url.netloc == netloc for hr in self)

    def assert_data(
        self, fields_to_check: dict[str : str | int], request_idx: int = -1
    ) -> None:
        """
        Assert that the data in the request matches the expected values.

        Args:
            fields_to_check: A dictionary of field names and expected values.
            request_idx: The index of the request to check.
        Returns:
            None
        """
        for key, expected_value in fields_to_check.items():
            assert (
                self[request_idx].request.kwargs.get("json").get(key) == expected_value
            )


class GoogleCloudApiSession(MockSession[MockRequest, MockResponse, None]):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.request_history: HistoryRecordsList[HistoryRecord] = HistoryRecordsList()

    def get_routed_functions(self) -> list[RouteFunction]:
        return [
            self.get_from_project,
            self.get_default_service_account,
            self.get_default_service_account_email,
            self.get_service_account_token,
            self.get_access_token_invalid,
            self.get_access_token,
            self.get_oauth_token,
        ]

    @router.post(r"/v2/entries:list")
    def get_from_project(self, _: MockRequest) -> MockResponse:
        return MockResponse(**MOCK_DATA["get_from_project"])

    @router.get("/computeMetadata/v1/instance/service-accounts/default/")
    def get_default_service_account(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content={
                "email": "default@domain.com",
                "scopes": ["test-scope"],
                "aliases": ["default"],
            },
            headers={"content-type": "application/json"},
        )

    @router.get("/computeMetadata/v1/instance/service-accounts/default/email")
    def get_default_service_account_email(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content="default@domain.com",
            headers={"content-type": "text/plain"},
        )

    @router.get(
        r"/computeMetadata/v1/instance/service-accounts/\w+@[a-zA-Z]+\.com/token"
    )
    def get_service_account_token(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            {"access_token": "xxxx.yyyy", "expires_in": 3599, "token_type": "Bearer"},
            headers={"content-type": "application/json"},
        )

    @router.post(
        r"/v1/projects/-/serviceAccounts/invalid-sa@domain.com:generateAccessToken"
    )
    def get_access_token_invalid(self, _: MockRequest) -> MockResponse:
        return MockResponse(**MOCK_DATA["get_access_token_invalid"])

    @router.post(
        r"/v1/projects/-/serviceAccounts/\w+@[a-zA-Z]+\.com:generateAccessToken"
    )
    def get_access_token(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content={
                "accessToken": "xxxx.yyyy",
                "expireTime": (
                    datetime.datetime.now() + datetime.timedelta(seconds=3600)
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )

    @router.post("/token")
    def get_oauth_token(self, _: MockRequest) -> MockResponse:
        """Get an OAuth token"""
        return MockResponse(
            {"access_token": "xxxx.yyyy", "expires_in": 3599, "token_type": "Bearer"}
        )
