from __future__ import annotations
from .McAfeeMvisionEPOParser import McAfeeMvisionEPOParser
from .UtilsManager import validate_response
import requests
from urllib.parse import urljoin
from .constants import (
    IAM_URL,
    INTEGRATION_DISPLAY_NAME,
    AUTH_PAYLOAD,
    PER_PAGE_LIMIT,
    HEADERS,
)
from .exceptions import (
    UnableToGetTokenException,
    GroupNotFoundException,
    TagNotFoundException,
    EndpointNotFoundException,
)

ENDPOINTS = {
    "login": "/iam/v1.2/token",
    "ping": "/epo/v1/groups",
    "tags": "/epo/v1/tags",
    "devices": "/epo/v1/devices",
    "add_tag": "/epo/v1/devices/add_tag",
    "remove_tag": "/epo/v1/devices/remove_tag",
    "list_groups": "/epo/v1/groups",
}


class McAfeeMvisionEPOManager:

    def __init__(
        self,
        api_root,
        client_id,
        client_secret,
        scopes,
        group_name=None,
        verify_ssl=False,
        siemplify_logger=None,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: McAfee Mvision ePO API Root
        :param client_id: Client ID of the McAfee Mvision ePO account
        :param client_secret: Client Secret of the McAfee Mvision ePO account
        :param scopes: Scopes of the McAfee Mvision ePO account
        :param group_name: Group name that will be used to search for endpoints. If nothing is specified. All of the groups will be used
        :param verify_ssl: Enable (True) or disable (False). If enabled, verify the SSL certificate for the connection to the McAfee Mvision ePO public cloud server is valid.
        :param siemplify_logger: Siemplify logger.
        """
        self.api_root = api_root
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes
        self.group_name = group_name
        self.siemplify_logger = siemplify_logger
        self.parser = McAfeeMvisionEPOParser()
        self.session = requests.session()
        self.session.headers = HEADERS
        self.session.verify = verify_ssl
        self.set_auth_token()
        self.already_loaded_devices = []
        self.all_devices_loaded = False
        # because we are using one host for getting token, and another one for fetching data, we need to call
        # test_connectivity to be sure that the manager is able to fetch data
        self.test_connectivity()

    def set_auth_token(self):
        """
        Set Authorization header to request session.
        """
        self.session.headers.update({"Authorization": self.get_auth_token()})

    def get_auth_token(self):
        """
        Send request in order to get generated tokens.
        :return: {unicode} The Authorization Token to use for the next requests
        """
        try:
            login_response = self.session.get(
                IAM_URL, auth=(self.client_id, self.client_secret), params=AUTH_PAYLOAD
            )
            validate_response(login_response)
            return self.parser.get_auth_token(login_response.json())
        except Exception as err:
            raise UnableToGetTokenException(f"{INTEGRATION_DISPLAY_NAME}: {err}")

    def _get_full_url(self, url_id):
        """
        Send full url from url identifier.
        :param url_id: {unicode} The id of url
        :return: {unicode} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id])

    def _add_filters_to_payload(self, filters, payload=None):
        """
        Build filter.
        :param filters: {dict} The filters to include in request
        :param payload: {dict} The request's payload
        :return: {str} filter
        """
        payload = payload if payload else {}

        payload["$filter"] = "{{{}}}".format(
            ",".join([f'"{key}":"{value}"' for key, value in filters.items()])
        )

        return payload

    def test_connectivity(self):
        """
        Test connectivity to the McAfee Mvision ePO.
        :return: {bool} True if successful, exception otherwise
        """
        payload = {"$limit": 1, "$offset": 0}

        if self.group_name:
            payload["$filter"] = f'{{"name":"{self.group_name}"}}'

        response = self.session.get(self._get_full_url("ping"), params=payload)
        try:
            validate_response(response, "Unable to connect to McAfee Mvision ePO.")
        except:
            if response.status_code == 404 and self.group_name:
                raise GroupNotFoundException(f"Group {self.group_name} not found")
            else:
                raise

    def find_tag_or_fail(self, tag_name):
        """
        Find Tag by name or rise not found exception.
        :param tag_name: {str} The name of the tag
        :return: {Tag} The tag
        """
        payload = self._add_filters_to_payload({"name": tag_name})

        response = self.session.get(self._get_full_url("tags"), params=payload)

        if response.status_code == 404:
            raise TagNotFoundException(f"Tag {tag_name} not found")
        validate_response(response)
        items_json = self.parser.get_items_json(response.json())

        if not items_json:
            raise TagNotFoundException(f"Tag {tag_name} not found")

        return self.parser.build_siemplify_tag(items_json[0])

    def find_entity_or_fail(self, identifier, is_host):
        """
        Find entity or fail.
        :param identifier: {str} The identifier to search
        :param is_host: {bool} True in case of searching host
        :return: {Device} The tag
        """
        matched_device = self.search_identifier_in_devices(
            identifier, self.already_loaded_devices, is_host
        )

        if not matched_device and not self.all_devices_loaded:

            matched_device = list(
                filter(
                    lambda device: self.device_filter(device, identifier, is_host),
                    self.load_more_devices(),
                )
            )

            while not matched_device and not self.all_devices_loaded:
                matched_device = self.search_identifier_in_devices(
                    identifier, self.load_more_devices(), is_host
                )

        if not matched_device:
            raise EndpointNotFoundException

        return matched_device[0]

    def load_more_devices(self):
        """
        Load more devices. This action works like pagination.
        :return: {list} The list of the loaded devices
        """
        response = self.session.get(
            self._get_full_url("devices"),
            params={
                "$offset": len(self.already_loaded_devices),
                "$limit": PER_PAGE_LIMIT,
            },
        )
        validate_response(response)
        response_json = response.json()
        total_items = self.parser.get_total_items(response_json)
        devices = [
            self.parser.build_siemplify_device(device_json)
            for device_json in self.parser.get_items_json(response_json)
        ]
        self.already_loaded_devices.extend(devices)
        if total_items <= len(self.already_loaded_devices):
            self.all_devices_loaded = True
        return devices

    def search_identifier_in_devices(self, identifier, devices, is_host):
        """
        Search identifier in already loaded devices.
        :param identifier: {str} The identifier to search
        :param devices: {list} The list of devices to search
        :param is_host: {bool} True in case of searching host
        :return: {list} The list of devices found for identifier
        """
        return list(
            filter(
                lambda device: self.device_filter(device, identifier, is_host), devices
            )
        )

    def device_filter(self, device, identifier, is_host):
        """
        Determine if specific device match the condition.
        :param device: {Device} The device to filter
        :param identifier: {str} The identifier to search
        :param is_host: {bool} True in case of searching host
        :return: {bool} True if device match the condition
        """
        if self.group_name and (device.group_name != self.group_name):
            return False

        if is_host:
            return device.host == identifier

        return device.ip == identifier

    def add_or_remove_tag(self, device, tag, add=True):
        """
        Add or remove tag.
        :param device: {Device} The device to add the tag
        :param tag: {Tag} The tag to attache the device
        :param add: {bool} If true it will add the tag to device, else will remove
        :return: {bool} True if the tag attached to device
        """
        payload = {"tagId": tag.tag_id, "deviceIds": [device.uuid]}
        endpoint_id = "add_tag" if add else "remove_tag"
        response = self.session.post(self._get_full_url(endpoint_id), json=payload)
        validate_response(response)
        return True

    def list_groups(self, max_groups_to_return=100):
        """
        List Groups in EPO
        :param max_groups_to_return: {int} Limit of groups that should be returned
        :return {List} List Of groups
        """
        payload = {"$limit": max_groups_to_return, "$offset": 0}

        response = self.session.get(self._get_full_url("list_groups"), params=payload)
        validate_response(response)

        items = self.parser.get_items_json(response.json())

        return [self.parser.build_siemplify_group(item) for item in items]

    def get_endpoints_for_group(self, group_name, max_endpoints_to_return):
        """
        Function that returns endpoints for a group in EPO
        :param group_name: {string} Name of a group
        :param max_endpoints_to_return: {int} Limit of endpoints that should be returned
        :return {List} List Of Endpoints
        """

        payload = {
            "$limit": 1,
            "$offset": 0,
            "$filter": f'{{"name":"{self.group_name}"}}',
        }

        response = self.session.get(self._get_full_url("list_groups"), params=payload)
        try:
            validate_response(response, "Unable to connect to McAfee Mvision ePO.")
        except:
            if response.status_code == 404:
                raise GroupNotFoundException(f"Group {self.group_name} not found")

        items = self.parser.get_items_json(response.json())
        group_id = items[0].get("id")

        if not group_id:
            raise GroupNotFoundException(f"Group {self.group_name} not found")

        list_of_endpoints = self.fetch_endpoints(group_id, max_endpoints_to_return)

        return list_of_endpoints

    def fetch_endpoints(self, group_id, max_endpoints_to_return):
        """
        Function that fetches endpoints for particular group
        :param group_id: {string} ID of the group
        :param max_endpoints_to_return: {int} Limit of endpoints that should be returned
        :return {List} List Of Endpoints
        """

        payload = {
            "$limit": max_endpoints_to_return,
            "$offset": 0,
            "$filter": f'{{"group.groupId":"{group_id}"}}',
        }

        response = self.session.get(self._get_full_url("devices"), params=payload)
        validate_response(response, "Unable to connect to McAfee Mvision ePO.")

        items = self.parser.get_items_json(response.json())
        return [self.parser.build_siemplify_endpoint(item) for item in items]

    def get_tags(self, max_tags_to_return):
        """
        Function that returns tags
        :param max_tags_to_return: {int} Limit of tags that should be returned
        :return {List} List Of Tags
        """
        payload = {"$limit": max_tags_to_return, "$offset": 0}

        response = self.session.get(self._get_full_url("tags"), params=payload)
        validate_response(response)

        tags = self.parser.get_items_json(response.json())

        return [self.parser.build_siemplify_tag_details(tag) for tag in tags]
