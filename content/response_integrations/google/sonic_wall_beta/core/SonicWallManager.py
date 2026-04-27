from __future__ import annotations
import requests
import urllib.parse
from .SonicWallParser import SonicWallParser

from .SonicWallExceptions import UnauthorizedException, UnableToAddException

from .UtilsManager import validate_response, permissive_json_loads

from .constants import (
    ENDPOINTS,
    HEADERS,
    NO_MATCH_ERROR_CODE,
    UNAUTHORIZED_ERROR_CODE,
    GENERAL_ERROR_CODE,
    ALLOWED_URI_FIRST_STRING,
)


class SonicWallManager:

    def __init__(
        self, api_root, username, password, verify_ssl=False, siemplify_logger=None
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: SonicWall API Root
        :param username: Username of the SonicWall account
        :param password: Password of the SonicWall account
        :param verify_ssl: Enable (True) or disable (False). If enabled, verify the SSL certificate for the connection
        to the SonicWall server is valid.
        :param siemplify_logger: Siemplify logger.
        """
        self.api_root = api_root
        self.siemplify_logger = siemplify_logger
        self.parser = SonicWallParser()
        self.session = requests.session()
        self.session.headers = HEADERS
        self.username = username.encode("utf-8")
        self.password = password.encode("utf-8")
        self.session.auth = (self.username, self.password)
        self.session.verify = verify_ssl
        self.auth_session()

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {unicode} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {unicode} The full url
        """
        return urllib.parse.urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def auth_session(self):
        """
        Make auth request to start the session
        """
        request_url = self._get_full_url("auth")
        response = self.session.post(request_url)
        try:
            validate_response(response, "Unable to login to SonicWall.")
        except Exception as e:
            response_object = self.parser.build_response_object(
                permissive_json_loads(response.text)
            )
            if response_object.message:
                raise UnauthorizedException(
                    f"Failed to connect to the SonicWall server! Reason: {response_object.message}"
                )
            else:
                raise Exception(e)

    def test_connectivity(self):
        """
        Test connectivity to the SonicWall.
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("ping")
        response = self.session.get(request_url)
        validate_response(response, "Unable to connect to SonicWall.")

    def check_group(self, group_name, ip_type):
        """
        Check if the Group with the specified Group name exists.
        :param group_name: Group name to be checked
        :param ip_type: IPv4 or IPv6
        :return: Address Group
        """
        request_url = self._get_full_url(
            "address_groups", ip_type=ip_type, group_name=group_name
        )
        response = self.session.get(request_url)
        try:
            validate_response(response, "No matching group found.")
            result = response.json().get("address_group", {})
            return self.parser.build_address_group(result.get(ip_type), ip_type)
        except Exception as e:
            response_object = self.parser.build_response_object(
                permissive_json_loads(response.text)
            )
            if response_object.code == UNAUTHORIZED_ERROR_CODE:
                raise UnauthorizedException(
                    f"Failed to connect to the SonicWall server! Reason: {response_object.message}"
                )
            if response_object.code != NO_MATCH_ERROR_CODE:
                raise Exception(e)
            return None

    def create_address_object(self, ip_type, zone, ip_identifier):
        """
        Create address object in SonicWall
        :param ip_type: IPv4 or IPv6
        :param zone: The zone of the IP address to add.
        :param ip_identifier: IP address
        :return: {unicode} return object name
        """
        request_url = self._get_full_url("create_address", ip_type=ip_type)
        object_name = f"Siemplify {ip_identifier} {zone}"
        payload = {
            "address_object": {
                ip_type: {
                    "name": object_name,
                    "zone": zone,
                    "host": {"ip": ip_identifier},
                }
            }
        }
        response = self.session.post(request_url, json=payload)
        try:
            validate_response(response, "Unable to create address object")
            return object_name
        except Exception:
            return object_name

    def add_ip_to_address_group(self, ip_type, group_name, object_name):
        """
        Add IP to existing address group
        :param ip_type: IPv4 or IPv6
        :param group_name: Group name to add IP to
        :param object_name: Name of the object to add
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url(
            "address_groups", ip_type=ip_type, group_name=group_name
        )
        payload = {
            "address_group": {
                ip_type: {"address_object": {ip_type: [{"name": object_name}]}}
            }
        }

        response = self.session.put(request_url, json=payload)

        try:
            validate_response(response, "Unable to add IP to Address Group")
        except Exception:
            response_object = self.parser.build_response_object(
                permissive_json_loads(response.text)
            )
            raise UnableToAddException(response_object)

    def confirm_changes(self):
        """
        Confirm changes made in previous steps
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("confirm")
        response = self.session.post(request_url)
        response_object = self.parser.build_response_object(
            permissive_json_loads(response.text)
        )
        try:
            validate_response(response, "Unable to confirm changes")
            if response_object.code == GENERAL_ERROR_CODE:
                raise UnableToAddException(response_object)
        except Exception:
            raise UnableToAddException(response_object)

    def get_all_address_objects(self, ip_type):
        """
        Get all address objects by type
        :param ip_type: IPv4 or IPv6
        :return: {list} List of IP objects
        """
        request_url = self._get_full_url("all_addresses", ip_type=ip_type)
        response = self.session.get(request_url)
        validate_response(response, "Unable to get address objects")
        results = response.json().get("address_objects", [])

        return [
            self.parser.build_ip_object(ip_json.get(ip_type)) for ip_json in results
        ]

    def delete_ip_from_address_group(self, ip_type, group_name, object_name):
        """
        Add IP to existing address group
        :param ip_type: IPv4 or IPv6
        :param group_name: Group name to add IP to
        :param object_name: Name of the object to add
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url(
            "address_groups", ip_type=ip_type, group_name=group_name
        )
        payload = {
            "address_group": {
                ip_type: {"address_object": {ip_type: [{"name": object_name}]}}
            }
        }
        response = self.session.delete(request_url, json=payload)
        try:
            validate_response(response, "Unable to delete IP from Address Group")
        except Exception:
            response_object = self.parser.build_response_object(
                permissive_json_loads(response.text)
            )
            raise UnableToAddException(response_object)

    def add_url_to_uri_list(self, uri_list, identifier):
        """
        Add URL to specific SonicWall URI List
        :param uri_list: URI list to add the URL
        :param identifier: URL identifier
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("add_url", uri_list=uri_list)
        payload = {
            "content_filter": {
                "uri_list_object": {"name": uri_list, "uri": [{"uri": identifier}]}
            }
        }
        response = self.session.put(request_url, json=payload)
        try:
            validate_response(response, "Unable to add URL to URI list")
        except Exception:
            response_object = self.parser.build_response_object(
                permissive_json_loads(response.text)
            )
            raise UnableToAddException(response_object)

    def remove_url_from_uri_list(self, uri_list, identifier):
        """
        Remove URL from specific SonicWall URI List
        :param uri_list: URI list to add the URL
        :param identifier: URL identifier
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("delete_url")
        payload = {
            "content_filter": {
                "uri_list_object": {"name": uri_list, "uri": [{"uri": identifier}]}
            }
        }
        response = self.session.delete(request_url, json=payload)
        try:
            validate_response(response, "Unable to remove URL from URI list")
        except Exception:
            response_object = self.parser.build_response_object(
                permissive_json_loads(response.text)
            )
            raise UnableToAddException(response_object)

    def get_address_groups(self, ip_type):
        """
        Get address groups by type
        :param ip_type: IPv4 or IPv6
        :return: {list} List of Address groups
        """
        request_url = self._get_full_url("get_address_groups", ip_type=ip_type)
        response = self.session.get(request_url)
        validate_response(response, "Unable to get address groups")
        results = response.json().get("address_groups", [])

        return [
            self.parser.build_address_group(result_json.get(ip_type), ip_type)
            for result_json in results
        ]

    def get_uri_lists(self):
        """
        Get URI Lists
        :return: {list} List of URI List objects
        """
        request_url = self._get_full_url("get_uri_lists")
        response = self.session.get(request_url)
        validate_response(response, "Unable to get URI Lists")
        results = response.json().get("content_filter", {}).get("uri_list_object", [])

        return [
            self.parser.build_uri_list_object(result_json) for result_json in results
        ]

    def add_uri_list_to_uri_group(self, uri_list, uri_group):
        """
        Add URI List to specific SonicWall URI Group
        :param uri_list: URI list to add the URL
        :param uri_group: URI Group name to add the list to
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("add_uri_to_group")
        payload = {
            "content_filter": {
                "uri_list_group": {
                    "name": uri_group,
                    "uri_list_object": [{"name": uri_list}],
                }
            }
        }
        response = self.session.put(request_url, json=payload)
        try:
            validate_response(response, "Unable to add URL to URI list")
        except Exception:
            response_object = self.parser.build_response_object(
                permissive_json_loads(response.text)
            )
            raise UnableToAddException(response_object)

    def get_groups(self):
        """
        Get groups from SonicWall
        :return: {List} List of SonicWall groups
        """
        request_url = self._get_full_url("list_groups")
        response = self.session.get(request_url)
        validate_response(response, "Unable to get URI groups")
        results = response.json().get("content_filter", {}).get("uri_list_group", [])

        return [
            self.parser.build_uri_group_object(result_json) for result_json in results
        ]

    def create_cfs_profile(
        self,
        profile_name,
        allowed,
        forbidden,
        search_order,
        forbidden_operation,
        smart_filter,
        safe_search,
        youtube_mode,
        bing_search,
    ):
        """
        Create SonicWall CFS Profile
        :param profile_name: Name of the CFS Profile
        :param allowed: Allowed URI list or group for the CFS Profile
        :param forbidden: Forbidden URI list or group for the CFS Profile
        :param search_order: Search order for the CFS Profile
        :param forbidden_operation: Operation for forbidden URI for the CFS Profile
        :param smart_filter: Enable Smart Filter
        :param safe_search: Enable Google Safe Search
        :param youtube_mode: Enable Youtube Restricted Mode
        :param bing_search: Enable Bing Safe Search
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("create_cfs_profile")
        allowed_list = []
        forbidden_list = []
        if allowed:
            allowed_list.append({"name": allowed})
        if forbidden:
            forbidden_list.append({"name": forbidden})
        search_order_string = (
            "allowed-first"
            if search_order == ALLOWED_URI_FIRST_STRING
            else "forbidden-first"
        )
        payload = {
            "content_filter": {
                "profile": {
                    "name": profile_name,
                    "uri_list": {
                        "allowed": allowed_list,
                        "forbidden": forbidden_list,
                        "search_order": search_order_string,
                        "forbidden_operation": forbidden_operation.lower(),
                    },
                    "smart_filter": smart_filter,
                    "google_force_safe_search": safe_search,
                    "youtube_restrict_mode": youtube_mode,
                    "bing_force_safe_search": bing_search,
                }
            }
        }
        response = self.session.post(request_url, json=payload)
        try:
            validate_response(response, "Unable to create CFS Profile")
        except Exception:
            response_object = self.parser.build_response_object(
                permissive_json_loads(response.text)
            )
            raise UnableToAddException(response_object)
