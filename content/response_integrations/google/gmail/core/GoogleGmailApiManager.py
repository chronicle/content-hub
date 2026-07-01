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

import base64
import json
import time

from email.mime.multipart import MIMEMultipart
from urllib.parse import urljoin

import aiohttp
import aiohttp.client_exceptions
from google.auth.exceptions import RefreshError, TransportError
from google.auth.transport._aiohttp_requests import AuthorizedSession

from TIPCommon.base.interfaces import Apiable
from TIPCommon.rest.gcp import get_workload_sa_email
from TIPCommon.types import SingleJson

from ..core.GoogleGmailConsts import (
    INVALID_ARGUMENT,
    INTERNAL_SERVER_ERROR,
    MAX_LIST_RESULTS,
    NOT_FOUND,
    PERMISSION_DENIED,
    PROJECT_LOOKUP_ERROR_MESSAGE,
    THROTTLING_OVERLOAD_MESSAGE,
)
from ..core.GoogleGmailExceptions import (
    GoogleCloudAuthenticationError,
    GoogleGmailInvalidRequestArgumentError,
    GoogleGmailNotFoundError,
    GoogleGmailManagerError,
    GoogleGmailPermissionDeniedError,
    GoogleGmailProjectLookupError,
    GoogleGmailThrottlingOverloaded,
)
from ..core.GoogleGmailUtils import get_auth_request_async, extract_body


# ============================= CONSTS ===================================== #
API_URL = "https://gmail.googleapis.com"
ENDPOINTS = {
    "users.messages.list": "/gmail/v1/users/{user_email}/messages",
    "users.messages.details": "/gmail/v1/users/{user_email}/messages/{message_id}",
    "users.messages.trash": "/gmail/v1/users/{user_email}/messages/{message_id}/trash",
    "users.messages.attachments.details": (
        "gmail/v1/users/{user_email}/messages/{message_id}/attachments/{id}"
    ),
    "users.messages.batchModify": "gmail/v1/users/{user_email}/messages/batchModify",
    "users.labels.create": "/gmail/v1/users/{user_email}/labels",
    "users.labels.list": "/gmail/v1/users/{user_email}/labels",
    "users.messages.send": "gmail/v1/users/{user_email}/messages/send",
    "users.threads.get": "gmail/v1/users/{user_email}/threads/{thread_id}"
}
# ============================= CLASSES ===================================== #


def throttling_decorator(retries: int, cooldown: int = 1):
    """Throttling decorator to retry API calls when quota is exhausted."""
    def inner_decorator(func):
        async def wrapped(*args, **kwargs):
            _tries = 0

            while True:
                try:
                    return await func(*args, **kwargs)
                except (
                    GoogleGmailThrottlingOverloaded,
                    aiohttp.client_exceptions.ClientConnectionError
                ):
                    if _tries >= retries:
                        raise

                time.sleep(cooldown)
                _tries += 1

        return wrapped
    return inner_decorator


def auth_handler(func):
    """Auth handling decorator, to catch and reraise auth related errors."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)

        except (RefreshError, TransportError) as e:
            workload_sa_email = get_workload_sa_email("Unknown Principal")
            if "Invalid email or User ID" in str(e):
                try:
                    error_json = json.loads(
                        ("{" + str(e).split("{", 1)[-1][:-1])
                        .replace("'", "\"")
                    )
                    raise GoogleGmailNotFoundError(
                        error_json["error_description"]
                    ) from e

                except (KeyError, IndexError, json.JSONDecodeError):
                    raise GoogleGmailNotFoundError(str(e)) from e

            raise GoogleCloudAuthenticationError(
                "Impersonation is not allowed for the provided service "
                f"account. Please check the \"Service Account Token Creator\" role "
                f"to the service account: {workload_sa_email} if Workload Identity "
                f"is enabled. Please also verify that your Service Account is "
                f"authorized in Google Workspace for all the necessary scopes. "
                f"For more information please refer to documentation."
            ) from e

    return wrapper


class GoogleGmailApiManager(Apiable):
    """
    Google Gmail API Manager
    """

    def __init__(
            self,
            session: AuthorizedSession,
    ):
        self.session = session

    def _get_full_url(
            self,
            url_key: str,
            postfix: str = None,
            **kwargs
    ) -> str:
        """
        Get full url from url key.

        Args:
            url_id: {str} The key of url
            postfix: {str} The postfix to add to the url path
            kwargs: {dict} Key value arguments passed for string formatting

        Returns:
            {str} The full url
        """
        url = ENDPOINTS[url_key].format(**kwargs)
        full_url = urljoin(API_URL, url)
        if postfix is not None:
            full_url += postfix

        return full_url

    @classmethod
    async def validate_response(
            cls,
            response: aiohttp.ClientResponse,
            error_msg: str = "An error occurred"
    ) -> None:
        """Validate API response.

        Args:
            response: {requests.Response} The response to validate
            error_msg: {str} Default message to display on error

        Raises:
            GoogleGmailThrottlingOverloaded: If the API is overloaded
            GoogleGmailProjectLookupError: If the project lookup failed
            GoogleGmailInvalidRequestArgumentError: If the request is invalid
            GoogleGmailNotFoundError: If the resource is not found
            GoogleGmailManagerError: If the API call failed
        """
        response_text = await extract_body(response)
        try:
            response.raise_for_status()
        except aiohttp.ClientResponseError as error:
            try:
                response_json = json.loads(response_text)
                error_json = response_json.get("error", {})
                message = error_json.get("message")
                status = error_json.get("status")
                error_details = "; ".join(
                    el.get("detail") for el in error_json.get("details", [])
                    if el.get("detail") is not None
                )

                if (
                    status == INTERNAL_SERVER_ERROR and
                    THROTTLING_OVERLOAD_MESSAGE in error_details
                ):
                    raise GoogleGmailThrottlingOverloaded(
                        f"{error_msg}: {error} {error_details}"
                    ) from error

                if status == PERMISSION_DENIED:
                    if PROJECT_LOOKUP_ERROR_MESSAGE in message:
                        raise GoogleGmailProjectLookupError(
                            f"{error_msg}: {error} {message or response_text}"
                        ) from error

                    raise GoogleGmailPermissionDeniedError(
                        f"{error_msg}: {error} {error_details}"
                    ) from error

                if status == INVALID_ARGUMENT:
                    raise GoogleGmailInvalidRequestArgumentError(
                        f"{error_msg}: {error} {message or response_text}"
                    ) from error

                if status == NOT_FOUND:
                    raise GoogleGmailNotFoundError(
                        f"{error_msg}: {error} {message or response_text}"
                    ) from error

                raise GoogleGmailManagerError(
                    f"{error_msg}: {error} {message or response.text}"
                ) from error

            except json.JSONDecodeError as e:
                raise GoogleGmailManagerError(
                    f"{error_msg}: {error} {response_text}"
                ) from e

    @auth_handler
    async def test_connectivity(self):
        """Test connectivity with Google Gmail."""
        # pylint: disable=protected-access
        # Unfortunately that's the only way to extract it
        auth_request = get_auth_request_async(self.session.connector._ssl)
        await self.session.credentials.refresh(
            request=auth_request
        )
        await auth_request.session.close()

    @throttling_decorator(retries=3)
    @auth_handler
    async def list_messages(
            self,
            user_email: str,
            max_results: int | None = None,
            query: str | None = None
    ) -> list[str]:
        """List all messages for a specific user.

        Args:
            user_email: Email address of the user to fetch emails for.
            max_results: Maximum number of emails to be returned
            query: Query to filter email messages with.

        Returns:
            List of email message IDs
        """

        params = {
            "maxResults": max_results if max_results is not None else MAX_LIST_RESULTS,
            "includeSpamTrash": "true",
        }
        if query is not None:
            params["q"] = query

        message_ids = []

        while max_results is None or len(message_ids) < max_results:
            response = await self.session.request(
                "GET",
                self._get_full_url("users.messages.list", user_email=user_email),
                params=params
            )
            await self.validate_response(response)
            response_json = json.loads(await extract_body(response))
            if "messages" not in response_json:
                break

            message_ids.extend([
                message["id"] for message in response_json["messages"]
            ])
            if "nextPageToken" not in response_json:
                break

            params["pageToken"] = response_json["nextPageToken"]

        return (
            message_ids if max_results is None
            else message_ids[:max_results]
        )

    @throttling_decorator(retries=3)
    @auth_handler
    async def get_thread(
            self,
            user_email: str,
            thread_id: str,
            format_: str = "full",
            metadata_headers: list[str] | None = None
    ) -> SingleJson:
        """Get thread details by thread ID.

        Args:
            user_email: Email address of the user to fetch emails for.
            thread_id: The email thread ID
            format_: Message format for enrichment.
                Possible values: "full" (default), "minimal", "raw", "metadata"
            metadata_headers: When given and format is METADATA, only include
                headers specified.

        Returns:
            Message details JSON data
        """
        params = {"format": format_}
        if metadata_headers is not None:
            params["metadataHeaders"] = metadata_headers

        response = await self.session.request(
            "GET",
            self._get_full_url(
                "users.threads.get",
                user_email=user_email,
                thread_id=thread_id
            ),
            params=params
        )
        await self.validate_response(response)
        return json.loads(await extract_body(response))

    @throttling_decorator(retries=3)
    @auth_handler
    async def get_message(
            self,
            user_email: str,
            message_id: str,
            format_: str = "full",
            metadata_headers: list[str] | None = None
    ) -> SingleJson:
        """Get message details by message ID.

        Args:
            user_email: Email address of the user to fetch emails for.
            message_id: The email message ID
            format_: Message format for enrichment.
                Possible values: "full" (default), "minimal", "raw", "metadata"
            metadata_headers: When given and format is METADATA, only include
                headers specified.

        Returns:
            Message details JSON data
        """
        params = {"format": format_}
        if metadata_headers is not None:
            params["metadataHeaders"] = metadata_headers

        response = await self.session.request(
            "GET",
            self._get_full_url(
                "users.messages.details",
                user_email=user_email,
                message_id=message_id
            ),
            params=params
        )
        await self.validate_response(response)
        return json.loads(await extract_body(response))

    @throttling_decorator(retries=3)
    @auth_handler
    async def get_attachment(
            self,
            user_email: str,
            message_id: str,
            attachment_id: str
    ) -> SingleJson:
        """Get message attachment by message and attachment IDs.

        Args:
            user_email: Email address of the user to fetch emails for.
            message_id: The email message ID
            attachment_id: The attachment ID

        Returns:
            Message details JSON data
        """
        response = await self.session.request(
            "GET",
            self._get_full_url(
                "users.messages.attachments.details",
                user_email=user_email,
                message_id=message_id,
                id=attachment_id
            )
        )
        await self.validate_response(response)
        return json.loads(await extract_body(response))

    @throttling_decorator(retries=3)
    @auth_handler
    async def batch_modify(
            self,
            user_email: str,
            message_ids: list[str],
            add_label_ids: list[str] = None,
            remove_label_ids: list[str] = None
    ) -> None:
        """Batch modify messages.

        Args:
            user_email: Email address of the user mailbox
            message_ids: Message IDs for the updated
            add_label_ids: Label IDs to be added
            remove_label_ids: Label IDs to be removed
        """
        payload = {
            "ids": message_ids
        }

        if add_label_ids:
            payload["addLabelIds"] = add_label_ids
        if remove_label_ids:
            payload["removeLabelIds"] = remove_label_ids

        response = await self.session.request(
            "POST",
            url=self._get_full_url(
                "users.messages.batchModify",
                user_email=user_email
            ),
            json=payload
        )
        await self.validate_response(response)

    @throttling_decorator(retries=3)
    @auth_handler
    async def delete_message(
            self,
            user_email: str,
            message_id: str
    ) -> None:
        """Delete message details by message ID.

        Args:
            user_email: Email address of the user to fetch emails for.
            message_id: The email message ID

        Returns:
            Message details JSON data
        """
        response = await self.session.request(
            "DELETE",
            self._get_full_url(
                "users.messages.details",
                user_email=user_email,
                message_id=message_id
            )
        )
        await self.validate_response(response)

    @throttling_decorator(retries=3)
    @auth_handler
    async def trash_message(
            self,
            user_email: str,
            message_id: str
    ) -> None:
        """Trash message details by message ID.

        Args:
            user_email: Email address of the user to fetch emails for.
            message_id: The email message ID

        Returns:
            Message details JSON data
        """
        response = await self.session.request(
            "POST",
            self._get_full_url(
                "users.messages.trash",
                user_email=user_email,
                message_id=message_id
            )
        )
        await self.validate_response(response)

    @throttling_decorator(retries=3)
    @auth_handler
    async def create_label(self, user_email: str, label_name: str) -> SingleJson:
        """Creates a new label in Gmail.

        Args:
            user_email: Email address of the user to create label for
            label_name: Name of the label

        Returns:
            Label details JSON data
        """
        response = await self.session.request(
            "POST",
            self._get_full_url(
                "users.labels.create",
                user_email=user_email
            ),
            json={
                "name": label_name,
                "type": "user"
            }
        )
        await self.validate_response(response)
        return json.loads(await extract_body(response))

    @throttling_decorator(retries=3)
    @auth_handler
    async def list_labels(
            self,
            user_email: str
    ) -> list[SingleJson]:
        """List labels from Google Gmail for specific user.

        Args:
            user_email: Email address of the user to fetch labels for.

        Returns:
            List of labels in JSON. Note that each label resource only contains an
            id, name, messageListVisibility, labelListVisibility, and type.
        """
        response = await self.session.request(
            "GET",
            self._get_full_url(
                "users.labels.list",
                user_email=user_email
            )
        )
        await self.validate_response(response)
        return json.loads(await extract_body(response))["labels"]

    @auth_handler
    async def send_email(
        self,
        sender: str,
        message: MIMEMultipart
    ):
        """
        Send email with the specified arguments

        Args:
            sender: Email mailbox to send the email from
            message: Message to be sent

        Returns:
            Message details JSON data
        """

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        response = await self.session.request(
            "POST",
            self._get_full_url("users.messages.send", user_email=sender),
            json={"raw": encoded_message}
        )

        await self.validate_response(response)
        return json.loads(await extract_body(response))

    async def close(self) -> None:
        """Close the session to Gmail API."""
        await self.session.close()
