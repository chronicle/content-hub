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
from ...tests.core.google_gmail import (
    GoogleGmail
)
from integration_testing import router
from integration_testing.aiohttp.response import MockClientResponse
from integration_testing.aiohttp.session import MockClientSession, RouteFunction
from integration_testing.request import MockRequest


class GoogleGmailAsyncSession(MockClientSession):

    def get_routed_functions(self) -> list[RouteFunction]:
        return [
            self.list_labels,
            self.create_label,
            self.get_attachment,
            self.trash_email,
            self.delete_email,
            self.get_message,
            self.get_thread,
            self.list_messages_invalid_mailbox,
            self.list_messages,
            self.get_oauth_token,
            self.send_email,
            self.batch_modify,
        ]

    @router.post(r"/gmail/v1/users/(\w+)@([a-zA-Z]+\.[a-zA-Z]+)/labels")
    def create_label(self, _: MockRequest) -> MockClientResponse:
        return MockClientResponse(
            content=self._product.list_labels()[-1]
        )

    @router.get(r"/gmail/v1/users/(\w+)@([a-zA-Z]+\.[a-zA-Z]+)/labels")
    def list_labels(self, _: MockRequest) -> MockClientResponse:
        return MockClientResponse(
            content={
                "labels": self._product.list_labels()
            }
        )

    @router.get(
        r"/gmail/v1/users/(\w+)@([a-zA-Z]+\.[a-zA-Z]+)/messages/\w{16}/attachments/\w+"
    )
    def get_attachment(self, request: MockRequest) -> MockClientResponse:
        """Mock get attachment request."""
        attachment_id = request.url.path.split("/")[-1]
        return MockClientResponse(
            content=self._product.get_attachment(attachment_id)
        )

    @router.get(r"/gmail/v1/users/(\w+)@([a-zA-Z]+\.[a-zA-Z]+)/messages/\w{16}")
    def get_message(self, request: MockRequest) -> MockClientResponse:
        message_id = request.url.path.split("/")[-1]
        return MockClientResponse(
            content=self._product.get_message(message_id)
        )

    @router.get(r"/gmail/v1/users/(\w+)@([a-zA-Z]+\.[a-zA-Z]+)/threads/\w{16}")
    def get_thread(self, request: MockRequest) -> MockClientResponse:
        message_id = request.url.path.split("/")[-1]
        return MockClientResponse(
            content=self._product.get_thread(message_id)
        )

    @router.post(
        r"/gmail/v1/users/(\w+)@([a-zA-Z]+\.[a-zA-Z]+)/messages/\w{16}/trash"
    )
    def trash_email(self, _: MockRequest) -> MockClientResponse:
        return MockClientResponse()

    @router.delete(
        r"/gmail/v1/users/(\w+)@([a-zA-Z]+\.[a-zA-Z]+)/messages/\w{16}"
    )
    def delete_email(self, _: MockRequest) -> MockClientResponse:
        return MockClientResponse(status_code=204)

    @router.get(r"/gmail/v1/users/invalid@mailbox.com/messages")
    def list_messages_invalid_mailbox(self, _: MockRequest) -> MockClientResponse:
        return MockClientResponse(
            content={"error": {"status": "NOT_FOUND"}},
            status_code=403
        )

    @router.get(r"/gmail/v1/users/(\w+)@([a-zA-Z]+\.[a-zA-Z]+)/messages")
    def list_messages(self, request: MockRequest) -> MockClientResponse:
        """Mock list messages request."""
        query = request.kwargs["params"]["q"]
        filter_params = query.split(" ")

        def _extract_param(param_name: str):
            return next(
                filter(
                    lambda param: f"{param_name}:" in param,
                    filter_params
                ),
                ""
            ).replace(f"{param_name}:", "")

        after_ts = _extract_param("after")
        before_ts = _extract_param("before")
        message_id = _extract_param("rfc822msgid")

        return MockClientResponse(
            content={
                "messages": [
                    {
                        "id": message["id"],
                        "threadId": message["threadId"]
                    }
                    for message in self._product.list_messages(
                        after_ts,
                        before_ts,
                        message_id,
                    )
                ]
            }
        )

    @router.post("/o/oauth2/token")
    def get_oauth_token(self, request: MockRequest) -> MockClientResponse:
        """Get an OAuth token"""
        if (
                not isinstance(request.kwargs["data"], bytes)
                and "raise_error" in request.kwargs["data"].values()
        ):
            return MockClientResponse(
                content={
                    "error": "invalid_grant",
                    "error_description": "Invalid grant: account not found"
                },
                status_code=400,
            )

        return MockClientResponse(
            {
                "access_token": "xxxx.yyyy",
                "expires_in": 3599,
                "token_type": "Bearer"
            }
        )

    @router.post(
        r"/gmail/v1/users/[a-zA-Z]+@[a-zA-Z]+\.[a-zA-Z]+/messages/send"
    )
    def send_email(self, _: MockRequest) -> MockClientResponse:
        return MockClientResponse(
            content={
                "id": "19050407063955c1",
                "threadId": "19050407063955c1",
                "labelIds": [
                    "SENT"
                ]
            }
        )

    @router.post(
        r"/gmail/v1/users/[a-zA-Z]+@[a-zA-Z]+\.[a-zA-Z]+/messages/batchModify"
    )
    def batch_modify(self, request: MockRequest) -> MockClientResponse:
        """Messages batch modify request mock."""
        if "invalid" in str(request.kwargs.get("json")):
            return MockClientResponse(
                content={
                    "error": {
                        "code": 400,
                        "message": "Invalid label: invalid",
                        "errors": [
                            {
                                "message": "Invalid label: invalid",
                                "domain": "global",
                                "reason": "invalidArgument"
                            }
                        ],
                        "status": "INVALID_ARGUMENT"
                    }
                },
                status_code=400
            )

        return MockClientResponse(status_code=204)
