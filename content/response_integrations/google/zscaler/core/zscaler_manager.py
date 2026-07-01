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

import copy
import requests
import json
from urllib.parse import urlparse

from TIPCommon.base.interfaces import Apiable
from TIPCommon.base.interfaces.logger import ScriptLogger
from TIPCommon.types import SingleJson

from ..core.auth import AuthenticatedSession
from ..core.constants import (
    BATCH_SIZE,
    ADD_WHITE_LIST_KEY,
    REMOVE_WHITE_LIST_KEY,
)
from ..core.data_models import IntegrationParameters
from ..core.exceptions import (
    ZscalerMissingError,
)
from ..core.utils import Logger, validate_response


class ZscalerManager(Apiable):
    """
    Zscaler Manager supporting both Legacy API Key Auth and OAuth 2.0 (OneAPI)
    """

    def __init__(
        self,
        authenticated_session: AuthenticatedSession,
        configuration: IntegrationParameters,
        logger: ScriptLogger,
    ) -> None:
        super().__init__(
            authenticated_session=authenticated_session,
            configuration=configuration,
        )
        self.authenticated_session: AuthenticatedSession = authenticated_session
        self.session: requests.Session = authenticated_session.session
        self.logger: Logger = Logger(logger)
        self.api_root: str = authenticated_session.api_root
        self.use_oauth: bool = authenticated_session.use_oauth
        self.use_legacy: bool = authenticated_session.use_legacy

    def test_connectivity(self) -> bool:
        """
        Test connectivity to Zscaler
        :return: {bool} True if successfully connected, Exception otherwise.
        """
        res: requests.Response
        if self.use_oauth:
            res = self.session.get(f"{self.api_root}/status")
        else:
            res = self.session.get(f"{self.api_root}/authenticatedSession")

        validate_response(res)
        return True

    def get_blacklist_items(self) -> SingleJson:
        """
        Gets a list of black-listed URLs
        :return: {dict} that includes list of black-listed URLs {strings} or none
        """
        res: requests.Response = self.session.get(f"{self.api_root}/security/advanced")
        validate_response(res)
        return res.json()

    def add_to_blacklist(self, url: str) -> None:
        """
        Adds a URL to black list.
        The action applied to the Advanced Threat Protection policys blacklist
        :param url: {str} url to be added
        """
        request_url: str = (
            f"{self.api_root}/security/advanced/blacklistUrls?action=ADD_TO_LIST"
        )
        res: requests.Response = self.session.post(
            request_url, json.dumps({"blacklistUrls": [url]})
        )

        validate_response(res)

    def add_multiple_to_blacklist(self, urls: list[str]) -> None:
        """Adds multiple URLs to the blacklist.

        The action applied to the Advanced Threat Protection policy's blacklist.

        Args:
            urls (list[str]): List of URLs to be added.
        """
        if not urls:
            return

        request_url = (
            f"{self.api_root}/security/advanced/blacklistUrls?action=ADD_TO_LIST"
        )
        res = self.session.post(request_url, json={"blacklistUrls": urls})

        validate_response(res)

    def remove_from_blacklist(
        self, url: str, blacklist_urls: list[str] | None = None
    ) -> None:
        """
        removes a URL from the black list.
        The action applied to the Advanced Threat Protection policys blacklist
        :param url: {str} url to be removed
        :param blacklist_urls: {list} optional list of blacklisted URLs
        """
        # check if the url is blacklisted
        urls: list[str] = (
            blacklist_urls
            if blacklist_urls is not None
            else (self.get_blacklist_items().get("blacklistUrls") or [])
        )
        if url not in urls:
            raise ZscalerMissingError("Given host address is not blacklisted")

        request_url: str = (
            f"{self.api_root}/security/advanced/blacklistUrls?action=REMOVE_FROM_LIST"
        )
        res: requests.Response = self.session.post(
            request_url, json={"blacklistUrls": [url]}
        )

        validate_response(res)

    def remove_multiple_from_blacklist(
        self,
        urls: list[str],
    ) -> tuple[list[str], list[str]]:
        """Removes multiple URLs from the black list.

        The action applied to the Advanced Threat Protection policy's blacklist.

        Args:
            urls (list[str]): List of URLs to be removed.

        Returns:
            tuple[list[str], list[str]]: A tuple containing successful URLs
                and failed URLs.
        """
        if not urls:
            return [], []

        blacklisted = set(self.get_blacklist_items().get("blacklistUrls", []))
        valid_urls = [url for url in urls if url in blacklisted]
        invalid_urls = [url for url in urls if url not in blacklisted]

        if valid_urls:
            request_url = (
                f"{self.api_root}/security/advanced/"
                "blacklistUrls?action=REMOVE_FROM_LIST"
            )
            res = self.session.post(request_url, json={"blacklistUrls": valid_urls})
            validate_response(res)

        return valid_urls, invalid_urls

    def get_whitelist_items(self) -> SingleJson:
        """
        Gets a list of white-listed URLs
        :return: {dict} that includes list of white-listed URLs {strings}
        """
        res: requests.Response = self.session.get(f"{self.api_root}/security")
        validate_response(res)
        return res.json()

    def update_to_whitelist(
        self, url: str, action: str, whitelist_urls: list[str] | None = None
    ) -> None:
        """
        Updates the list of white-listed URLs.
        :param url: {string} url
        :param action: {string} add or remove from whitelist
        :param whitelist_urls: {list} optional list of whitelisted URLs
        """

        url_list: list[str] = (
            whitelist_urls
            if whitelist_urls is not None
            else (self.get_whitelist_items().get("whitelistUrls") or [])
        )
        new_url_list: list[str] = copy.copy(url_list)
        if url not in url_list:
            if action == ADD_WHITE_LIST_KEY:
                new_url_list.append(url)
            if action == REMOVE_WHITE_LIST_KEY:
                raise ZscalerMissingError("Given host address is not whitelisted")

        if url in url_list:
            if action == REMOVE_WHITE_LIST_KEY:
                new_url_list.remove(url)
            if action == ADD_WHITE_LIST_KEY:
                raise ZscalerMissingError("Given host address is already whitelisted")

        request_url: str = f"{self.api_root}/security"
        res: requests.Response = self.session.put(
            request_url, json={"whitelistUrls": new_url_list}
        )

        validate_response(res)

    def update_multiple_to_whitelist(
        self,
        urls: list[str],
        action: str,
    ) -> tuple[list[str], list[str]]:
        """Updates the list of white-listed URLs.

        Args:
            urls (list[str]): List of URLs to update.
            action (str): The action to perform (e.g., ADD_WHITE_LIST_KEY
                or REMOVE_WHITE_LIST_KEY).

        Returns:
            tuple[list[str], list[str]]: A tuple containing successful URLs
                and failed URLs.
        """
        if not urls:
            return [], []

        url_list = self.get_whitelist_items().get("whitelistUrls") or []
        whitelist_set = set(url_list)

        valid_urls = []
        invalid_urls = []

        for url in urls:
            if action == ADD_WHITE_LIST_KEY:
                if url not in whitelist_set:
                    whitelist_set.add(url)
                    valid_urls.append(url)
                else:
                    invalid_urls.append(url)
            elif action == REMOVE_WHITE_LIST_KEY:
                if url in whitelist_set:
                    whitelist_set.remove(url)
                    valid_urls.append(url)
                else:
                    invalid_urls.append(url)

        if valid_urls:
            request_url = f"{self.api_root}/security"
            res = self.session.put(
                request_url, json={"whitelistUrls": list(whitelist_set)}
            )
            validate_response(res)

        return valid_urls, invalid_urls

    def add_multiple_to_whitelist(self, urls: list[str]) -> tuple[list[str], list[str]]:
        """Adds multiple URLs to whitelist."""
        return self.update_multiple_to_whitelist(urls, ADD_WHITE_LIST_KEY)

    def remove_multiple_from_whitelist(
        self, urls: list[str]
    ) -> tuple[list[str], list[str]]:
        """Removes multiple URLs from whitelist."""
        return self.update_multiple_to_whitelist(urls, REMOVE_WHITE_LIST_KEY)

    def list_url_categories(self) -> list[SingleJson]:
        """
        Gets information about all URL categories.
        :return: {list} of url category and its urls {dict}
        """
        res: requests.Response = self.session.get(f"{self.api_root}/urlCategories")
        validate_response(res)
        return res.json()

    def get_sandbox_report(self, md5_hash: str) -> SingleJson:
        """
        Get a full or summary detail report for an MD5 hash of a file
        that was analyzed by Sandbox.
        :param md5_hash: {string}
        :return:
        """
        request_url: str = f"{self.api_root}/sandbox/report/{md5_hash}?details=full"
        res: requests.Response = self.session.get(request_url)
        validate_response(res)
        response: SingleJson = res.json()
        if not isinstance(response.get("Full Details"), dict):
            return {}
        return response

    def lookup_url(self, url: str) -> list[SingleJson]:
        """
        Look up the categorization of the given set of URLs.
        Up to 100 URLs can be looked up per request, and a URL cannot
        exceed 1024 characters.
        :return: {list} of found urls {dict}
        """
        res: requests.Response = self.session.post(
            f"{self.api_root}/urlLookup", json=[url]
        )
        validate_response(res)
        return res.json()

    def lookup_urls(self, urls: list[str]) -> list[SingleJson]:
        """
        Look up the categorization of the given set of URLs.
        Up to 100 URLs can be looked up per request, and a URL cannot
        exceed 1024 characters.
        :return: {list} of found urls {dict}
        """

        def divide_chunks(data: list[str], chunk_size: int):
            """
            A generator for dividing a list to chunks of given size
            :param data: {list} List of items
            :param chunk_size: {int} Size of the chunks
            :yields: {list} The generated chunks
            """
            for i in range(0, len(data), chunk_size):
                yield data[i : i + chunk_size]

        results: list[SingleJson] = []
        for chunk in divide_chunks(urls, BATCH_SIZE):
            res: requests.Response = self.session.post(
                f"{self.api_root}/urlLookup", json=chunk
            )
            validate_response(res)
            results.extend(res.json())

        return results

    def activate_changes(self) -> SingleJson:
        """
        Activates configuration changes. (e.g. add to blacklist)
        :return: {dict} activates status {string}
        """
        request_url: str = f"{self.api_root}/status/activate"
        res: requests.Response = self.session.post(request_url)
        validate_response(res)
        return res.json()

    def get_activate_status(self) -> str:
        """
        Gets the activation status for a configuration change.
        :return: {string} activates status
        """
        request_url: str = f"{self.api_root}/status"
        res: requests.Response = self.session.get(request_url)
        validate_response(res)
        return res.json().get("status")

    @staticmethod
    def validate_and_extract_url(url: str) -> str:
        """
        Validates a URL and extracts its network location.

        This method checks if a given URL starts with a valid scheme (e.g.,
        "http://", "https://", "ftp://", "ftps://", "ssh://", "git://", "smb://",
        "ldap://", "file://", "ws://", "wss://", "svn://", "rsync://"). If not,
        it assumes "http://" as the default scheme. The network location (netloc)
        is extracted from the
        provided or modified URL after stripping any "www." prefix. If no valid
        network location is found, the method returns the input URL.

        Args:
            url (str): The URL to validate and extract the network location from.

        Returns:
            str: The network location (netloc) part of the URL without the "www."
            prefix, or the input URL if no netloc is found.
        """
        url_lower: str = url.lower()

        if not url_lower.startswith(
            (
                "http://",
                "https://",
                "ftp://",
                "ftps://",
                "ssh://",
                "git://",
                "smb://",
                "ldap://",
                "file://",
                "ws://",
                "wss://",
                "svn://",
                "rsync://",
            )
        ):
            url_to_parse: str = f"http://{url}"
        else:
            url_to_parse: str = url

        netloc: str = urlparse(url_to_parse).netloc

        if netloc:
            return netloc.lstrip("www.")

        return url
