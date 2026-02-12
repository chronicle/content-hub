# ==============================================================================
# title           :ElasticseasrchManager.py
# description     :This Module contain all Elastic Search functionality
# author          :victor@siemplify.co
# date            :12-10-18
# python_version  :2.7
# ==============================================================================
# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations

import copy
import urllib.parse

import requests

# =====================================
#             CONSTANTS               #
# =====================================
# URLs
PING_URL = "api/V2/ping"
GET_DEVICES_URL = "api/v2/devices"
GET_LABELS_URL = "api/v2/labels/label_summary"
ACT_ON_DEVICE_URL = "api/v2/devices/action"
GET_DEVICE_DETAILS_URL = "api/v2/devices/{0}/details"  # {0} - Device UUID.

CLOUD_ROOT_URL_POSTFIX = "rest/"

# Params
GET_DEVICES_PARAMS = {"adminDeviceSpaceId": 1, "query": "", "fields": ""}

GET_LABELS_PARAMS = {"adminDeviceSpaceId": 1, "limit": 200}

ACT_ON_DEVICE_PARAMS = {
    "adminDeviceSpaceId": "",
    "actionType": "",
    "deviceUuids": [],
    "additionalParameters": {},
    "message": "",
    "mode": "",  # sms, pns or email.
    "subject": "",
}

# Consts
DEFAULT_FIELDS_TO_FETCH = """
android.afw_capable,android.attestation,common.background_status,common.battery_level,
common.client_name,common.client_version,common.clientId,common.comment,common.compliant,common.creation_date,
common.current_phone_number,common.data_protection_enabled,common.data_protection_reasons,common.device_admin_enabled,
common.device_is_compromised,common.device_space_name,common.ethernet_mac,common.home_country_name,
common.home_operator_name,common.id,common.imei,common.imsi,common.ip_address,common.language,common.last_connected_at,
common.locale,common.manufacturer,common.mdm_managed,common.memory_capacity,common.memory_free,
common.miclient_last_connected_at,common.model,common.noncompliance_reasons,common.os_version,common.owner,
common.platform,common.platform_name,common.quarantined,common.quarantined_reasons,common.registration_date,
common.status,common.storage_capacity,common.storage_capacity,common.storage_free,common.uuid,ios.DataRoamingEnabled,
ios.DeviceName,user.display_name,user.email_address,user.user_id
"""

DEFAULT_ADMIN_DEVICE_ID = 1
DEFAULT_LABELS_LIMIT = 200  # Maximum rate.

DEVICE_UNLOCK_ACTION_STRING = "UNLOCK_DEVICE_ONLY"
DEFAULT_DEVICE_ACTION_MESSAGE_MODE = "sms"
DEFAULT_ACTION_MESSAGE_SUBJECT = DEFAULT_ACTION_MESSAGE = "Action was executed by Siemplify."
GET_DEVICE_BY_IP_QUERY = 'common.ip_address "contains" {0}'  # {0} - IP address.
DEVICE_UUID_FIELD = "common.uuid"


# =====================================
#              CLASSES                #
# =====================================
class MobileIronManagerError(Exception):
    pass


class MobileIronManager:
    def __init__(
        self,
        api_root,
        username,
        password,
        admin_device_id=DEFAULT_ADMIN_DEVICE_ID,
        connected_cloud=False,
        verify_ssl=False,
    ):
        """
        :param username: {string} API username.
        :param password: {string} API username password.
        :param verify_ssl: {bool} Verify SSL processing requests.
        """
        self.api_root = api_root if api_root[-1:] == "/" else api_root + "/"
        if connected_cloud:
            self.api_root = urllib.parse.urljoin(self.api_root, CLOUD_ROOT_URL_POSTFIX)
        self.admin_device_id = admin_device_id
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.auth = (username, password)

    @staticmethod
    def validate_response(response):
        """
        HTTP response validation.
        :param response: {HTTP response object}
        :return: throws exception if there is exception at the response {void}
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as err:
            raise MobileIronManagerError(
                f"Failed processing request to MobileIron, Status Code:{response.status_code}, Error:{err}, Content: {response.content}"
            )

    @staticmethod
    def rearrange_details_output(output_dict):
        """
        Rearrange output.
        :param output_dict: {list} Output values.
        :return: {dict} Rearranged output.
        """
        result_dict = {}
        for item in output_dict:
            if item.get("name"):
                result_dict[item.get("name")] = item.get("value")
        return result_dict

    def ping(self):
        """
        Verify API validity.
        :return: {bool/exception} True for success.
        """
        request_url = urllib.parse.urljoin(self.api_root, PING_URL)
        response = self.session.get(request_url)
        self.validate_response(response)
        return True

    def fetch_labels(self, limit=DEFAULT_LABELS_LIMIT):
        """
        Fetch label information by query.
        :param: admin_device_id: {integerDevice space ID of the administrator
        :param: limit: {integer} Indicates the maximum number of entries to return. Must be at
        least 0 and no more than 200.
        :return: {dict} Label information.
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_LABELS_URL)
        params = copy.deepcopy(GET_LABELS_PARAMS)
        params["adminDeviceSpaceId"] = self.admin_device_id
        params["limit"] = limit

        response = self.session.get(request_url, params=params)
        self.validate_response(response)
        return response.json().get("results", [])

    def get_label_id_by_name(self, label_name):
        """
        Get lablel id by it's name.
        :param label_name: {string} Label name.
        :return: {string} Label ID.
        """
        labels = self.fetch_labels()
        for label in labels:
            if label.get("name", "").lower() == label_name.lower() and label.get("id"):
                return label.get("id")
        raise MobileIronManagerError(
            f'Failed fetching label with name "{label_name}", Error: Label was not found.'
        )

    def fetch_devices(self, query="", fields_to_fetch=DEFAULT_FIELDS_TO_FETCH):
        """
        :param query: {string} Query for device parameters.
        :param fields_to_fetch: {string} Fields to fetch in  query result.
        :return: {list} List of device objects.
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_DEVICES_URL)
        params = copy.deepcopy(GET_DEVICES_PARAMS)
        params["adminDeviceSpaceId"] = self.admin_device_id
        params["query"] = query
        params["fields"] = fields_to_fetch

        response = self.session.get(request_url, params=params)
        self.validate_response(response)
        return response.json().get("results", [])

    def unlock_device_by_uuid(
        self,
        device_uuid,
        message=DEFAULT_ACTION_MESSAGE,
        mode=DEFAULT_DEVICE_ACTION_MESSAGE_MODE,
        subject=DEFAULT_ACTION_MESSAGE_SUBJECT,
    ):
        """
        Unlock device by it's UUID.
        :param device_uuid: {string} UUID String of the device on which to perform the action.
        :param message: {string} Message to send.
        :param mode: {string} Mode of transmission for the message.Has to be sms, pns or email.
        :param subject: {string} Subject of the message.
        :return: {bool}
        """
        request_url = urllib.parse.urljoin(self.api_root, ACT_ON_DEVICE_URL)
        params = copy.deepcopy(ACT_ON_DEVICE_PARAMS)
        params["adminDeviceSpaceId"] = self.admin_device_id
        params["actionType"] = DEVICE_UNLOCK_ACTION_STRING
        params["deviceUuids"].append(device_uuid)
        params["message"] = message
        params["mode"] = mode
        params["subject"] = subject

        response = self.session.post(request_url, params=params)
        self.validate_response(response)
        return True

    def fetch_device_information_by_ip(self, ip_address, fields_to_fetch=DEFAULT_FIELDS_TO_FETCH):
        """
        Fetch device information by IP address.
        :param ip_address: {string} IP address to search the device by.
        :param fields_to_fetch: {string} Desired fields to fetch.
        :return: {dict} Device system information.
        """
        query = GET_DEVICE_BY_IP_QUERY.format(ip_address)
        if fields_to_fetch:
            devices = self.fetch_devices(query=query, fields_to_fetch=fields_to_fetch)
        else:
            devices = self.fetch_devices(query=query, fields_to_fetch=DEFAULT_FIELDS_TO_FETCH)
        if devices:
            return devices[0]
        raise MobileIronManagerError(
            f'Failed fetching device for address "{ip_address}", ERROR: Device was not found.'
        )

    def get_device_uuid_by_ip_address(self, ip_address):
        """
        Get device uuid by IP address.
        :param ip_address: {string} IP address to search the device by.
        :return: {string} Device UUID.
        """
        device = self.fetch_device_information_by_ip(ip_address)
        return device.get(DEVICE_UUID_FIELD)

    def get_device_details_by_uuid(self, device_uuid):
        """
        Get device details using it's UUID.
        :param device_uuid: {string} Device UUID.
        :return: {dict} Device Information.
        """
        request_url = urllib.parse.urljoin(
            self.api_root, GET_DEVICE_DETAILS_URL.format(device_uuid)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json().get("results", [])
