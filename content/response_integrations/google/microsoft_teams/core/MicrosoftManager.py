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

# =====================================
#             IMPORTS
# =====================================
from __future__ import annotations
import json
from copy import deepcopy
from typing import Final, Iterator
from urllib.parse import urljoin, quote

import requests

from .datamodels import Chat, Message, Reply
from .MicrosoftConstants import CHAT_TYPES
from .MicrosoftExceptions import (
    MicrosoftTeamsChannelNotFoundError,
    MicrosoftTeamsClientError,
    MicrosoftTeamsManagerError,
    MicrosoftTeamsMessageNotFoundError,
    MicrosoftTeamsTeamNotFoundError,
)
from .MicrosoftTeamsParser import MicrosoftTeamsParser


# =====================================
#             CONSTANTS
# =====================================
# Access consts
SCOPE_SEPARATOR = "%20"
SCOPE_SUFFIXES = [".default"]

TOKEN_PAYLOAD = {
    "client_id": None,
    "scope": None,
    "client_secret": None,
    "grant_type": "authorization_code",
    "code": None,
    "redirect_uri": None,
}

REFRESH_PAYLOAD = {
    "client_id": None,
    "scope": None,
    "refresh_token": None,
    "client_secret": None,
    "grant_type": "refresh_token",
    "redirect_uri": None,
}

HEADERS = {"Content-Type": "application/json"}

MESSAGE_REQ_BODY = {"body": {"content": None}}

# urls
URL_AUTHORIZATION = (
    "{tenant}/oauth2/v2.0/authorize"
    "?client_id={client_id}"
    "&redirect_uri={redirect_uri}"
    "&response_type=code"
    "&response_mode=query"
    "&scope={scope}"
)

VERSION_V1: Final[str] = "v1.0"
VERSION_BETA: Final[str] = "beta"
API_ENDPOINTS: Final[dict[str, str]] = {
    # Authentication
    "fetch_token": "{tenant}/oauth2/token",

    # Users
    "get_user": "{version}/users/{userID}",
    "list_users": "{version}/users",
    "get_user_id": (
        "{version}/users?$filter=displayName eq '{user_name}'&$select=id,displayName"
    ),
    "find_user_id": (
        "{version}/users?$filter=displayName eq '{user_name}' "
        "or userPrincipalName eq '{user_name}' "
        "or mail eq '{user_name}'"
        "&$select=id,displayName,mail,userPrincipalName"
    ),
    "user_data_bind": "{version}/users('{user_id}')",
    "check_account": "{version}/me",

    # Teams
    "list_teams": (
        "{version}/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team')"
    ),
    "get_team": "{version}/teams/{team_id}",
    "get_team_id": (
        "{version}/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team') "
        "and displayName eq '{team_name}'&select=id,displayName"
    ),

    # Channels
    "list_channels": "{version}/teams/{team_id}/channels",
    "get_channel_id": (
        "{version}/teams/{team_id}/channels?$filter=displayName eq "
        "'{channel_name}'&$select=id,displayName"
    ),
    "create_channel": "{version}/teams/{team_id}/channels",
    "delete_channel": "{version}/teams/{team_id}/channels/{channel_id}",

    # Channel Members
    "manage_channel_users": "{version}/teams/{team_id}/channels/{channel_id}/members",
    "remove_user_from_channel": (
        "{version}/teams/{team_id}/channels/{channel_id}/members/{user_id}"
    ),

    # Messages
    "post_msg": "{version}/teams/{team_id}/channels/{channel_id}/messages",
    "get_msg": "{version}/teams/{team_id}/channels/{channel_id}/messages/{message_id}",
    "msg_replies": (
        "{version}/teams/{team_id}/channels/{channel_id}/messages/{message_id}/replies"
    ),
    "send_message_reply": (
        "{version}/teams/{team_id}/channels/{channel_id}/messages/{message_id}/replies"
    ),

    # Chats
    "list_chats": "{version}/me/chats",
    "manage_chats": "{version}/chats",
    "channel_messages": "{version}/chats/{chat_id}/messages",
    "list_channels_to_send_message": (
        "{version}/me/chats?$expand=members&$filter=chatType eq 'oneOnOne'"
    ),
}


# =====================================
#             HELPERS
# =====================================
def _get_full_scopes(api_root: str) -> list[str]:
    """Builds a list of full scope URLs based on the API root.

    Args:
        api_root: The base URL of the resource API.

    Returns:
        A list of fully formed scope URLs.
    """
    return [urljoin(api_root, suffix) for suffix in SCOPE_SUFFIXES]


def get_access_token_behalf_user(
    code: str,
    client_id: str,
    client_secret: str,
    tenant: str,
    redirect_url: str,
    api_root: str,
    login_api_root: str,
    verify_ssl: bool = False,
) -> str:
    """Uses the authorization code to request an access token.

    Args:
        code: The authorization_code.
        client_id: The Application ID from the registration portal.
        client_secret: The application secret from the registration portal.
        tenant: The domain name from the Azure portal.
        redirect_url: The Redirect URL used for authentication.
        verify_ssl: Whether to verify SSL for the request.
        api_root: The API root of the Microsoft Teams API.
        login_api_root: The login API root of the Microsoft Teams API.

    Returns:
        An OAuth 2.0 refresh token, which is long-lived and can be used to
        retain access to resources.
    """
    payload = deepcopy(TOKEN_PAYLOAD)
    payload["client_id"] = client_id
    payload["client_secret"] = client_secret
    payload["code"] = code
    payload["redirect_uri"] = redirect_url
    full_scopes = _get_full_scopes(api_root)
    payload["scope"] = " ".join(full_scopes)
    token_url = urljoin(
        login_api_root,
        API_ENDPOINTS["fetch_token"].format(tenant=tenant)
    )
    res = requests.post(token_url, data=payload, verify=verify_ssl)
    validate_response(res, handle_client_error=True)
    return res.json().get("refresh_token")


def generate_auth_url(
    login_api_root: str,
    api_root: str,
    tenant: str,
    client_id: str,
    redirect_uri: str,
) -> str:
    """Generates the Microsoft authorization URL for the OAuth 2.0 flow.

    This URL is used to initiate the user consent and sign-in process,
    requesting the necessary permissions (scopes) for the application.

    Args:
        login_api_root: The base URL for the login endpoint.
        api_root: The base URL of the resource API.
        tenant: The Azure AD tenant ID.
        client_id: The application's (client) ID.
        redirect_uri: The URI where the user is redirected after auth.

    Returns:
        The fully formed authorization URL.
    """
    full_scopes = _get_full_scopes(api_root)
    url_encoded_scope = SCOPE_SEPARATOR.join(full_scopes)

    relative_auth_path = URL_AUTHORIZATION.format(
        tenant=tenant,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=url_encoded_scope,
    )

    return urljoin(login_api_root, relative_auth_path)


def validate_response(
    response,
    custom_exception=MicrosoftTeamsManagerError,
    handle_client_error=False
):
    """Validates an API response and raises exceptions on failure.

    Args:
        response: The `requests` response object.
        custom_exception: The default exception to raise for non-404 errors.
        handle_client_error: If True, raises a specific client error for 400s.

    Raises:
        MicrosoftTeamsClientError: On a 400 error if handle_client_error is True.
        MicrosoftTeamsChannelNotFoundError: On a 404 error.
        custom_exception: On any other HTTP error.
    """
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        if response.status_code == 400 and handle_client_error:
            error_content = json.loads(error.response.content).get("error", {})
            inner_error = error_content.get("innerError", {})
            message = inner_error.get("message", "") or error_content.get(
                "message", ""
            )
            raise MicrosoftTeamsClientError(message) from error

        if response.status_code == 404:
            raise MicrosoftTeamsChannelNotFoundError(error) from error

        raise custom_exception(
            f"Error:{error}, response:{error.response.content}"
        ) from error


# =====================================
#               CLASSES
# =====================================
class MicrosoftTeamsManager:
    """Manages interactions with the Microsoft Teams API."""

    def __init__(
        self,
        client_id,
        client_secret,
        tenant,
        refresh_token,
        redirect_url,
        api_root,
        login_api_root,
        verify_ssl=False,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant = tenant
        self.default_version = VERSION_BETA
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.api_root = api_root
        self.login_api_root = login_api_root
        self.parser = MicrosoftTeamsParser()
        self.access_token = self.refresh_token(refresh_token, redirect_url)

    def refresh_token(self, refresh_token: str, redirect_url: str) -> str:
        """Refreshes a short-lived access token using a refresh token.

        Args:
            refresh_token: The long-lived token acquired during authorization.
            redirect_url: The Redirect URL used for authentication.

        Returns:
            A new, short-lived access token for API calls.

        Raises:
            MicrosoftTeamsManagerError: If the refresh token is expired or invalid.
        """
        payload = deepcopy(REFRESH_PAYLOAD)
        payload["client_id"] = self.client_id
        payload["refresh_token"] = refresh_token
        payload["client_secret"] = self.client_secret
        payload["redirect_uri"] = redirect_url
        full_scopes = _get_full_scopes(self.api_root)
        payload["scope"] = " ".join(full_scopes)

        token_url = urljoin(self.login_api_root, f"{self.tenant}/oauth2/token")
        res = self.session.post(token_url, data=payload)

        try:
            response_json = res.json()
        except Exception:
            response_json = {}

        if "error" in response_json or "error_description" in response_json:
            error = response_json.get("error", "")
            error_description = response_json.get("error_description", "")
            raise MicrosoftTeamsManagerError(
                f"Failed to refresh token: {error}: {error_description}"
            )

        validate_response(res)
        access_token = response_json["access_token"]
        self.new_refresh_token = response_json.get("refresh_token")
        self.session.headers.update({"Authorization": f"Bearer {access_token}"})

        return access_token

    def list_users(self, max_users_to_return: int | None = None) -> list[dict]:
        """Retrieves a list of user objects from the API.

        Args:
            max_users_to_return: The maximum number of users to return.

        Returns:
            A list of dictionaries, where each dictionary represents a user.
        """
        url = self._build_url(API_ENDPOINTS["list_users"])
        return self._paginate_results(url=url, limit=max_users_to_return)

    def filter_users_by_name(
        self, user_names: list[str], select_fields: list[str] | None = None
    ) -> Iterator[dict]:
        """Retrieves a list of user objects filtered by displayName and mail.

        Args:
            user_names: A list of user names or emails.
            select_fields: A list of fields to include in the response.

        Returns:
            A generator of dictionaries, where each dictionary represents a user.
        """
        base_url = self._build_url(API_ENDPOINTS["list_users"])
        select_query = f"&$select={','.join(select_fields)}" if select_fields else ""

        for chunk in self._chunk_user_names(user_names, max_items_per_chunk=7):
            names_str = ", ".join(f"'{name}'" for name in chunk)
            url = (
                f"{base_url}?$filter=displayName in ({names_str})"
                f" or mail in ({names_str}){select_query}"
            )
            yield from self._paginate_results(url=url)


    def _chunk_user_names(
        self,
        user_names: list[str],
        max_chunk_length: int = 1800,
        max_items_per_chunk: int = 15
    ) -> Iterator[list[str]]:
        """Yields chunks of user names that collectively fit within the
        URL max length limit and Graph API clause limits.

        Args:
            user_names: The original list of user names to chunk.
            max_chunk_length: The max string length contribution allowed per chunk.
            max_items_per_chunk: The maximum number of items in a single chunk.

        Yields:
            Lists of properly escaped names suitable for batch graph API lookup.
        """
        current_chunk = []
        current_chunk_length = 0

        safe_names = [name.replace("'", "''") for name in user_names]

        for name in safe_names:
            estimated_length = len(name.replace(" ", "%20"))
            name_contribution_length = (estimated_length + 4) * 2

            if current_chunk and (
                current_chunk_length + name_contribution_length > max_chunk_length
                or len(current_chunk) >= max_items_per_chunk
            ):
                yield current_chunk
                current_chunk = []
                current_chunk_length = 0

            current_chunk.append(name)
            current_chunk_length += name_contribution_length

        if current_chunk:
            yield current_chunk

    def get_user_id(self, user_name: str) -> str:
        """Finds a user's ID by their exact display name.

        Args:
            user_name: The display name of the user to find.

        Returns:
            The user's unique ID.

        Raises:
            MicrosoftTeamsManagerError: If no user with the exact display name is found.
        """
        url = self._build_url(API_ENDPOINTS["get_user_id"], user_name=user_name)
        response = self.session.get(url)
        validate_response(response)

        users = response.json().get("value")

        for user in users:
            if user.get("displayName") == user_name:
                return user.get("id")

        raise MicrosoftTeamsManagerError("User not found")

    def find_user_id(self, user_name: str) -> str:
        """Finds a user's ID by displayName, userPrincipalName, or email.

        Args:
            user_name: The name, UPN, or email to search for.

        Returns:
            The user's unique ID.

        Raises:
            MicrosoftTeamsManagerError: If no matching user is found.
        """
        url = self._build_url(
            API_ENDPOINTS["find_user_id"],
            version=VERSION_V1,
            user_name=user_name
        )
        response = self.session.get(url)
        validate_response(response)

        users = response.json().get("value")

        for user in users:
            if user_name == user.get("displayName") or (
                user.get("userPrincipalName").casefold() == user_name.casefold()
                or (
                    user.get("mail") is not None
                    and user.get("mail").casefold() == user_name.casefold()
                )
            ):
                return user.get("id")

        raise MicrosoftTeamsManagerError("User not found")

    def get_user_details(self, user_name: str) -> dict:
        """Retrieves the full properties and relationships of a user object.

        Args:
            user_name: The display name, UPN, or email of the user.

        Returns:
            A dictionary containing the user's detailed information.
        """
        user_id = self.find_user_id(user_name=user_name)
        url = self._build_url(API_ENDPOINTS["get_user"], userID=user_id)
        response = self.session.get(url)
        validate_response(response)
        return response.json()

    def list_channels(
        self, team_name: str, max_channels_to_return: int | None = None
    ) -> list[dict]:
        """Retrieves the list of channels for a specific team.

        Args:
            team_name: The name of the team to get channels from.
            max_channels_to_return: Optional limit for the number of channels.

        Returns:
            A list of dictionaries, where each dictionary represents a channel.
        """
        team_id = self.get_team_id(team_name)
        url = self._build_url(API_ENDPOINTS["list_channels"], team_id=team_id)
        teams_response = self.session.get(url)
        validate_response(teams_response)
        results = teams_response.json().get("value")

        if max_channels_to_return:
            return results[:max_channels_to_return]

        return results

    def list_teams(self, max_teams_to_return: int | None = None) -> list[dict]:
        """Retrieves a list of all teams.

        Args:
            max_teams_to_return: An optional limit on the number of teams to return.

        Returns:
            A list of dictionaries, where each dictionary represents a team.
        """
        url = self._build_url(API_ENDPOINTS["list_teams"])
        return self._paginate_results(url=url, limit=max_teams_to_return)

    def _paginate_results(self, url, limit=None, method="GET"):
        """Paginates through API results.

        Args:
            url (str): The initial URL to fetch.
            limit (int, optional): The maximum number of results to return.
            method (str, optional): The HTTP method to use. Defaults to "GET".

        Returns:
            list: A list of paginated results.
        """
        response = self.session.request(method, url)
        validate_response(response)
        json_result = response.json()
        results = json_result.get("value", [])
        next_url = json_result.get("@odata.nextLink")

        while next_url:
            if limit and len(results) >= limit:
                break
            url = next_url
            response = self.session.request(method, url)
            validate_response(response)
            json_result = response.json()
            next_url = json_result.get("@odata.nextLink")
            results.extend(json_result.get("value", []))

        return results[:limit] if limit else results

    def get_team_id(
        self,
        team_name: str,
        handle_client_error: bool = False
    ) -> str:
        """Finds a team's ID by its exact display name.

        Args:
            team_name: The display name of the team to find.
            handle_client_error: If True, client errors are handled differently.

        Returns:
            The team's unique ID.

        Raises:
            MicrosoftTeamsTeamNotFoundError: If no team with that exact name is found.
        """
        url = self._build_url(API_ENDPOINTS["get_team_id"], team_name=team_name)
        response = self.session.get(url)
        validate_response(response, handle_client_error=handle_client_error)

        teams = response.json().get("value")

        for team in teams:
            if team.get("displayName") == team_name:
                return team.get("id")

        raise MicrosoftTeamsTeamNotFoundError("No team was found")

    def get_team_details(self, team_name: str) -> dict:
        """Retrieves the full properties of a team object.

        Args:
            team_name: The display name of the team.

        Returns:
            A dictionary containing the team's detailed information.
        """
        team_id = self.get_team_id(team_name)
        url = self._build_url(API_ENDPOINTS["get_team"], team_id=team_id)
        response = self.session.get(url)
        validate_response(response)
        return response.json()

    def send_message(
        self,
        channel_name: str,
        team_name: str,
        message: str
    ) -> dict:
        """Posts a message to a specific channel within a team.

        Args:
            channel_name: The name of the target channel.
            team_name: The name of the team containing the channel.
            message: The message content to post (can be plain text or HTML).

        Returns:
            A dictionary of the API response containing the new message's ID.
        """
        team_id = self.get_team_id(team_name)
        channel_id = self.get_channel_id(team_id, channel_name)
        url = self._build_url(
            API_ENDPOINTS["post_msg"], team_id=team_id, channel_id=channel_id
        )
        payload = {"body": {"content": message}}
        response = self.session.post(url, json=payload)
        validate_response(response)
        return response.json()

    def get_message_by_id(
        self, team_id: str, channel_id: str, message_id: str
    ) -> str | None:
        """Retrieves a single message from a channel by its ID.

        Args:
            team_id: The ID of the team containing the channel.
            channel_id: The ID of the channel containing the message.
            message_id: The ID of the message to retrieve.

        Returns:
            The message's unique ID as a string, or None if not found.

        Raises:
            MicrosoftTeamsMessageNotFoundError: If the API returns a 404 Not Found.
        """
        url = self._build_url(
            API_ENDPOINTS["get_msg"],
            team_id=team_id,
            channel_id=channel_id,
            message_id=message_id,
        )
        response = self.session.get(url)
        validate_response(response, MicrosoftTeamsMessageNotFoundError)
        return response.json().get("id")

    def get_channel_id(
        self, team_id: str, channel_name: str, handle_client_error: bool = False
    ) -> str:
        """Finds a channel's ID within a team by its exact display name.

        Args:
            team_id: The unique ID of the team.
            channel_name: The display name of the channel to find.
            handle_client_error: If True, client errors are handled differently.

        Returns:
            The channel's unique ID.

        Raises:
            MicrosoftTeamsChannelNotFoundError: If the channel is not found.
        """
        url = self._build_url(
            API_ENDPOINTS["get_channel_id"],
            team_id=team_id,
            channel_name=channel_name,
        )
        response = self.session.get(url)
        validate_response(response, handle_client_error=handle_client_error)

        channels = response.json().get("value")

        for channel in channels:
            if channel.get("displayName") == channel_name:
                return channel.get("id")

        raise MicrosoftTeamsTeamNotFoundError("No channel was found")

    def get_channel_by_channel_name(
        self,
        team_id: str,
        channel_name: str
    ) -> dict:
        """Finds a channel's full data object by its display name.

        Note:
            This method fetches all channels in the team and filters them locally,
            which may be inefficient for teams with many channels.

        Args:
            team_id: The unique ID of the team.
            channel_name: The display name of the channel to find.

        Returns:
            A dictionary containing the channel's data.

        Raises:
            MicrosoftTeamsChannelNotFoundError: If the channel is not found.
        """
        url = self._build_url(API_ENDPOINTS["list_channels"], team_id=team_id)
        response = self.session.get(url)
        validate_response(response)

        for channel in response.json().get("value"):
            if channel.get("displayName") == channel_name:
                return channel

        raise MicrosoftTeamsChannelNotFoundError("No channel was found")

    def get_message_replies(
        self, team_id: str, channel_id: str, message_id: str
    ) -> list[dict]:
        """Retrieves all replies to a specific message in a channel.

        Args:
            team_id: The ID of the team.
            channel_id: The ID of the channel.
            message_id: The ID of the parent message.

        Returns:
            A list of dictionaries, where each dictionary is a reply message.
        """
        url = self._build_url(
            API_ENDPOINTS["msg_replies"],
            team_id=team_id,
            channel_id=channel_id,
            message_id=message_id,
        )
        response = self.session.get(url)
        validate_response(response)
        return response.json().get("value", [])

    def send_message_to_chat(
        self, chat_id: str, message: str, content_type: str
    ) -> Message:
        """Sends a message to a chat.

        Args:
            chat_id: ID of the chat to send a message to.
            message: The message content.
            content_type: Message type (e.g., 'text', 'html').

        Returns:
            A `Message` object representing the sent message.
        """
        url = self._build_url(
            API_ENDPOINTS["channel_messages"],
            version=VERSION_V1,
            chat_id=chat_id
        )
        self.session.headers.update(HEADERS)
        payload = json.dumps(
            {"body": {"contentType": content_type, "content": message}}
        )
        response = self.session.post(url, data=payload)
        validate_response(response)
        return self.parser.build_message_object(raw_json=response.json())

    def get_chat_messages(self, chat_id: str) -> list[Message]:
        """Gets chat messages from a specific chat.

        Args:
            chat_id: The ID of the chat.

        Returns:
            A list of `Message` objects.
        """
        url = self._build_url(
            API_ENDPOINTS["channel_messages"],
            version=VERSION_V1,
            chat_id=chat_id
        )
        self.session.headers.update(HEADERS)
        chat_messages = self._paginate_results(url=url)

        return [
            self.parser.build_message_object(raw_json=message)
            for message in chat_messages
        ]

    def check_account(self):
        """Gets information about the current account.

        Returns:
            A 'Me' object with account details.
        """
        url = self._build_url(
            API_ENDPOINTS["check_account"],
            version=VERSION_V1
        )
        response = self.session.get(url)
        validate_response(response)
        return self.parser.build_me_object(response.json())

    def get_chat_id(self, entity_identifier: str) -> str:
        """Gets the chat ID for a one-on-one chat.

        Args:
            entity_identifier: The user's identifier (e.g., email) to find the chat.

        Returns:
            The ID of the chat.
        """
        url = self._build_url(
            API_ENDPOINTS["list_channels_to_send_message"], version=VERSION_V1
        )
        response = self.session.get(url)
        validate_response(response)

        return self.parser.get_chat_ids(
            raw_json=response.json(), entity_identifier=entity_identifier
        )

    def get_chats(
        self,
        chat_type: str,
        filter_key: str,
        filter_value: str,
        filter_logic: str,
        limit: int,
    ) -> list[Chat]:
        """Gets all chats based on specified criteria.

        Args:
            chat_type: The type of chat ('meeting', 'group', 'oneOnOne', 'all').
            filter_key: The key to filter results by.
            filter_value: The value to match for the filter key.
            filter_logic: The filtering logic to apply.
            limit: The maximum number of chats to return.

        Returns:
            A list of filtered `Chat` objects.
        """
        chat_type_filter = CHAT_TYPES.get(chat_type)
        params = {"$expand": "members"}
        if chat_type_filter is not None:
            params["$filter"] = f"chatType eq '{chat_type_filter}'"

        url = self._build_url(API_ENDPOINTS["list_chats"], version=VERSION_V1)
        response = self.session.get(url, params=params)
        validate_response(response)
        return self.parser.build_chat_objects(
            raw_json=response.json(),
            filter_key=filter_key,
            filter_value=filter_value,
            filter_logic=filter_logic,
            limit=limit,
        )

    def create_channel(
        self,
        team_id: str,
        channel_name: str,
        channel_type: str,
        description: str
    ):
        """Creates a new channel in a team.

        Args:
            team_id: The ID of the team.
            channel_name: The name for the new channel.
            channel_type: The membership type of the channel.
            description: A description for the channel.

        Returns:
            A `Channel` object representing the new channel.
        """
        url = self._build_url(API_ENDPOINTS["create_channel"], team_id=team_id)
        payload = {
            "displayName": channel_name,
            "membershipType": channel_type,
            "description": description or "",
        }
        response = self.session.post(url, json=payload)
        validate_response(response, handle_client_error=True)
        return self.parser.build_channel_object(response.json())

    def delete_channel(self, team_id: str, channel_id: str) -> None:
        """Deletes a channel from a team.

        Args:
            team_id: The ID of the team.
            channel_id: The ID of the channel to delete.
        """
        url = self._build_url(
            API_ENDPOINTS["delete_channel"],
            team_id=team_id,
            channel_id=channel_id
        )
        response = self.session.delete(url)
        validate_response(response, handle_client_error=True)

    def add_user_to_channel(
        self, team_id: str, channel_id: str, user_id: str
    ) -> None:
        """Adds a user as a member to a specific channel.

        Args:
            team_id: The ID of the team containing the channel.
            channel_id: The ID of the channel to add the user to.
            user_id: The ID of the user to add.
        """
        url = self._build_url(
            API_ENDPOINTS["manage_channel_users"],
            team_id=team_id,
            channel_id=channel_id,
        )
        user_bind_url = self._build_url(
            API_ENDPOINTS["user_data_bind"], user_id=user_id
        )
        payload = {
            "@odata.type": "#microsoft.graph.aadUserConversationMember",
            "user@odata.bind": user_bind_url,
        }
        response = self.session.post(url, json=payload)
        validate_response(response, handle_client_error=True)

    def remove_user_from_channel(
        self, team_id: str, channel_id: str, user_id: str
    ) -> None:
        """Removes a user from a channel.

        Args:
            team_id: The ID of the team.
            channel_id: The ID of the channel.
            user_id: The ID of the user to remove.
        """
        url = self._build_url(
            API_ENDPOINTS["remove_user_from_channel"],
            team_id=team_id,
            channel_id=channel_id,
            user_id=user_id,
        )
        response = self.session.delete(url)
        validate_response(response, handle_client_error=True)

    def get_channel_users(self, team_id: str, channel_id: str) -> list:
        """Gets users from a particular channel.

        Args:
            team_id: The ID of the team.
            channel_id: The ID of the channel.

        Returns:
            A list of `User` objects.
        """
        url = self._build_url(
            API_ENDPOINTS["manage_channel_users"],
            team_id=team_id,
            channel_id=channel_id,
        )
        results = self._paginate_results(url=url)
        return self.parser.build_user_objects(results)

    def create_chat(self, user_ids: list[str]) -> Chat:
        """Creates a new chat conversation with one or more users.

        Args:
            user_ids: A list of user IDs to include in the chat.

        Returns:
            A `Chat` object parsed from the API response.
        """
        url = self._build_url(API_ENDPOINTS["manage_chats"])
        payload = {
            "chatType": "oneOnOne",
            "members": [
                {
                    "@odata.type": "#microsoft.graph.aadUserConversationMember",
                    "roles": ["owner"],
                    "user@odata.bind": self._build_url(
                        API_ENDPOINTS["user_data_bind"], user_id=user_id
                    ),
                }
                for user_id in user_ids
            ],
        }
        response = self.session.post(url, json=payload)
        validate_response(response, handle_client_error=True)
        return self.parser.build_chat_object(response.json())

    def send_message_reply(
        self,
        team_id: str,
        channel_id: str,
        message_id: str,
        content_type: str,
        content: str,
    ) -> Reply:
        """Sends a reply to a specific message in a channel.

        Args:
            team_id: The ID of the team.
            channel_id: The ID of the channel.
            message_id: The ID of the message to reply to.
            content_type: The type of the content (e.g., 'text', 'html').
            content: The content of the reply message.

        Returns:
            A `Reply` object representing the sent reply.

        Raises:
            requests.HTTPError: For HTTP-related errors.
            MicrosoftTeamsManagerError: For general manager errors.
            MicrosoftTeamsClientError: For client-side errors (e.g., 400).
            MicrosoftChannelNotFoundError: If the channel is not found.
        """
        payload = {"body": {"contentType": content_type, "content": content}}
        url = self._build_url(
            API_ENDPOINTS["send_message_reply"],
            version=VERSION_V1,
            team_id=team_id,
            channel_id=channel_id,
            message_id=message_id,
        )
        response = self.session.post(url, json=payload)
        validate_response(response, handle_client_error=True)
        return self.parser.build_send_message_reply(response.json())

    def _build_url(
        self, path_template: str, version: str | None = None, **kwargs
    ) -> str:
        """Constructs a full API URL from a path template and arguments."""
        keys_to_encode: Final[set[str]] = {
            "team_name", "channel_name", "user_name"
        }
        api_version = version or self.default_version
        kwargs["version"] = api_version
        encoded_kwargs = kwargs.copy()
        for key, value in encoded_kwargs.items():
            if key in keys_to_encode and isinstance(value, str):
                encoded_kwargs[key] = quote(value)
        formatted_path = path_template.format(**encoded_kwargs)
        return urljoin(self.api_root, formatted_path)
