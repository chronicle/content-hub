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
from .McAfeeMvisionEPOV2Parser import McAfeeMvisionEPOV2Parser
from .UtilsManager import validate_response
import requests
from urllib.parse import urljoin
from .constants import INTEGRATION_DISPLAY_NAME, PER_PAGE_LIMIT, DEFAULT_SCOPES
from .exceptions import (
    UnableToGetTokenException,
    TagNotFoundException,
    DeviceNotFoundException,
)

ENDPOINTS = {
    "login": "/iam/v1.0/token",
    "tags": "/epo/v2/tags",
    "devices": "/epo/v2/devices",
    "events": "/epo/v2/events",
    "add_remove_tag_from_device": "/epo/v2/devices/{}/relationships/assignedTags",
}


class McAfeeMvisionEPOV2Manager:
    def __init__(
        self,
        api_root,
        iam_root,
        client_id,
        client_secret,
        api_key,
        scopes=DEFAULT_SCOPES,
        verify_ssl=False,
        siemplify_logger=None,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: McAfee Mvision ePO API Root
        :param client_id: Client ID of the McAfee Mvision ePO account
        :param client_secret: Client Secret of the McAfee Mvision ePO account
        :param scopes: Scopes of the McAfee Mvision ePO account
        :param group_name: Group name that will be used to search for endpoints.
                          If nothing is specified. All of the groups will be used
        :param verify_ssl: Enable (True) or disable (False). If enabled,
                           verify the SSL certificate for the connection to the McAfee
                           Mvision ePO public cloud server is valid.
        :param siemplify_logger: Siemplify logger.
        """
        self.api_root = api_root
        self.iam_root = iam_root
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_key = api_key
        self.scopes = scopes
        self.siemplify_logger = siemplify_logger

        self.parser = McAfeeMvisionEPOV2Parser()

        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers["x-api-key"] = self.api_key

        self.set_auth_token()

        self.session.headers["Content-Type"] = "application/vnd.api+json"

        self.already_loaded_devices = []
        self.all_devices_loaded = False

        # Because we are using one host for getting token, and another one for
        # fetching data, we need to call
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
                self._get_full_url("login", self.iam_root),
                auth=(self.client_id, self.client_secret),
                params={"grant_type": "client_credentials", "scope": self.scopes},
            )
            validate_response(login_response)
            return self.parser.get_auth_token(login_response.json())
        except Exception as err:
            raise UnableToGetTokenException(f"{INTEGRATION_DISPLAY_NAME}: {err}")

    def _get_full_url(self, url_id, api_root=None):
        """
        Send full url from url identifier.
        :param api_root: {unicode} The api root
        :param url_id: {unicode} The id of url
        :return: {unicode} The full url
        """
        return urljoin(api_root or self.api_root, ENDPOINTS[url_id])

    def test_connectivity(self):
        """
        Test connectivity to the McAfee Mvision ePO.
        :return: {bool} True if successful, exception otherwise
        """
        params = {"page[limit]": 1, "page[offset]": 0}

        response = self.session.get(self._get_full_url("devices"), params=params)
        validate_response(response, "Unable to connect to McAfee Mvision ePO (V2).")
        return True

    def find_tag_or_fail(self, tag_name):
        """
        Find Tag by name or rise not found exception.
        :param tag_name: {str} The name of the tag
        :return: {Tag} The tag
        """
        response = self.session.get(
            self._get_full_url("tags"), params={"filter[name][EQ]": tag_name}
        )

        if response.status_code == 404:
            raise TagNotFoundException(f"Tag {tag_name} not found")

        validate_response(response, f"Unable to find tag {tag_name}")
        items_json = response.json().get("data", [])

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
            raise DeviceNotFoundException

        return matched_device[0]

    def load_more_devices(self):
        """
        Load more devices. This action works like pagination.
        :return: {list} The list of the loaded devices
        """
        response = self.session.get(
            self._get_full_url("devices"),
            params={
                "page[offset]": len(self.already_loaded_devices),
                "page[limit]": PER_PAGE_LIMIT,
            },
        )
        validate_response(response, "Unable to get devices")
        response_json = response.json()

        total_items = self.parser.get_total_items(response_json)
        devices = [
            self.parser.build_siemplify_device(device_json)
            for device_json in response.json().get("data", [])
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
        if is_host:
            return device.hostname == identifier

        return device.ip == identifier

    def add_or_remove_tag(self, device, tag, add=True):
        """
        Add or remove tag.
        :param device: {Device} The device to add the tag
        :param tag: {Tag} The tag to attache the device
        :param add: {bool} If true it will add the tag to device, else will remove
        :return: {bool} True if the successful
        """
        payload = {"data": [{"type": "tags", "id": int(tag.tag_id)}]}
        if add:
            response = self.session.post(
                self._get_full_url("add_remove_tag_from_device").format(
                    device.device_id
                ),
                json=payload,
            )
            validate_response(
                response, f"Unable to add tag {tag.tag_id} to device {device.device_id}"
            )

        else:
            response = self.session.delete(
                self._get_full_url("add_remove_tag_from_device").format(
                    device.device_id
                ),
                json=payload,
            )
            validate_response(
                response,
                f"Unable to remove tag {tag.tag_id} from device {device.device_id}",
            )

        return True

    def get_tags(self, max_tags_to_return):
        """
        Function that returns tags
        :param max_tags_to_return: {int} Limit of tags that should be returned
        :return {List} List Of Tags
        """
        payload = {"page[limit]": max_tags_to_return, "page[offset]": 0}

        response = self.session.get(self._get_full_url("tags"), params=payload)
        validate_response(response, "Unable to get tags")

        return [
            self.parser.build_siemplify_tag(tag)
            for tag in response.json().get("data", [])
        ]

    def get_devices(self, max_devices_to_return):
        """
        Function that returns devices
        :param max_devices_to_return: {int} Limit of devices that should be returned
        :return {Device} List Of Devices
        """
        payload = {"page[limit]": max_devices_to_return, "page[offset]": 0}

        response = self.session.get(self._get_full_url("devices"), params=payload)
        validate_response(response, "Unable to get devices")

        return [
            self.parser.build_siemplify_device(device)
            for device in response.json().get("data", [])
        ]

    def get_events(self, start_time=None, limit=None, asc=True, existing_ids=None):
        """
        Get events
        :param start_time: {str} Timestamp to fetch events from
                           (ISO format, i,e: 2020-11-10T12:24:42.855Z)
        :param limit: {int} Max number of events to fetch
        :param asc: {bool} Whether to fetch events in ascending or descending order
        :param existing_ids: {list} List of existing IDs to filter out
        :return: {[Event]} List of found events
        """
        payload = {
            "page[limit]": min(limit, PER_PAGE_LIMIT) if limit else None,
            "filter[timestamp][GE]": start_time,
            "sort": "timestamp" if asc else "-timestamp",
        }

        payload = {k: v for k, v in payload.items() if v is not None}

        response = self.session.get(self._get_full_url("events"), params=payload)
        validate_response(response, "Unable to get events")

        all_events = [
            self.parser.build_siemplify_event(event)
            for event in response.json().get("data", [])
        ]

        if existing_ids:
            all_events = [
                event for event in all_events if event.event_id not in existing_ids
            ]

        next_link = response.json().get("links", {}).get("next")

        while next_link:
            if limit and len(all_events) >= limit:
                break

            url = f"{self.api_root}{next_link}"
            response = self.session.get(url)
            validate_response(response, "Unable to get events")

            events = [
                self.parser.build_siemplify_event(event)
                for event in response.json().get("data", [])
            ]

            if existing_ids:
                events = [
                    event for event in events if event.event_id not in existing_ids
                ]

            all_events.extend(events)
            next_link = response.json().get("links", {}).get("next")

        return all_events[:limit] if limit else all_events
