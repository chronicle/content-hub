from __future__ import annotations
from copy import deepcopy
from typing import Optional, List
from urllib.parse import urljoin

import requests
from requests import Session

from soar_sdk.SiemplifyLogger import SiemplifyLogger
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

        self.parser: AxoniusTransformationLayer = AxoniusTransformationLayer()
        self.siemplify_logger: SiemplifyLogger = siemplify_logger

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
        response = self._session.get(request_url)
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
        if emails:
            for email in emails:
                user_query = (
                    '("specific_data.data.username"' f' == regex("{email}", "i"))'
                )
                mail_query = '("specific_data.data.mail"' f' == regex("{email}", "i"))'
                sub_queries.append(user_query)
                sub_queries.append(mail_query)
        if usernames:
            for user in usernames:
                display_name_query = (
                    '("specific_data.data.display_name"' f' == regex("{user}", "i"))'
                )
                username_query = (
                    '("specific_data.data.username"' f' == regex("{user}", "i"))'
                )
                sub_queries.append(display_name_query)
                sub_queries.append(username_query)

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
        if ip_addresses:
            for ip in ip_addresses:
                ip_query = '("specific_data.data.network_interfaces.ips"' f' == "{ip}")'
                sub_queries.append(ip_query)
        if hostnames:
            for hostname in hostnames:
                name_query = (
                    '("specific_data.data.name"' f' == regex("{hostname}", "i"))'
                )
                hostname_query = (
                    '("specific_data.data.hostname"' f' == regex("{hostname}", "i"))'
                )
                sub_queries.append(name_query)
                sub_queries.append(hostname_query)
        if mac_addresses:
            for mac in mac_addresses:
                mac_query = (
                    '("specific_data.data.network_interfaces.mac"'
                    f' == regex("{mac}", "i"))'
                )
                sub_queries.append(mac_query)
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
        self, emails: Optional[str] = None, usernames: Optional[str] = None
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
        request_url = self._get_full_url("get_users")
        payload = {
            "data": {
                "type": "entity_request_schema",
                "attributes": {
                    "get_metadata": True,
                    "include_details": False,
                    "fields": {
                        "devices": [
                            "specific_data.data.mail",
                            "specific_data.data.display_name",
                            "specific_data.data.username",
                        ]
                    },
                    "excluded_adapters": {},
                    "use_cursor": True,
                    "filter": self._build_users_filter_query(emails, usernames),
                    "use_cache_entry": False,
                    "page": {"limit": 2000, "offset": 0},
                    "field_filters": {},
                    "include_notes": False,
                    "always_cached_query": False,
                },
            }
        }
        response = self._session.post(request_url, json=payload)
        err_msg = "Failed to get users with provided email addresses or usernames of: "
        if emails:
            err_msg += " ".join(emails)
        if usernames:
            err_msg += " ".join(usernames)

        self.validate_response(response, err_msg)
        return self.parser.build_user_general_attribute_obj_list(response.json())

    def get_user_details(self, internal_axonius_id: str) -> UserDetailedInformation:
        """
        Get details of a user in axonius platform
        :param internal_axonius_id: {str} User's internal Axonius ID. Can be retrieved using AxoniusManager.get_users() method.
        :return:
        """
        request_url = self._get_full_url(
            "get-user-details", internal_axonius_id=internal_axonius_id
        )
        response = self._session.get(request_url)
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
        request_url = self._get_full_url("get-devices")
        payload = {
            "data": {
                "type": "entity_request_schema",
                "attributes": {
                    "get_metadata": True,
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
                    "use_cursor": True,
                    "filter": self._build_devices_filter_query(
                        ip_addresses, mac_addresses, hostnames
                    ),
                    "use_cache_entry": False,
                    "page": {"limit": 2000, "offset": 0},
                    "field_filters": {},
                    "include_notes": False,
                    "always_cached_query": False,
                },
            }
        }
        response = self._session.post(request_url, json=payload)
        err_msg = "Failed to get devices with provided ip addresses, hostnames or mac addresses of: "
        if ip_addresses:
            err_msg += " ".join(ip_addresses)
        if hostnames:
            err_msg += " ".join(hostnames)
        if mac_addresses:
            err_msg += " ".join(mac_addresses)

        self.validate_response(response, err_msg)
        return self.parser.build_device_general_attribute_obj_list(response.json())

    def get_device_details(self, internal_axonius_id: str) -> DeviceDetailedInformation:
        """
        Get details of a device in axonius platform
        :param internal_axonius_id: {str} Device's internal Axonius ID. Can be retrieved using AxoniusManager.get_devices() method.
        :return:
        """
        request_url = self._get_full_url(
            "get-device-details", internal_axonius_id=internal_axonius_id
        )
        response = self._session.get(request_url)
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
        response = self._session.put(request_url, json=payload)
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
        response = self._session.delete(request_url, json=payload)
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
        response = self._session.put(request_url, json=payload)
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
        response = self._session.delete(request_url, json=payload)
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
        response = self._session.post(request_url, json=payload)
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
        response = self._session.post(request_url, json=payload)
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
