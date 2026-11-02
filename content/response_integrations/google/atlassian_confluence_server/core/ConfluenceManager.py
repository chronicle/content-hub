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

"""Manager module for Atlassian Confluence Server Integration."""
from __future__ import annotations

from typing import Any
from urllib import parse
import requests

from .ConfluenceParser import ConfluenceParser
from soar_sdk.SiemplifyLogger import SiemplifyLogger

from .constants import (
    API_BAD_REQUEST,
    API_NOT_FOUND,
    API_SERVER_ERROR,
    API_UNAUTHORIZED_ERROR,
    ENDPOINTS,
)
from .exceptions import (
    ConfluenceBadRequestError,
    ConfluenceHTTPError,
    ConfluencePATAuthenticationError,
    ConfluenceValidationError,
)
from .utils import filter_items


class ConfluenceManager:
    """Manager class for Confluence connection instance."""

    def __init__(
        self,
        server_address: str,
        username: str,
        password: str,
        api_token: str,
        verify_ssl: bool = False,
        logger: SiemplifyLogger = None,
        ping: bool = False,
    ) -> None:
        """Connect to a Confluence instnace."""
        self.server_address = server_address
        self.username = username.encode("utf-8") if username else None
        self.password = password
        self.token = api_token
        self.logger = logger
        self.ping = ping
        self.session = requests.session()
        self.session.verify = verify_ssl
        self._authenticate()
        self.parser = ConfluenceParser()

    def _authenticate(self):
        """The method is used to authenticate request use token or, username
        and password.

        return: None or raise ConfluenceValidationError exception
        """
        if not self.token and not (self.username and self.password):
            raise ConfluenceValidationError(
                "Failed to connect to Atlassian Confluence Server, expecting"
                " either username and password, or personal access token to "
                "connect with!"
            )

        if self.token:
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            self.session.auth = (self.username, self.password)

    def _get_full_url(
        self,
        url_id: str,
        query_params: dict[str, Any] | None = None,
        **params: dict[str, Any],
    ) -> str:
        """Get full url from url identifier.

        Args:
            url_id: {str} The id of url
            query_params: {dict} Variables passed for string formatting
            **params: dict variable for unpacking params

        Returns:
            {str} The full url
        """
        query_params = query_params or {}

        full_url = parse.urljoin(
            self.server_address, ENDPOINTS[url_id].format(**params)
        )
        # update query params
        url_parts = list(parse.urlparse(full_url))
        query = dict(parse.parse_qsl(url_parts[4]))
        query.update(query_params)
        url_parts[4] = parse.urlencode(query)

        return parse.urlunparse(url_parts)

    def _get_next_page_url(self, next_cursor_url: str) -> str:
        """Get next page url.

        Args:
            next_cursor_url: {str} The url to send request to

        Returns:
            {str} Full url for next page
        """
        return parse.urljoin(self.server_address, next_cursor_url)

    def _paginate_results(
        self,
        full_url: str,
        limit: int | None = None,
        filter_key: str | None = None,
        filter_logic: str | None = None,
        filter_value: str | None = None,
    ) -> list[dict[str, Any]]:
        """Paginate the results.

        Args:
            full_url: {str} The url to send request to
            limit: {int} The limit of the results to fetch
            filter_key: {str} [Title, Space Name, Status]
            filter_logic: {str} [Equal, Contains]
            filter_value: {str}

        Returns:
            {list} List of results
        """
        results, next_cursor_url, response = [], None, None

        while True:
            if response:
                if not next_cursor_url or (limit is not None and len(results) > limit):
                    break

                full_url = self._get_next_page_url(next_cursor_url)
            params = {"limit": limit}

            response = self.session.get(full_url, params=params)
            self.validate_response(response)

            next_cursor_url = self.parser.get_next_cursor(response.json())
            results.extend(
                filter_items(
                    items=[
                        self.parser.build_siemplify_list_object(res)
                        for res in response.json().get("results")
                    ],
                    filter_key=filter_key,
                    filter_logic=filter_logic,
                    filter_value=filter_value,
                    limit=limit,
                )
            )

        return results[:limit] if limit else results

    def test_connectivity(self) -> None:
        """Test connectivity to Confluence Server.

        Returns:
            {bool} True if successful, exception otherwise
        """
        params = {"limit": 1}
        response = self.session.get(self._get_full_url("ping", **params))
        self.validate_response(response)

    def validate_response(
        self,
        response: requests.Response,
        error_msg: str | None = None,
        is_api_page_by_id: bool = False,
    ) -> None:
        """Validate response of the API request.

        Args:
            response: {requests.Response} The response to validate
            error_msg: error message for get_page_by_id
            is_api_page_by_id: boolean

        Returns:
            boolean

        Raises:
            ConfluenceBadRequestError|ConfluenceHTTPError|
            ConfluencePATAuthenticationError
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            if (
                response.status_code == API_BAD_REQUEST
                or response.status_code == API_SERVER_ERROR
            ):
                raise ConfluenceBadRequestError(
                    self.get_api_error_message(error)
                ) from error

            if response.status_code == API_UNAUTHORIZED_ERROR:
                raise ConfluenceHTTPError(error)

            msg = ""
            try:
                msg = response.json()["message"]
            except requests.JSONDecodeError:
                if is_api_page_by_id:
                    return

            if not (is_api_page_by_id and msg == error_msg):
                raise ConfluenceHTTPError(self.get_api_error_message(error)) from error

        if self.ping and self.token and not response.json()["results"]:
            raise ConfluencePATAuthenticationError("Personal Access Token is invalid.")

    def get_api_error_message(self, exception) -> str:
        """Get API error message.

        Args:
            exception: {Exception} The api error

        Returns:
            {str} error message
        """
        try:
            return self.parser.extract_error_message(exception.response.json())
        except Exception:
            exception_response = exception.response.content.decode()
            if exception_response:
                return exception_response
            else:

                return str(exception)

    def get_child_pages(self, page_id: str, limit: int) -> dict[str, Any]:
        """Getting child pages with max limit from Confluence Server.

        Args:
            page_id: Specify the page id to return.
            limit: Specify the limit of child pages to return.

        Returns:
            Dict: Dict Object if successful, exception otherwise
        """
        params = {"page_id": page_id, "limit": limit}
        response = self.session.get(self._get_full_url("get_child_pages", **params))
        self.validate_response(response)

        return self.parser.build_siemplify_child_object(response.json())

    def list_pages(
        self, limit: int, filter_key: str, filter_logic: str, filter_value: str
    ) -> dict[str, Any]:
        """Getting list pages with max limit from Confluence Server.

        Args:
            limit: {int} The limit of the results to fetch
            filter_key: {str} [Title, Space Name, Status]
            filter_logic: {str} [Equal, Contains]
            filter_value: {str}

        Returns:
            Dict: Dict Object if successful, exception otherwise
        """
        params = {"limit": limit}

        return self._paginate_results(
            full_url=self._get_full_url("list_pages", **params),
            limit=limit,
            filter_key=filter_key,
            filter_logic=filter_logic,
            filter_value=filter_value,
        )

    def get_page_comment_page(
        self, page_id: str, expand: str, limit: int
    ) -> dict[str, Any]:
        """Getting page comment with max limit from Confluence Server.

        Args:
            page_id: Specify the page id to return.
            expand: expand parameter to return additional information
             about the page.
            limit: Specify the limit of child pages to return.

        Returns:
            Dict: Dict Object if successful, exception otherwise
        """
        params = {"page_id": page_id, "expand": expand, "limit": limit}
        response = self.session.get(self._get_full_url("get_page_comments", **params))
        self.validate_response(response)

        return self.parser.build_siemplify_comment_object(response.json())

    def get_page_by_id(
        self, page_id: str, expand: str = "body.storage"
    ) -> dict[str, Any]:
        """Get Atlassian Confluence Server page by id.

        Args:
            page_id: Specify the page id to return.
            expand: Specify the expand parameter to
              return additional information about the page.
              Parameter accepts multiple values as a comma separated list.
              By default with body.storage the content of the page is fetched.

        Returns:
            Dict: Dict Object if successful, exception otherwise
        """
        params = {"page_id": page_id, "expand": expand}

        response = self.session.get(self._get_full_url("get_page_by_id", **params))
        error_msg = f"No content found with id: ContentId{{id={page_id}}}"
        self.validate_response(response, error_msg=error_msg, is_api_page_by_id=True)
        if response.status_code == API_NOT_FOUND:
            response_dict = {"message": error_msg}

            return self.parser.build_siemplify_page_object(response_dict)

        return self.parser.build_siemplify_page_object(response.json())
