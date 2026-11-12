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
from urllib.parse import quote, urljoin
from unittest.mock import Mock

import pytest

from TIPCommon.types import SingleJson

from microsoft_teams.core.MicrosoftManager import \
    MicrosoftTeamsManager
from microsoft_teams.core.MicrosoftExceptions import MicrosoftTeamsManagerError

from microsoft_teams.tests.conftest import CONFIG
from microsoft_teams.tests.core.session import MicrosoftTeamsSession


CUSTOM_LOGIN_ROOT: str = CONFIG["Login API Root"]
CUSTOM_API_ROOT: str = CONFIG["API Root"]
TENANT: str = CONFIG["Tenant"]


def test_build_url_encodes_special_parameters(
    microsoft_teams_manager: MicrosoftTeamsManager,
) -> None:
    """
    Verifies that _build_url correctly encodes values
    for keys specified in keys_to_encode.
    This directly tests the centralized fix.
    """
    team_name_with_special_chars = "Finance & Accounting / R&D"
    path_template = (
        "{version}/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team') "
        "and displayName eq '{team_name}'&select=id,displayName"
    )

    result_url = microsoft_teams_manager._build_url(  # pylint: disable=protected-access
        path_template, team_name=team_name_with_special_chars
    )

    encoded_value = quote(team_name_with_special_chars)
    expected_path = (
        f"beta/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team') "
        f"and displayName eq '{encoded_value}'&select=id,displayName"
    )
    expected_url = urljoin(CUSTOM_API_ROOT, expected_path)

    assert result_url == expected_url


def test_get_team_id_with_special_characters(
    microsoft_teams_manager: MicrosoftTeamsManager,
    mock_data: SingleJson,
) -> None:
    """
    Integration Test: Verifies get_team_id works with a name containing '&'.
    This relies on the fixed _build_url and the smart router in session.py.
    """
    team_name = "JH Information & Cyber Security Team"
    expected_id = mock_data["get_team_id_with_ampersand_success"]["value"][0][
        "id"]

    found_id = microsoft_teams_manager.get_team_id(team_name)
    assert found_id == expected_id


def test_add_user_to_channel_builds_correct_payload(
    microsoft_teams_manager: MicrosoftTeamsManager,
    mocker: pytest.MockFixture,
) -> None:
    """
    Verifies that `add_user_to_channel` constructs the correct JSON payload
    as defined in the manager.
    """
    spy_post = mocker.spy(microsoft_teams_manager.session, "post")

    team_id, channel_id, user_id = "t1", "c1", "u1"

    microsoft_teams_manager.add_user_to_channel(
        team_id=team_id, channel_id=channel_id, user_id=user_id
    )

    spy_post.assert_called_once()
    request_payload = spy_post.call_args.kwargs.get("json")

    expected_bind_url = urljoin(CUSTOM_API_ROOT, f"beta/users('{user_id}')")
    expected_payload = {
        "@odata.type": "#microsoft.graph.aadUserConversationMember",
        "user@odata.bind": expected_bind_url,
    }

    assert request_payload == expected_payload


def test_refresh_token_uses_custom_login_root(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests that token refresh logic builds URL from the custom `login_api_root`."""
    spy_post: Mock = mocker.spy(script_session, "post")
    microsoft_teams_manager.refresh_token(
        CONFIG["Refresh Token"],
        CONFIG["Redirect URL"]
    )
    spy_post.assert_called_once()
    request_url: str = spy_post.call_args.args[0]
    expected_url: str = urljoin(CUSTOM_LOGIN_ROOT, f"{TENANT}/oauth2/token")
    assert request_url == expected_url


def test_refresh_token_error_response_raises_manager_error(
    microsoft_teams_manager: MicrosoftTeamsManager,
    mocker: pytest.MockFixture,
) -> None:
    """Tests that OAuth error response raises MicrosoftTeamsManagerError with error details."""
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 400
    mock_response.json.return_value = {
        "error": "invalid_grant",
        "error_description": "AADSTS700082: The refresh token has expired due to inactivity.",
    }
    mocker.patch.object(microsoft_teams_manager.session, "post", return_value=mock_response)

    with pytest.raises(MicrosoftTeamsManagerError, match=r"AADSTS700082"):
        microsoft_teams_manager.refresh_token("dummy_token", "http://localhost/")


def test_get_user_details_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for get_user_details, which gets a user by ID."""
    mocker.patch.object(
        microsoft_teams_manager, "find_user_id", return_value="user1"
    )
    spy_get: Mock = mocker.spy(script_session, "get")
    microsoft_teams_manager.get_user_details(user_name="test")
    spy_get.assert_called_once()
    request_url: str = spy_get.call_args.args[0]
    expected_url = urljoin(CUSTOM_API_ROOT, "beta/users/user1")
    assert request_url == expected_url


def test_list_users_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for list_users."""
    spy_request: Mock = mocker.spy(script_session, "request")
    microsoft_teams_manager.list_users()
    spy_request.assert_called_once()
    request_url: str = spy_request.call_args.args[1]
    expected_url = urljoin(CUSTOM_API_ROOT, "beta/users")
    assert request_url == expected_url


def test_get_user_id_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for get_user_id (find by display name)."""
    spy_get: Mock = mocker.spy(script_session, "get")
    microsoft_teams_manager.get_user_id(user_name="test")
    spy_get.assert_called_once()
    request_url: str = spy_get.call_args.args[0]
    path = "beta/users?$filter=displayName eq 'test'&$select=id,displayName"
    expected_url = urljoin(CUSTOM_API_ROOT, path)
    assert request_url == expected_url


def test_find_user_id_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for find_user_id (find by name, UPN, or mail)."""
    spy_get: Mock = mocker.spy(script_session, "get")
    microsoft_teams_manager.find_user_id(user_name="test")
    spy_get.assert_called_once()
    request_url: str = spy_get.call_args.args[0]
    path = (
        "v1.0/users?$filter=displayName eq 'test' "
        "or userPrincipalName eq 'test' "
        "or mail eq 'test'&$select=id,displayName,mail,userPrincipalName"
    )
    expected_url = urljoin(CUSTOM_API_ROOT, path)
    assert request_url == expected_url


def test_check_account_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for check_account (gets current user info)."""
    spy_get: Mock = mocker.spy(script_session, "get")
    microsoft_teams_manager.check_account()
    spy_get.assert_called_once()
    request_url: str = spy_get.call_args.args[0]
    expected_url = urljoin(CUSTOM_API_ROOT, "v1.0/me")
    assert request_url == expected_url


def test_list_teams_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for list_teams."""
    spy_request: Mock = mocker.spy(script_session, "request")
    microsoft_teams_manager.list_teams()
    spy_request.assert_called_once()
    request_url: str = spy_request.call_args.args[1]
    path = "beta/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team')"
    expected_url = urljoin(CUSTOM_API_ROOT, path)
    assert request_url == expected_url


def test_get_team_details_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for get_team_details, which gets a team by ID."""
    mocker.patch.object(
        microsoft_teams_manager, "get_team_id", return_value="team1"
    )
    spy_get: Mock = mocker.spy(script_session, "get")
    microsoft_teams_manager.get_team_details(team_name="test")
    spy_get.assert_called_once()
    request_url: str = spy_get.call_args.args[0]
    expected_url = urljoin(CUSTOM_API_ROOT, "beta/teams/team1")
    assert request_url == expected_url


def test_get_team_id_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for get_team_id (find by display name)."""
    spy_get: Mock = mocker.spy(script_session, "get")
    microsoft_teams_manager.get_team_id(team_name="test")
    spy_get.assert_called_once()
    request_url: str = spy_get.call_args.args[0]
    path = (
        "beta/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team') "
        "and displayName eq 'test'&select=id,displayName"
    )
    expected_url = urljoin(CUSTOM_API_ROOT, path)
    assert request_url == expected_url


def test_list_channels_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for list_channels."""
    mocker.patch.object(
        microsoft_teams_manager, "get_team_id", return_value="t1"
    )
    spy_get: Mock = mocker.spy(script_session, "get")
    microsoft_teams_manager.list_channels(team_name="test")
    spy_get.assert_called_once()
    request_url: str = spy_get.call_args.args[0]
    expected_url = urljoin(CUSTOM_API_ROOT, "beta/teams/t1/channels")
    assert request_url == expected_url


def test_get_channel_id_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for get_channel_id (find by display name)."""
    spy_get: Mock = mocker.spy(script_session, "get")
    microsoft_teams_manager.get_channel_id(team_id="t1", channel_name="c1")
    spy_get.assert_called_once()
    request_url: str = spy_get.call_args.args[0]
    path = "beta/teams/t1/channels?$filter=displayName eq 'c1'&$select=id,displayName"
    expected_url = urljoin(CUSTOM_API_ROOT, path)
    assert request_url == expected_url


def test_create_channel_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for create_channel."""
    spy_post: Mock = mocker.spy(script_session, "post")
    microsoft_teams_manager.create_channel(
        team_id="t1",
        channel_name="c1",
        channel_type="standard",
        description=""
    )
    spy_post.assert_called_once()
    request_url: str = spy_post.call_args.args[0]
    expected_url = urljoin(CUSTOM_API_ROOT, "beta/teams/t1/channels")
    assert request_url == expected_url


def test_delete_channel_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for delete_channel."""
    spy_delete: Mock = mocker.spy(script_session, "delete")
    microsoft_teams_manager.delete_channel(team_id="t1", channel_id="c1")
    spy_delete.assert_called_once()
    request_url: str = spy_delete.call_args.args[0]
    expected_url = urljoin(CUSTOM_API_ROOT, "beta/teams/t1/channels/c1")
    assert request_url == expected_url


def test_get_channel_users_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for get_channel_users."""
    spy_request: Mock = mocker.spy(script_session, "request")
    microsoft_teams_manager.get_channel_users(team_id="t1", channel_id="c1")
    spy_request.assert_called_once()
    request_url: str = spy_request.call_args.args[1]
    expected_url = urljoin(CUSTOM_API_ROOT, "beta/teams/t1/channels/c1/members")
    assert request_url == expected_url


def test_remove_user_from_channel_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for remove_user_from_channel."""
    spy_delete: Mock = mocker.spy(script_session, "delete")
    microsoft_teams_manager.remove_user_from_channel(
        team_id="t1",
        channel_id="c1",
        user_id="u1"
    )
    spy_delete.assert_called_once()
    request_url: str = spy_delete.call_args.args[0]
    expected_url = urljoin(
        CUSTOM_API_ROOT, "beta/teams/t1/channels/c1/members/u1"
    )
    assert request_url == expected_url


def test_send_message_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for send_message."""
    mocker.patch.object(
        microsoft_teams_manager, "get_team_id", return_value="t1"
    )
    mocker.patch.object(
        microsoft_teams_manager, "get_channel_id", return_value="c1"
    )
    spy_post: Mock = mocker.spy(script_session, "post")
    microsoft_teams_manager.send_message(
        team_name="test",
        channel_name="test",
        message="hi"
    )
    spy_post.assert_called_once()
    request_url: str = spy_post.call_args.args[0]
    expected_url = urljoin(
        CUSTOM_API_ROOT,
        "beta/teams/t1/channels/c1/messages"
    )
    assert request_url == expected_url


def test_get_message_by_id_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for get_message_by_id."""
    spy_get: Mock = mocker.spy(script_session, "get")
    microsoft_teams_manager.get_message_by_id(
        team_id="t1",
        channel_id="c1",
        message_id="m1"
    )
    spy_get.assert_called_once()
    request_url: str = spy_get.call_args.args[0]
    expected_url = urljoin(
        CUSTOM_API_ROOT, "beta/teams/t1/channels/c1/messages/m1"
    )
    assert request_url == expected_url


def test_get_message_replies_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for get_message_replies."""
    spy_get: Mock = mocker.spy(script_session, "get")
    microsoft_teams_manager.get_message_replies(
        team_id="t1",
        channel_id="c1",
        message_id="m1"
    )
    spy_get.assert_called_once()
    request_url: str = spy_get.call_args.args[0]
    expected_url = urljoin(
        CUSTOM_API_ROOT,
        "beta/teams/t1/channels/c1/messages/m1/replies"
    )
    assert request_url == expected_url


def test_send_message_reply_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for send_message_reply."""
    spy_post: Mock = mocker.spy(script_session, "post")
    microsoft_teams_manager.send_message_reply(
        team_id="t1",
        channel_id="c1",
        message_id="m1",
        content_type="text",
        content="hi"
    )
    spy_post.assert_called_once()
    request_url: str = spy_post.call_args.args[0]
    expected_url = urljoin(
        CUSTOM_API_ROOT,
        "v1.0/teams/t1/channels/c1/messages/m1/replies"
    )
    assert request_url == expected_url


def test_get_chats_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for get_chats."""
    spy_get: Mock = mocker.spy(script_session, "get")
    microsoft_teams_manager.get_chats(
        chat_type="All",
        filter_key="",
        filter_value="",
        filter_logic="",
        limit=10
    )
    spy_get.assert_called_once()
    request_url: str = spy_get.call_args.args[0]
    expected_url = urljoin(CUSTOM_API_ROOT, "v1.0/me/chats")
    assert request_url == expected_url


def test_create_chat_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for create_chat."""
    spy_post: Mock = mocker.spy(script_session, "post")
    microsoft_teams_manager.create_chat(user_ids=["u1"])
    spy_post.assert_called_once()
    request_url: str = spy_post.call_args.args[0]
    expected_url = urljoin(CUSTOM_API_ROOT, "beta/chats")
    assert request_url == expected_url


def test_get_chat_messages_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for get_chat_messages."""
    spy_request: Mock = mocker.spy(script_session, "request")  # Uses paginate
    microsoft_teams_manager.get_chat_messages(chat_id="chat1")
    spy_request.assert_called_once()
    request_url: str = spy_request.call_args.args[1]
    expected_url = urljoin(CUSTOM_API_ROOT, "v1.0/chats/chat1/messages")
    assert request_url == expected_url


def test_get_chat_id_builds_correct_url(
    microsoft_teams_manager: MicrosoftTeamsManager,
    script_session: MicrosoftTeamsSession,
    mocker: pytest.MockFixture
) -> None:
    """Tests URL for get_chat_id."""
    spy_get: Mock = mocker.spy(script_session, "get")
    microsoft_teams_manager.get_chat_id(entity_identifier="user@a.com")
    spy_get.assert_called_once()
    request_url: str = spy_get.call_args.args[0]
    path = "v1.0/me/chats?$expand=members&$filter=chatType eq 'oneOnOne'"
    expected_url = urljoin(CUSTOM_API_ROOT, path)
    assert request_url == expected_url


def test_chunk_user_names_escaping(
    microsoft_teams_manager: MicrosoftTeamsManager
) -> None:
    """Verifies that _chunk_user_names correctly escapes single quotes."""
    user_names = ["O'Connor", "Test User"]
    chunks = list(microsoft_teams_manager._chunk_user_names(user_names, 1800))  # pylint: disable=protected-access
    assert len(chunks) == 1
    assert chunks[0] == ["O''Connor", "Test User"]


def test_chunk_user_names_chunking(
    microsoft_teams_manager: MicrosoftTeamsManager
) -> None:
    """Verifies that _chunk_user_names splits user names based on length limit."""
    user_names = ["User1", "User2", "User3"]
    chunks = list(
        microsoft_teams_manager._chunk_user_names(user_names, max_chunk_length=36)  # pylint: disable=protected-access
    )
    assert len(chunks) == 2
    assert chunks[0] == ["User1", "User2"]
    assert chunks[1] == ["User3"]


def test_chunk_user_names_item_limit(
    microsoft_teams_manager: MicrosoftTeamsManager
) -> None:
    """Verifies that _chunk_user_names splits user names based on item limit."""
    user_names = [f"User{i}" for i in range(1, 10)]
    chunks = list(
        microsoft_teams_manager._chunk_user_names(  # pylint: disable=protected-access
            user_names, max_chunk_length=1800, max_items_per_chunk=7
        )  # pylint: disable=protected-access
    )
    assert len(chunks) == 2
    assert chunks[0] == [f"User{i}" for i in range(1, 8)]
    assert chunks[1] == ["User8", "User9"]


def test_chunk_user_names_empty_list(
    microsoft_teams_manager: MicrosoftTeamsManager
) -> None:
    """Verifies that empty list yields nothing."""
    chunks = list(microsoft_teams_manager._chunk_user_names([], 1800))  # pylint: disable=protected-access
    assert len(chunks) == 0


def test_filter_users_by_name_single_chunk(
    microsoft_teams_manager: MicrosoftTeamsManager,
    mocker: pytest.MockFixture
) -> None:
    """Verifies filter_users_by_name constructs the right url and paginates
    for a single chunk.
    """
    mock_paginate = mocker.patch.object(microsoft_teams_manager, "_paginate_results")
    mock_paginate.return_value = [{"id": "1", "displayName": "User1"}]

    results = list(microsoft_teams_manager.filter_users_by_name(["User1", "User2"]))

    assert results == [{"id": "1", "displayName": "User1"}]
    mock_paginate.assert_called_once()
    url = mock_paginate.call_args.kwargs.get("url")
    assert "displayName in ('User1', 'User2') or mail in ('User1', 'User2')" in url
    assert "&$select=" not in url


def test_filter_users_by_name_multiple_chunks(
    microsoft_teams_manager: MicrosoftTeamsManager,
    mocker: pytest.MockFixture
) -> None:
    """Verifies filter_users_by_name builds the URL per chunk due to size limits."""
    mock_paginate = mocker.patch.object(microsoft_teams_manager, "_paginate_results")
    mock_paginate.side_effect = [[{"id": "1"}], [{"id": "2"}], [{"id": "3"}]]

    mock_chunk = mocker.patch.object(
        microsoft_teams_manager,
        "_chunk_user_names",
        return_value=[["User1", "User2"], ["User3"]]
    )

    results = list(microsoft_teams_manager.filter_users_by_name(
        ["User1", "User2", "User3"],
        select_fields=["id", "displayName"]
    ))

    assert results == [{"id": "1"}, {"id": "2"}]
    assert mock_paginate.call_count == 2
    mock_chunk.assert_called_once_with(
        ["User1", "User2", "User3"],
        max_items_per_chunk=7
    )

    first_call_url = mock_paginate.call_args_list[0].kwargs.get("url")
    second_call_url = mock_paginate.call_args_list[1].kwargs.get("url")

    assert (
        "displayName in ('User1', 'User2') or mail in ('User1', 'User2')"
        in first_call_url
    )
    assert "&$select=id,displayName" in first_call_url

    assert "displayName in ('User3') or mail in ('User3')" in second_call_url
    assert "&$select=id,displayName" in second_call_url
