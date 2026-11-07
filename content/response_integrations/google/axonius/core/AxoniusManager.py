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
from copy import deepcopy
import re
from typing import Optional, List, Tuple, Union
from urllib.parse import urljoin

import requests
from requests import Session

from soar_sdk.SiemplifyLogger import SiemplifyLogger
from soar_sdk.SiemplifyUtils import unix_now
from .consts import (
    INTEGRATION_IDENTIFIER,
    LOGICAL_OR,
    AUTHORIZATION_ERROR_STATUS_CODE,
    FORBIDDEN_ERROR_STATUS_CODE,
)
from .datamodels import (
    UserGeneralAttribute,
    UserDetailedInformation,
    DeviceGeneralAttribute,
    DeviceDetailedInformation,
    UserNote,
    DeviceNote,
)
from .exceptions import (
    AxoniusManagerError,
    AxoniusManagerMandatoryParametersError,
    AxoniusAuthorizationError,
    AxoniusForbiddenError,
)
from .parser import AxoniusTransformationLayer

ENDPOINTS = {
    "ping": "/api/V4.0/settings/meta/about",
    "get_users": "/api/V4.0/users",
    "get-user-details": "/api/V4.0/users/{internal_axonius_id}",
    "get-devices": "/api/V4.0/devices",
    "get-device-details": "/api/V4.0/devices/{internal_axonius_id}",
    "add-tags-to-users": "/api/V4.0/users/labels",
    "add-tags-to-devices": "/api/V4.0/devices/labels",
    "remove-tags-from-users": "/api/V4.0/users/labels",
    "remove-tags-from-devices": "/api/V4.0/devices/labels",
    "add-note-to-user": "/api/V4.0/users/{internal_axonius_id}/notes",
    "add-note-to-device": "/api/V4.0/devices/{internal_axonius_id}/notes",
}

HEADERS = {"Content-Type": "application/json"}

DEFAULT_CONNECT_TIMEOUT = 10
DEFAULT_READ_TIMEOUT = 60
DEFAULT_REQUEST_TIMEOUT: Tuple[float, float] = (
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_READ_TIMEOUT,
)
MIN_REQUEST_TIMEOUT = 5.0
DEADLINE_SAFETY_BUFFER_MS = 5000
DEFAULT_QUERY_BATCH_SIZE = 50
MIN_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 2000
PAGE_LIMIT_MULTIPLIER = 10


class AxoniusManager:
    """
    Axonius Manager
    """

    def __init__(
        self,
        api_root: str,
        api_key: str,
        secret_key: str,
        verify_ssl: Optional[bool] = True,
        siemplify_logger: Optional[SiemplifyLogger] = None,
        timeout: Union[Tuple[float, float], float] = DEFAULT_REQUEST_TIMEOUT,
        execution_deadline_ms: Optional[int] = None,
    ) -> None:
        """
        The method is used to instantiate an object of AxoniusManager class
        :param api_root: {str} The API root of the Axonius instance.
        :param api_key: {str} The API key of the Axonius instance.
        :param secret_key: {str} The API secret key of the Axonius instance.
        :param verify_ssl: {bool} True if to verify the SSL certificate for the connection to the Axonius server.
            Otherwise False
        """
        self._api_root: str = api_root[:-1] if api_root.endswith("/") else api_root
        self._session: Session = requests.Session()
        self._session.verify = verify_ssl
        self._session.headers = deepcopy(HEADERS)
        self._session.headers.update({"api-key": api_key, "api-secret": secret_key})
        self._timeout: Union[Tuple[float, float], float] = timeout
        self._execution_deadline_ms: Optional[int] = execution_deadline_ms

        self.parser: AxoniusTransformationLayer = AxoniusTransformationLayer()
        self.siemplify_logger: Optional[SiemplifyLogger] = siemplify_logger

    def _log_info(self, message: str) -> None:
        if self.siemplify_logger:
            self.siemplify_logger.info(message)

    def _get_request_timeout(self) -> Union[Tuple[float, float], float]:
        """
        Calculate bounded HTTP timeout respecting the SOAR action execution deadline when set.
        :return: {tuple|float} Connect/read timeout for requests
        """
        if not self._execution_deadline_ms or self._execution_deadline_ms <= 0:
            return self._timeout
        remaining_sec = (
            self._execution_deadline_ms - DEADLINE_SAFETY_BUFFER_MS - unix_now()
        ) / 1000.0
        bounded_sec = max(MIN_REQUEST_TIMEOUT, remaining_sec)
        if isinstance(self._timeout, tuple):
            connect_timeout, read_timeout = self._timeout
            computed_timeout: Union[Tuple[float, float], float] = (
                min(connect_timeout, bounded_sec),
                min(read_timeout, bounded_sec),
            )
        else:
            computed_timeout = min(self._timeout, bounded_sec)
        if computed_timeout != self._timeout:
            self._log_info(
                f"Adjusted HTTP timeout from {self._timeout} to {computed_timeout}s based on remaining execution time"
            )
        return computed_timeout

    @staticmethod
    def _exact_case_insensitive_regex(value: str) -> str:
        """
        Build an anchored, escaped case-insensitive AQL regex expression.
        :param value: {str} Exact identifier string to match
        :return: {str} Escaped AQL regex expression
        """
        escaped = re.escape(value).replace('"', '\\"')
        return f'regex("^{escaped}$", "i")'

    @staticmethod
    def _deduplicate_non_empty(values: Optional[List[str]]) -> List[str]:
        if not values:
            return []
        return list(dict.fromkeys(v for v in values if isinstance(v, str) and v))

    def _get_full_url(self, url_key: str, **kwargs) -> str:
        """
        Get full url from url key.
        :param url_id: {str} The key of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self._api_root, ENDPOINTS[url_key].format(**kwargs))

    def test_connectivity(self) -> None:
        """
        Test connectivity with Axonius instance
            raise AxoniusManagerError exception if failed to test connectivity
        """
        request_url = self._get_full_url("ping")
        self._session.headers.update({"Content-Type": "application/vnd.api+json"})
        response = self._session.get(request_url, timeout=self._get_request_timeout())
        self.validate_response(
            response, f"Failed to test connectivity to {INTEGRATION_IDENTIFIER}"
        )

    def _build_users_filter_query(
        self, emails: Optional[List[str]] = None, usernames: Optional[List[str]] = None
    ) -> str:
        """
        Build filter query for users search
        :param emails: [{str}] Email Addresses of users to query
        :param usernames: [{str}] Usernames of users to query
        :return: {str} Filter query for users endpoint
        """
        sub_queries: List[str] = []
        for email in self._deduplicate_non_empty(emails):
            regex_expr = self._exact_case_insensitive_regex(email)
            sub_queries.append(f'("specific_data.data.username" == {regex_expr})')
            sub_queries.append(f'("specific_data.data.mail" == {regex_expr})')
        for user in self._deduplicate_non_empty(usernames):
            regex_expr = self._exact_case_insensitive_regex(user)
            sub_queries.append(f'("specific_data.data.display_name" == {regex_expr})')
            sub_queries.append(f'("specific_data.data.username" == {regex_expr})')

        return f" {LOGICAL_OR} ".join(sub_queries)

    def _build_devices_filter_query(
        self,
        ip_addresses: Optional[List[str]],
        mac_addresses: Optional[List[str]],
        hostnames: Optional[List[str]] = None,
    ) -> str:
        """
        Build filter query for devices search
        :param ip_addresses: [{str}] IP addresses of devices to query
        :param mac_addresses: [{str}] Mac addresses of devices to query
        :param hostnames: [{str}] Hostnames of devices to query
        :return: {str} Filter query for devices endpoint
        """
        sub_queries: List[str] = []
        for ip in self._deduplicate_non_empty(ip_addresses):
            escaped_ip = ip.replace("\\", "\\\\").replace('"', '\\"')
            sub_queries.append(
                f'("specific_data.data.network_interfaces.ips" == "{escaped_ip}")'
            )
        for hostname in self._deduplicate_non_empty(hostnames):
            regex_expr = self._exact_case_insensitive_regex(hostname)
            sub_queries.append(f'("specific_data.data.name" == {regex_expr})')
            sub_queries.append(f'("specific_data.data.hostname" == {regex_expr})')
        for mac in self._deduplicate_non_empty(mac_addresses):
            regex_expr = self._exact_case_insensitive_regex(mac)
            sub_queries.append(
                f'("specific_data.data.network_interfaces.mac" == {regex_expr})'
            )
        return f" {LOGICAL_OR} ".join(sub_queries)

    def get_user_axonius_id(
        self, email: Optional[str] = None, username: Optional[str] = None
    ) -> str:
        """
        Get axonius user id
        :param email: {str} Email address of user
        :param username: {str} Username of users
        :return: {str} Axonius unique ID of the user
        """
        payload = {}
        if email:
            payload["emails"] = [email]
        if username:
            payload["usernames"] = [username]
        found_users = self.get_users(**payload)
        if found_users:
            return found_users[0].internal_axon_id

    def get_users_axonius_ids_by_username(self, usernames: Optional[List[str]] = None):
        """
        Get axonius user ids by usernames
        :param usernames: {[str]} List of usernames to find in axonius
        :return: {[str]} Axonius unique user ids
        """
        found_users = self.get_users(usernames=[usernames])
        return [user.internal_axon_id for user in found_users]

    def get_users_axonius_ids_by_email(self, emails: Optional[List[str]] = None):
        """
        Get axonius user ids by usernames
        :param emails: {[str]} List of users emails to find in axonius
        :return: {[str]} Axonius unique user ids
        """
        found_users = self.get_users(emails=[emails])
        return [user.internal_axon_id for user in found_users]

    def get_users(
        self,
        emails: Optional[List[str]] = None,
        usernames: Optional[List[str]] = None,
    ) -> List[UserGeneralAttribute]:
        """
        Get users general information
        :param emails: {[str]} Email addresses of users to retrieve
        :param usernames: {[str]} Usernames of users to retrieve
        :return: {[UserGeneralAttribue]} List of general information about found users
        """
        if not (emails or usernames):
            raise AxoniusManagerMandatoryParametersError(
                f"Failed to get general information for users. Emails or Usernames parameters must be provided"
            )
        email_list = self._deduplicate_non_empty(emails)
        username_list = self._deduplicate_non_empty(usernames)
        tagged_items = [("email", e) for e in email_list] + [
            ("username", u) for u in username_list
        ]
        if not tagged_items:
            self._log_info(
                "No non-empty email or username identifiers provided after deduplication"
            )
            return []

        request_url = self._get_full_url("get_users")
        results_by_id: dict[str, UserGeneralAttribute] = {}
        results_without_id: List[UserGeneralAttribute] = []
        total_batches = (
            len(tagged_items) + DEFAULT_QUERY_BATCH_SIZE - 1
        ) // DEFAULT_QUERY_BATCH_SIZE
        self._log_info(
            f"Searching {INTEGRATION_IDENTIFIER} users for {len(email_list)} unique email(s) and "
            f"{len(username_list)} unique username(s) in {total_batches} batch(es) "
            f"(batch_size={DEFAULT_QUERY_BATCH_SIZE}, use_cache_entry=True)"
        )

        for idx in range(0, len(tagged_items), DEFAULT_QUERY_BATCH_SIZE):
            batch_num = (idx // DEFAULT_QUERY_BATCH_SIZE) + 1
            batch = tagged_items[idx : idx + DEFAULT_QUERY_BATCH_SIZE]
            batch_emails = [val for kind, val in batch if kind == "email"]
            batch_usernames = [val for kind, val in batch if kind == "username"]
            page_limit = min(
                MAX_PAGE_LIMIT, max(MIN_PAGE_LIMIT, len(batch) * PAGE_LIMIT_MULTIPLIER)
            )
            payload = {
                "data": {
                    "type": "entity_request_schema",
                    "attributes": {
                        "get_metadata": False,
                        "include_details": False,
                        "fields": {
                            "users": [
                                "specific_data.data.mail",
                                "specific_data.data.display_name",
                                "specific_data.data.username",
                            ]
                        },
                        "excluded_adapters": {},
                        "use_cursor": False,
                        "filter": self._build_users_filter_query(
                            batch_emails, batch_usernames
                        ),
                        "use_cache_entry": True,
                        "page": {"limit": page_limit, "offset": 0},
                        "field_filters": {},
                        "include_notes": False,
                        "always_cached_query": False,
                    },
                }
            }
            request_timeout = self._get_request_timeout()
            self._log_info(
                f"Requesting users batch {batch_num}/{total_batches} "
                f"(emails={len(batch_emails)}, usernames={len(batch_usernames)}, "
                f"page_limit={page_limit}, timeout={request_timeout})"
            )
            response = self._session.post(
                request_url, json=payload, timeout=request_timeout
            )
            err_msg = (
                "Failed to get users with provided email addresses or usernames of: "
            )
            if batch_emails:
                err_msg += " ".join(batch_emails)
            if batch_usernames:
                err_msg += " ".join(batch_usernames)

            self.validate_response(response, err_msg)
            batch_users = self.parser.build_user_general_attribute_obj_list(
                response.json()
            )
            self._log_info(
                f"Users batch {batch_num}/{total_batches} returned {len(batch_users)} user record(s)"
            )
            for user in batch_users:
                if user.internal_axon_id:
                    results_by_id.setdefault(user.internal_axon_id, user)
                else:
                    results_without_id.append(user)

        final_users = list(results_by_id.values()) + results_without_id
        if total_batches > 1:
            self._log_info(
                f"Deduplicated user search results across {total_batches} batches to {len(final_users)} unique user(s)"
            )
        return final_users

    def get_user_details(self, internal_axonius_id: str) -> UserDetailedInformation:
        """
        Get details of a user in axonius platform
        :param internal_axonius_id: {str} User's internal Axonius ID. Can be retrieved using AxoniusManager.get_users() method.
        :return:
        """
        request_url = self._get_full_url(
            "get-user-details", internal_axonius_id=internal_axonius_id
        )
        response = self._session.get(request_url, timeout=self._get_request_timeout())
        self.validate_response(
            response,
            f"Failed to get details of user with internal axonius id of {internal_axonius_id}",
        )
        return self.parser.build_user_detailed_information_obj(
            response.json(), api_root=self._api_root
        )

    def get_device_axonius_id(
        self, ip_address: str = None, mac_address: str = None, hostname: str = None
    ) -> str:
        """
        Get axonius device id
        :param ip_address: {str} IP address of the device
        :param mac_address: {str} MAC address of the device
        :param hostname: {str} Hostname of the device
        :return: {str} Axonius internal id
        """
        payload = {}
        if ip_address:
            payload["ip_addresses"] = [ip_address]
        if mac_address:
            payload["mac_addresses"] = [mac_address]
        if hostname:
            payload["hostnames"] = [hostname]
        found_devices = self.get_devices(**payload)
        if found_devices:
            return found_devices[0].internal_axon_id

    def get_devices(
        self,
        ip_addresses: Optional[List[str]] = None,
        mac_addresses: Optional[List[str]] = None,
        hostnames: Optional[List[str]] = None,
    ) -> List[DeviceGeneralAttribute]:
        """
        Get devices general information
        :param ip_addresses: {[str]} IP addresses of devices to retrieve
        :param mac_addresses: {[str]} Mac addresses of devices to retrieve
        :param hostnames: {[str]} Hostnames of devices to retrieve
        :return: {[DeviceGeneralAttribute]} List of general information about found devices
        """
        if not (ip_addresses or mac_addresses or hostnames):
            raise AxoniusManagerMandatoryParametersError(
                f"Failed to get general information for devices. IP Addresses, Hostnames or MAC addresses parameters must be provided"
            )
        ip_list = self._deduplicate_non_empty(ip_addresses)
        mac_list = self._deduplicate_non_empty(mac_addresses)
        hostname_list = self._deduplicate_non_empty(hostnames)
        tagged_items = (
            [("ip", ip) for ip in ip_list]
            + [("mac", mac) for mac in mac_list]
            + [("hostname", h) for h in hostname_list]
        )
        if not tagged_items:
            self._log_info(
                "No non-empty device identifiers provided after deduplication"
            )
            return []

        request_url = self._get_full_url("get-devices")
        results_by_id: dict[str, DeviceGeneralAttribute] = {}
        results_without_id: List[DeviceGeneralAttribute] = []
        total_batches = (
            len(tagged_items) + DEFAULT_QUERY_BATCH_SIZE - 1
        ) // DEFAULT_QUERY_BATCH_SIZE
        self._log_info(
            f"Searching {INTEGRATION_IDENTIFIER} devices for {len(ip_list)} unique IP(s), "
            f"{len(mac_list)} unique MAC(s), and {len(hostname_list)} unique hostname(s) "
            f"in {total_batches} batch(es) (batch_size={DEFAULT_QUERY_BATCH_SIZE}, use_cache_entry=True)"
        )

        for idx in range(0, len(tagged_items), DEFAULT_QUERY_BATCH_SIZE):
            batch_num = (idx // DEFAULT_QUERY_BATCH_SIZE) + 1
            batch = tagged_items[idx : idx + DEFAULT_QUERY_BATCH_SIZE]
            batch_ips = [val for kind, val in batch if kind == "ip"]
            batch_macs = [val for kind, val in batch if kind == "mac"]
            batch_hostnames = [val for kind, val in batch if kind == "hostname"]
            page_limit = min(
                MAX_PAGE_LIMIT, max(MIN_PAGE_LIMIT, len(batch) * PAGE_LIMIT_MULTIPLIER)
            )
            payload = {
                "data": {
                    "type": "entity_request_schema",
                    "attributes": {
                        "get_metadata": False,
                        "include_details": False,
                        "fields": {
                            "devices": [
                                "adapters",
                                "specific_data.data.name",
                                "specific_data.data.hostname",
                                "specific_data.data.last_seen",
                                "specific_data.data.network_interfaces.ips",
                                "specific_data.data.network_interfaces.mac",
                                "specific_data.data.os.type",
                                "labels",
                            ]
                        },
                        "excluded_adapters": {},
                        "use_cursor": False,
                        "filter": self._build_devices_filter_query(
                            batch_ips, batch_macs, batch_hostnames
                        ),
                        "use_cache_entry": True,
                        "page": {"limit": page_limit, "offset": 0},
                        "field_filters": {},
                        "include_notes": False,
                        "always_cached_query": False,
                    },
                }
            }
            request_timeout = self._get_request_timeout()
            self._log_info(
                f"Requesting devices batch {batch_num}/{total_batches} "
                f"(ips={len(batch_ips)}, macs={len(batch_macs)}, hostnames={len(batch_hostnames)}, "
                f"page_limit={page_limit}, timeout={request_timeout})"
            )
            response = self._session.post(
                request_url, json=payload, timeout=request_timeout
            )
            err_msg = "Failed to get devices with provided ip addresses, hostnames or mac addresses of: "
            if batch_ips:
                err_msg += " ".join(batch_ips)
            if batch_hostnames:
                err_msg += " ".join(batch_hostnames)
            if batch_macs:
                err_msg += " ".join(batch_macs)

            self.validate_response(response, err_msg)
            batch_devices = self.parser.build_device_general_attribute_obj_list(
                response.json()
            )
            self._log_info(
                f"Devices batch {batch_num}/{total_batches} returned {len(batch_devices)} device record(s)"
            )
            for device in batch_devices:
                if device.internal_axon_id:
                    results_by_id.setdefault(device.internal_axon_id, device)
                else:
                    results_without_id.append(device)

        final_devices = list(results_by_id.values()) + results_without_id
        if total_batches > 1:
            self._log_info(
                f"Deduplicated device search results across {total_batches} batches to {len(final_devices)} unique device(s)"
            )
        return final_devices

    def get_device_details(self, internal_axonius_id: str) -> DeviceDetailedInformation:
        """
        Get details of a device in axonius platform
        :param internal_axonius_id: {str} Device's internal Axonius ID. Can be retrieved using AxoniusManager.get_devices() method.
        :return:
        """
        request_url = self._get_full_url(
            "get-device-details", internal_axonius_id=internal_axonius_id
        )
        response = self._session.get(request_url, timeout=self._get_request_timeout())
        self.validate_response(
            response,
            f"Failed to get details of device with internal axonius id of {internal_axonius_id}",
        )
        return self.parser.build_device_detailed_information_obj(
            response.json(), api_root=self._api_root
        )

    def add_tags_to_users(self, internal_axonius_ids: List[str], tags: List[str]):
        """
        Add tags to users
        :param internal_axonius_ids: {[str]} List of internal axonius ids of users
        :param tags: {[str]} List of tags to attach
        """
        request_url = self._get_full_url("add-tags-to-users")
        payload = {
            "data": {
                "type": "add_tags_schema",
                "attributes": {
                    "entities": {"ids": internal_axonius_ids, "include": True},
                    "labels": tags,
                    "filter": "",
                },
            }
        }
        response = self._session.put(
            request_url, json=payload, timeout=self._get_request_timeout()
        )
        self.validate_response(
            response,
            f"Failed to add tags to provided axonius ids {', '.join(internal_axonius_ids)}",
        )

    def remove_tags_from_users(self, internal_axonius_ids: List[str], tags: List[str]):
        """
        Remove tags fro, users
        :param internal_axonius_ids: {[str]} List of internal axonius ids of users
        :param tags: {[str]} List of tags to remove
        """
        request_url = self._get_full_url("remove-tags-from-users")
        payload = {
            "data": {
                "type": "add_tags_schema",
                "attributes": {
                    "entities": {"ids": internal_axonius_ids, "include": True},
                    "labels": tags,
                    "filter": "",
                },
            }
        }
        response = self._session.delete(
            request_url, json=payload, timeout=self._get_request_timeout()
        )
        self.validate_response(
            response,
            f"Failed to remove tags from the provided axonius ids {', '.join(internal_axonius_ids)}",
        )

    def add_tags_to_devices(self, internal_axonius_ids: List[str], tags: List[str]):
        """
        Add tags to devices
        :param internal_axonius_ids: {[str]} List of internal axonius ids of devices
        :param tags: {[str]} List of tags to attach
        """
        request_url = self._get_full_url("add-tags-to-devices")
        payload = {
            "data": {
                "type": "add_tags_schema",
                "attributes": {
                    "entities": {"ids": internal_axonius_ids, "include": True},
                    "labels": tags,
                    "filter": "",
                },
            }
        }
        response = self._session.put(
            request_url, json=payload, timeout=self._get_request_timeout()
        )
        self.validate_response(
            response,
            f"Failed to add tags to provided axonius ids {', '.join(internal_axonius_ids)}",
        )

    def remove_tags_from_devices(
        self, internal_axonius_ids: List[str], tags: List[str]
    ):
        """
        Remove tags from devices
        :param internal_axonius_ids: {[str]} List of internal axonius ids of devices
        :param tags: {[str]} List of tags to remove
        """
        request_url = self._get_full_url("remove-tags-from-devices")
        payload = {
            "data": {
                "type": "add_tags_schema",
                "attributes": {
                    "entities": {"ids": internal_axonius_ids, "include": True},
                    "labels": tags,
                    "filter": "",
                },
            }
        }
        response = self._session.delete(
            request_url, json=payload, timeout=self._get_request_timeout()
        )
        self.validate_response(
            response,
            f"Failed to remove tags from provided the axonius ids {', '.join(internal_axonius_ids)}",
        )

    def add_note_to_user(self, internal_axonius_id: str, note: str) -> UserNote:
        """
        Add a note to a user in Axonius
        :param internal_axonius_id: {str} Internal axonius id of the user
        :param note: {str} The note to add to the user
        :return: {UserNote} Created user note data model
        """
        request_url = self._get_full_url(
            "add-note-to-user", internal_axonius_id=internal_axonius_id
        )
        payload = {"data": {"type": "notes_schema", "attributes": {"note": note}}}
        response = self._session.post(
            request_url, json=payload, timeout=self._get_request_timeout()
        )
        self.validate_response(
            response,
            f"Failed to add note to user with axonius id {internal_axonius_id}",
        )
        return self.parser.build_user_note_obj(response.json())

    def add_note_to_device(self, internal_axonius_id: str, note: str) -> DeviceNote:
        """
        Add a note to a device in Axonius
        :param internal_axonius_id: {str} Internal axonius id of the device
        :param note: {str} The note to add to the device
        :return: {DeviceNote} Created device note data model
        """
        request_url = self._get_full_url(
            "add-note-to-device", internal_axonius_id=internal_axonius_id
        )
        payload = {"data": {"type": "notes_schema", "attributes": {"note": note}}}
        response = self._session.post(
            request_url, json=payload, timeout=self._get_request_timeout()
        )
        self.validate_response(
            response,
            f"Failed to add note to device with axonius id {internal_axonius_id}",
        )
        return self.parser.build_device_note_obj(response.json())

    @staticmethod
    def validate_response(
        response: requests.Response, error_msg="An error occurred"
    ) -> None:
        """
        Validate a response
        :param response: {requests.Response} The response
        :param error_msg: {str} The error message to display on failure
        """
        try:
            if response.status_code == FORBIDDEN_ERROR_STATUS_CODE:
                raise AxoniusForbiddenError(
                    f"{error_msg}: {FORBIDDEN_ERROR_STATUS_CODE} Forbidden"
                )
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response.json()
                error_messages = (
                    AxoniusTransformationLayer.parse_api_http_error_response(
                        response.json()
                    )
                )
                if response.status_code == AUTHORIZATION_ERROR_STATUS_CODE:
                    raise AxoniusAuthorizationError(
                        f"{error_msg}: {error} - {error_messages}"
                    )
                raise AxoniusManagerError(f"{error_msg}: {error} - {error_messages}")
            except (AxoniusAuthorizationError, AxoniusManagerError):
                raise

            except:
                raise AxoniusManagerError(f"{error_msg}: {error} - {response.text}")
