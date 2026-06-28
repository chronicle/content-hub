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
from collections.abc import Iterable

from TIPCommon.types import SingleJson

from mimecast.core.datamodels import (
    Attachment,
    HoldMessage,
    MessageDetails,
)
from mimecast.tests.common import (
    BLOCK_SENDER_POLICY_ERROR_JSON,
    DOWNLOAD_ATTACHMENT_URL,
    MOCK_INVALID_CLIENT_CREDENTIALS_JSON,
)
from mimecast.tests.core.product import Mimecast
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class MimecastSession(MockSession[MockRequest, MockResponse, Mimecast]):
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            self.create_block_policy,
            get_oauth_token,
            self.get_account_info,
            self.search_messages,
            self.get_message_details,
            self.get_hold_message_list,
            self.get_message_attachments,
            self.get_download_url_for_attachment,
            self.get_download_attachment,
        ]

    @router.post("/api/account/get-account")
    def get_account_info(self, _: MockRequest) -> MockResponse:
        """
        Simulates getting account information.
        """
        return MockResponse(
            content={
                "meta": {"status": 200},
                "data": [{"accountId": "some_account_id"}],
            },
            status_code=200,
        )

    @router.post("/api/policy/blockedsenders/create-policy")
    def create_block_policy(self, request: MockRequest) -> MockResponse:
        """
        Simulates adding a block sender policy entry.

        Returns:
            MockResponse: A response object.
        """
        if "wrong_format" in request.kwargs["json"]["data"][0]["policy"]["comment"]:
            return MockResponse(
                content=BLOCK_SENDER_POLICY_ERROR_JSON,
                status_code=200,
            )
        first_policy_id = self._product.get_first_block_policy_id()
        if first_policy_id:
            response_data: SingleJson = self._product.get_block_policy(
                first_policy_id
            ).to_json()
            return MockResponse(content={"data": [response_data]}, status_code=200)
        return MockResponse(content={"data": []}, status_code=200)

    @router.post("/api/message-finder/search")
    def search_messages(self, _: MockRequest) -> MockResponse:
        """Simulates searching for messages in Mimecast.

        This method mocks the behavior of the Mimecast API endpoint
        `/api/message-finder/search`. It retrieves a list of messages
        from the mock product and returns them in a successful response.

        Args:
            _ (MockRequest): The mock request object. This parameter is
                not used in the method but is required by the router.

        Returns:
            MockResponse: A mock response object containing a list of
                messages and a status code of 200.
        """
        response_data: SingleJson = {
            "data": [
                {
                    "trackedEmails": [
                        message.to_json() for message in self._product.get_messages()
                    ]
                }
            ]
        }

        return MockResponse(content=response_data, status_code=200)

    @router.post("/api/message-finder/get-message-info")
    def get_message_details(self, request: MockRequest) -> MockResponse:
        """Simulates searching for messages in Mimecast.

        This method mocks the behavior of the Mimecast API endpoint
        `/api/message-finder/search`. It returns a predefined list of
        messages as a successful response.

        Args:
            _ (MockRequest): The mock request object. This parameter is
                not used in the method but is required by the router.

        Returns:
            MockResponse: A mock response object containing a list of
                messages and a status code of 200.
        """
        payload: SingleJson = request.kwargs["json"]
        message_id: str = payload["data"][0]["id"]
        message_details: MessageDetails = self._product.get_message_details(message_id)
        response_data: SingleJson = {"data": [message_details.to_json()]}

        return MockResponse(content=response_data, status_code=200)

    @router.post("/api/gateway/get-hold-message-list")
    def get_hold_message_list(self, _: MockRequest) -> MockResponse:
        """Simulates retrieving a list of messages on hold from Mimecast.

        This method mocks the behavior of the Mimecast API endpoint
        `/api/gateway/get-hold-message-list`. It retrieves a list of
        hold messages from the mock product and returns them in a
        successful response.

        Args:
            _ (MockRequest): The mock request object. This parameter is
                not used in the method but is required by the router.

        Returns:
            MockResponse: A mock response object containing a list of
                hold messages and a status code of 200.
        """
        hold_messages: list[HoldMessage] = self._product.get_hold_messages()
        response_data: SingleJson = {
            "data": [message.to_json() for message in hold_messages]
        }
        return MockResponse(content=response_data, status_code=200)

    @router.post("/api/gateway/message/get-message-detail")
    def get_message_attachments(self, _: MockRequest) -> MockResponse:
        """Simulates retrieving message attachments from Mimecast.

        This method mocks the behavior of the Mimecast API endpoint
        `/api/gateway/message/get-message-detail`. It retrieves a list of
        attachments from the mock product and returns them in a
        successful response.

        Args:
            _ (MockRequest): The mock request object. This parameter is
                not used in the method but is required by the router.

        Returns:
            MockResponse: A mock response object containing a list of
                attachments and a status code of 200.
        """
        attachments: list[Attachment] = self._product.get_attachments()
        response_data: SingleJson = {
            "data": [
                {"attachments": [attachment.to_json() for attachment in attachments]}
            ]
        }
        return MockResponse(content=response_data, status_code=200)

    @router.post("/api/gateway/message/get-file")
    def get_download_url_for_attachment(self, _: MockRequest) -> MockResponse:
        """Simulates retrieving a download URL for an attachment from Mimecast.

        This method mocks the behavior of the Mimecast API endpoint
        `/api/gateway/message/get-file`. It returns a predefined download URL
        in a successful response.

        Args:
            _ (MockRequest): The mock request object. This parameter is
                not used in the method but is required by the router.

        Returns:
            MockResponse: A mock response object containing a download URL
                and a status code of 200.
        """
        return MockResponse(content=DOWNLOAD_ATTACHMENT_URL, status_code=200)

    @router.get("/api/archive/get-message-part")
    def get_download_attachment(self, _: MockRequest) -> MockResponse:
        response_data = "attachment_content"
        return MockResponse(content=response_data, status_code=200)


@router.post("/oauth/token")
def get_oauth_token(request: MockRequest) -> MockResponse:
    """
    Simulates an OAuth token generation endpoint.

    Args:
        request (MockRequest): The incoming request object containing the payload.

    Returns:
        MockResponse: A response object containing either an OAuth token or
            an error message.

    Raises:
        None: All errors are handled internally by returning appropriate responses.
    """
    if "raise_error" in request.kwargs["data"].values():
        return MockResponse(
            content=MOCK_INVALID_CLIENT_CREDENTIALS_JSON,
            status_code=401,
        )

    return MockResponse(
        content={
            "access_token": "b09Z0pRmnB4rXdvPza2de5Cn6FSQ",
            "token_type": "Bearer",
            "expires_in": 1799,
            "scope": "",
        },
        headers={"content-type": "application/json"},
    )
