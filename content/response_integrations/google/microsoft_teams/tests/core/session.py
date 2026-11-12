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

from collections.abc import Sequence
from urllib.parse import parse_qs, unquote

from microsoft_teams.tests.core.microsoft_teams import MicrosoftTeams

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class MicrosoftTeamsSession(MockSession[MockRequest, MockResponse, MicrosoftTeams]):
    """Contains handlers for each of the network-calling API endpoints.

    Handlers for endpoints that share a base path are combined and use request
    parameters to determine the correct mock response.
    """

    def __init__(self, product: MicrosoftTeams, mock_data: dict):
        """Initializes the MicrosoftTeamsSession.

        Args:
            product: An instance of the MicrosoftTeams integration.
            mock_data: A dictionary containing mock data for responses.
        """
        super().__init__(product)
        self.mock_data: dict = mock_data

    def get_routed_functions(self) -> Sequence[RouteFunction]:
        """Returns a list of all mock route handler functions."""
        return [
            self.get_oauth_token,
            self.users_beta_handler,
            self.get_user_handler,
            self.users_v1_handler,
            self.check_account_handler,
            self.groups_beta_handler,
            self.get_team_handler,
            self.list_channels_handler,
            self.create_channel_handler,
            self.delete_channel_handler,
            self.manage_channel_users_handler,
            self.add_user_to_channel_handler,
            self.remove_user_from_channel_handler,
            self.post_msg_handler,
            self.get_msg_handler,
            self.msg_replies_handler,
            self.send_message_reply_handler,
            self.list_chats_handler,
            self.manage_chats_handler,
            self.channel_messages_handler,
        ]

    @router.post("/test_tenant/oauth2/token")
    def get_oauth_token(self, _request: MockRequest) -> MockResponse:
        """Mocks the OAuth token acquisition endpoint."""
        return MockResponse(
            content={
                "access_token": "mock_access_token",
                "refresh_token": "mock_new_refresh_token",
            }
        )

    @router.get("/beta/users/user1")
    def get_user_handler(self, _request: MockRequest) -> MockResponse:
        """Mocks the retrieval of a single user by ID."""
        return MockResponse(content=self.mock_data["get_user_success"])

    @router.get("/beta/users")
    def users_beta_handler(self, request: MockRequest) -> MockResponse:
        """Mocks the /beta/users endpoint.

        Returns different data based on the presence of a "$filter" parameter.
        """
        params = parse_qs(request.url.query)
        if "$filter" in params:
            return MockResponse(
                content=self.mock_data["get_user_id_success"]
            )
        return MockResponse(content=self.mock_data["list_users_success"])

    @router.get("/v1.0/users")
    def users_v1_handler(self, _request: MockRequest) -> MockResponse:
        """Mocks the /v1.0/users endpoint for finding a user ID."""
        return MockResponse(
            content=self.mock_data["find_user_id_success"]
        )

    @router.get("/v1.0/me")
    def check_account_handler(self, _request: MockRequest) -> MockResponse:
        """Mocks the /v1.0/me endpoint for checking account validity."""
        return MockResponse(
            content=self.mock_data["check_account_success"]
        )

    @router.get("/beta/groups")
    def groups_beta_handler(self, request: MockRequest) -> MockResponse:
        """Mocks the /beta/groups endpoint for fetching teams.

        Differentiates behavior based on the "$filter" parameter.
        """
        params = parse_qs(request.url.query)
        filter_param = params.get("$filter", [""])[0]

        if "JH Information & Cyber Security Team" in unquote(filter_param):
            return MockResponse(
                content=self.mock_data[
                    "get_team_id_with_ampersand_success"
                ]
            )
        if "displayName" in filter_param:
            return MockResponse(
                content=self.mock_data["get_team_id_success"]
            )

        return MockResponse(content=self.mock_data["list_teams_success"])

    @router.get("/beta/teams/team1")
    def get_team_handler(self, _request: MockRequest) -> MockResponse:
        """Mocks the retrieval of a single team by ID."""
        return MockResponse(content=self.mock_data["get_team_success"])

    @router.get("/beta/teams/t1/channels")
    def list_channels_handler(self, request: MockRequest) -> MockResponse:
        """Mocks the listing and searching of channels in a team.

        Differentiates behavior based on the "$filter" parameter.
        """
        params = parse_qs(request.url.query)
        if "$filter" in params:
            return MockResponse(
                content=self.mock_data["get_channel_id_success"]
            )
        return MockResponse(content=self.mock_data["list_channels_success"])

    @router.post("/beta/teams/t1/channels")
    def create_channel_handler(self, _request: MockRequest) -> MockResponse:
        """Mocks the channel creation endpoint."""
        return MockResponse(
            content=self.mock_data["create_channel_success"],
            status_code=201,
        )

    @router.delete("/beta/teams/t1/channels/c1")
    def delete_channel_handler(self, _request: MockRequest) -> MockResponse:
        """Mocks the channel deletion endpoint."""
        return MockResponse(content=None, status_code=204)

    @router.post("/beta/teams/t1/channels/c1/members")
    def add_user_to_channel_handler(
        self, _request: MockRequest
    ) -> MockResponse:
        """Mocks adding a user as a member to a channel."""
        return MockResponse(
            content=self.mock_data["add_user_to_channel_success"],
            status_code=201,
        )

    @router.get("/beta/teams/t1/channels/c1/members")
    def manage_channel_users_handler(
        self, _request: MockRequest
    ) -> MockResponse:
        """Mocks the listing of users/members in a channel."""
        return MockResponse(
            content=self.mock_data["manage_channel_users_success"]
        )

    @router.delete("/beta/teams/t1/channels/c1/members/u1")
    def remove_user_from_channel_handler(
        self, _request: MockRequest
    ) -> MockResponse:
        """Mocks removing a user/member from a channel."""
        return MockResponse(content=None, status_code=204)

    @router.post("/beta/teams/t1/channels/c1/messages")
    def post_msg_handler(self, _request: MockRequest) -> MockResponse:
        """Mocks sending a new message to a channel."""
        return MockResponse(
            content=self.mock_data["post_msg_success"], status_code=201
        )

    @router.get("/beta/teams/t1/channels/c1/messages/m1")
    def get_msg_handler(self, _request: MockRequest) -> MockResponse:
        """Mocks retrieving a specific message from a channel."""
        return MockResponse(content=self.mock_data["get_msg_success"])

    @router.get("/beta/teams/t1/channels/c1/messages/m1/replies")
    def msg_replies_handler(self, _request: MockRequest) -> MockResponse:
        """Mocks listing the replies for a specific message."""
        return MockResponse(content=self.mock_data["msg_replies_success"])

    @router.post("/v1.0/teams/t1/channels/c1/messages/m1/replies")
    def send_message_reply_handler(
        self, _request: MockRequest
    ) -> MockResponse:
        """Mocks sending a reply to a message in a channel."""
        return MockResponse(
            content=self.mock_data["send_message_reply_success"],
            status_code=201,
        )

    @router.get("/v1.0/me/chats")
    def list_chats_handler(self, request: MockRequest) -> MockResponse:
        """Mocks listing and searching for chats.

        Returns different data based on the presence of a "$filter" parameter.
        """
        params = parse_qs(request.url.query)
        if "$filter" in params:
            return MockResponse(
                content=self.mock_data[
                    "list_channels_to_send_message_success"
                ]
            )
        return MockResponse(content=self.mock_data["list_chats_success"])

    @router.post("/beta/chats")
    def manage_chats_handler(self, _request: MockRequest) -> MockResponse:
        """Mocks the chat creation/management endpoint."""
        return MockResponse(
            content=self.mock_data["manage_chats_success"],
            status_code=201,
        )

    @router.get("/v1.0/chats/chat1/messages")
    def channel_messages_handler(
        self, _request: MockRequest
    ) -> MockResponse:
        """Mocks retrieving messages from a chat channel."""
        return MockResponse(
            content=self.mock_data["channel_messages_success"]
        )
