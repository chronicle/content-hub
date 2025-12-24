from __future__ import annotations

import copy
import datetime

import requests

ITEMS_PER_REQUEST = 50
API_ROOT = "https://gmc.banduracyber.com/api/v2/"
LOGIN = "{}/auth/login"
LOGOUT = "{}/auth/logout"
GET_API_TOKEN = "{}/auth/jwt/apikey"
GET_ALLOWED_DOMAIN_LIST = "{}/allowed-lists/domain"
GET_ALLOWED_DOMAIN_ENTITIES = "{}/allowed-lists/domain/{}/entries"
GET_ALLOWED_IP_LIST = "{}/allowed-lists/ipv4"
GET_ALLOWED_IP_ENTITIES = "{}/allowed-lists/ipv4/{}/entries"
GET_DENIED_DOMAIN_LIST = "{}/denied-lists/domain"
GET_DENIED_DOMAIN_ENTITIES = "{}/denied-lists/domain/{}/entries"
GET_DENIED_IP_LIST = "{}/denied-lists/ipv4"
GET_DENIED_IP_ENTITIES = "{}/denied-lists/ipv4/{}/entries"
GET_COMPANY_INFO = "{}/company/{}"

INSERT_DATE = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f+00:00")

# Headers.
HEADERS = {"Content-Type": "application/json"}

ENTITIES_PAYLOADS = {
    "page": "1",
    "perPage": "20",
    "search": "",
    "sortColumn": "",
    "sortDirection": "ascending",
}

CREATE_LIST_PAYLOAD = {
    "name": "",
    "description": "",
    "interval": "60",
    "pluginUuid": "00000000-6714-4000-8000-000000000000",
    "enabled": True,
    "type": "",
}

CREATE_ENTITY_PAYLOAD = {"expiresDatetime": ""}

CREATE_LIST_BODY = {"pluginParameters": {}}


# ============================= CLASSES ===================================== #


class BanduraCyberException(Exception):
    pass


class BanduraCyberManager:
    def __init__(self, username=None, password=None, api_token=None, verify_ssl=False):
        self.api_root = API_ROOT if API_ROOT[-1:] == "/" else API_ROOT + "/"
        self.session = requests.session()
        self.session.verify = verify_ssl
        login_info = self.login(username, password)
        self.access_token = login_info.get("accessToken")
        self.refresh_token = login_info.get("refreshToken")
        self.session.headers = copy.deepcopy(HEADERS)
        self.session.headers["Authorization"] = f"Bearer {self.access_token}"

    def login(self, username, password):
        request_url = LOGIN.format(self.api_root)
        payload = {"username": username, "password": password}
        response = self.session.post(request_url, json=payload)
        self.validate_response(response)
        return response.json()

    def logout(self):
        request_url = LOGOUT.format(self.api_root)
        payload = {"refreshToken": self.refresh_token}
        response = self.session.post(request_url, json=payload)
        self.validate_response(response)
        return True

    def get_api_token(self):
        request_url = GET_API_TOKEN.format(self.api_root)
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json().get("token")

    @staticmethod
    def filter_list_by_name(list_name, lists_data):
        for list_data in lists_data:
            if list_data.get("name") == list_name:
                return [list_data]

        return None  # "List {} not found".format(list_name)

    def show_denied_domain_list(self, list_name=None, cmp_uuid=None):
        """Retrieve existing object using object name
        :param group_name: {string}
        :return: {dict} Group details
        """
        request_url = GET_DENIED_DOMAIN_LIST.format(self.api_root)
        params = {"companyUuid": cmp_uuid}
        url_params = {k: v for k, v in list(params.items()) if v is not None}
        response = self.session.get(request_url, json=url_params)
        self.validate_response(response)

        if list_name:
            results = self.filter_list_by_name(list_name, response.json())
            return results
        return response.json()

    def show_denied_domain_entities(self, uuid):
        request_url = GET_DENIED_DOMAIN_ENTITIES.format(self.api_root, uuid)
        payload = copy.deepcopy(ENTITIES_PAYLOADS)
        response = self.session.get(request_url, json=payload)
        self.validate_response(response)
        return response.json()

    def show_denied_ip_list(self, list_name=None, cmp_uuid=None):
        """Retrieve existing object using object name
        :param group_name: {string}
        :return: {dict} Group details
        """
        request_url = GET_DENIED_IP_LIST.format(self.api_root)
        params = {"companyUuid": cmp_uuid}
        url_params = {k: v for k, v in list(params.items()) if v is not None}
        response = self.session.get(request_url, json=url_params)
        self.validate_response(response)

        if list_name:
            results = self.filter_list_by_name(list_name, response.json())
            return results
        return response.json()

    def show_denied_ip_entities(self, uuid):
        """Retrieve existing object using object name
        :param group_name: {string}
        :return: {dict} Group details
        """
        request_url = GET_DENIED_IP_ENTITIES.format(self.api_root, uuid)
        payload = copy.deepcopy(ENTITIES_PAYLOADS)
        response = self.session.get(request_url, json=payload)
        self.validate_response(response)
        return response.json()

    def show_allowed_domain_list(self, list_name=None, cmp_uuid=None):
        """Retrieve existing object using object name
        :param group_name: {string}
        :return: {dict} Group details
        """
        request_url = GET_ALLOWED_DOMAIN_LIST.format(self.api_root)
        params = {"companyUuid": cmp_uuid}
        url_params = {k: v for k, v in list(params.items()) if v is not None}
        response = self.session.get(request_url, json=url_params)
        self.validate_response(response)

        if list_name:
            results = self.filter_list_by_name(list_name, response.json())
            return results
        return response.json()

    def show_allowed_domain_entities(self, uuid):
        request_url = GET_ALLOWED_DOMAIN_ENTITIES.format(self.api_root, uuid)
        payload = copy.deepcopy(ENTITIES_PAYLOADS)
        response = self.session.get(request_url, json=payload)
        self.validate_response(response)
        return response.json()

    def show_allowed_ip_list(self, list_name=None, cmp_uuid=None):
        """Retrieve existing object using object name
        :param group_name: {string}
        :return: {dict} Group details
        """
        request_url = GET_ALLOWED_IP_LIST.format(self.api_root)
        params = {"companyUuid": cmp_uuid}
        url_params = {k: v for k, v in list(params.items()) if v is not None}
        response = self.session.get(request_url, json=url_params)
        self.validate_response(response)

        if list_name:
            results = self.filter_list_by_name(list_name, response.json())
            return results
        return response.json()

    def show_allowed_ip_entities(self, uuid):
        """Retrieve existing object using object name
        :param group_name: {string}
        :return: {dict} Group details
        """
        request_url = GET_ALLOWED_IP_ENTITIES.format(self.api_root, uuid)
        payload = copy.deepcopy(ENTITIES_PAYLOADS)
        response = self.session.get(request_url, json=payload)
        self.validate_response(response)
        return response.json()

    def create_denied_domain_list(
        self,
        name,
        description=None,
        interval="60",
        plugin_uuid="00000000-6714-4000-8000-000000000000",
        enabled="true",
        type="manual",
    ):
        """Retrieve existing object using object name
        :param group_name: {string}
        :return: {dict} Group details
        """
        request_url = GET_DENIED_DOMAIN_LIST.format(self.api_root)
        payload = copy.deepcopy(CREATE_LIST_PAYLOAD)
        payload["name"] = name
        payload["description"] = description
        payload["interval"] = interval
        payload["pluginUuid"] = plugin_uuid
        payload["enabled"] = enabled
        payload["type"] = type
        url_params = {k: v for k, v in list(payload.items()) if v is not None}
        response = self.session.post(request_url, json=url_params)
        self.validate_response(response)
        return response.json()

    def create_denied_ip_list(
        self,
        name,
        description=None,
        interval="60",
        plugin_uuid="00000000-6714-4000-8000-000000000000",
        enabled="true",
        type="manual",
    ):
        """Retrieve existing object using object name
        :param group_name: {string}
        :return: {dict} Group details
        """
        request_url = GET_DENIED_IP_LIST.format(self.api_root)
        payload = copy.deepcopy(CREATE_LIST_PAYLOAD)
        payload["name"] = name
        payload["description"] = description
        payload["interval"] = interval
        payload["pluginUuid"] = plugin_uuid
        payload["enabled"] = enabled
        payload["type"] = type
        url_params = {k: v for k, v in list(payload.items()) if v is not None}
        response = self.session.post(request_url, json=url_params)
        self.validate_response(response)
        return response.json()

    def create_allowed_domain_list(
        self,
        name,
        description=None,
        interval="60",
        plugin_uuid="00000000-6714-4000-8000-000000000000",
        enabled="true",
        type="manual",
    ):
        """Retrieve existing object using object name
        :param group_name: {string}
        :return: {dict} Group details
        """
        request_url = GET_ALLOWED_DOMAIN_LIST.format(self.api_root)
        payload = copy.deepcopy(CREATE_LIST_PAYLOAD)
        payload["name"] = name
        payload["description"] = description
        payload["interval"] = interval
        payload["pluginUuid"] = plugin_uuid
        payload["enabled"] = enabled
        payload["type"] = type
        url_params = {k: v for k, v in list(payload.items()) if v is not None}
        response = self.session.post(request_url, json=url_params)
        self.validate_response(response)
        return response.json()

    def create_allowed_ip_list(
        self,
        name,
        description=None,
        interval="60",
        plugin_uuid="00000000-6714-4000-8000-000000000000",
        enabled="true",
        type="manual",
    ):
        """Retrieve existing object using object name
        :param group_name: {string}
        :return: {dict} Group details
        """
        request_url = GET_ALLOWED_IP_LIST.format(self.api_root)
        payload = copy.deepcopy(CREATE_LIST_PAYLOAD)
        payload["name"] = name
        payload["description"] = description
        payload["interval"] = interval
        payload["pluginUuid"] = plugin_uuid
        payload["enabled"] = enabled
        payload["type"] = type
        url_params = {k: v for k, v in list(payload.items()) if v is not None}
        response = self.session.post(request_url, json=url_params)
        self.validate_response(response)
        return response.json()

    def add_allowed_ip_entity(
        self,
        list_name,
        address="string",
        maskbit="int",
        description=None,
        expires_date_time="",
    ):
        """Retrieve existing object using object name
        :param group_name: {string}
        :return: {dict} Group details
        """
        response = self.show_allowed_ip_list(list_name=list_name)
        list_uuid = response[0].get("uuid")

        request_url = GET_ALLOWED_IP_ENTITIES.format(self.api_root, list_uuid)
        payload = copy.deepcopy(CREATE_ENTITY_PAYLOAD)
        payload["address"] = address
        payload["maskbits"] = int(maskbit)
        payload["expiresDatetime"] = expires_date_time

        if description:
            payload["description"] = description

        url_params = {k: v for k, v in list(payload.items()) if v is not None}
        response = self.session.post(request_url, json=url_params)
        self.validate_response(response)
        return response.json()

    def add_allowed_domain_entity(
        self,
        list_name,
        domain="string",
        description=None,
        expires_date_time="",
    ):
        """Retrieve existing object using object name
        :param group_name: {string}
        :return: {dict} Group details
        """
        response = self.show_allowed_domain_list(list_name=list_name)
        list_uuid = response[0].get("uuid")

        request_url = GET_ALLOWED_DOMAIN_ENTITIES.format(self.api_root, list_uuid)
        payload = copy.deepcopy(CREATE_ENTITY_PAYLOAD)
        payload["domain"] = domain
        payload["expiresDatetime"] = expires_date_time

        if description:
            payload["description"] = description

        url_params = {k: v for k, v in list(payload.items()) if v is not None}
        response = self.session.post(request_url, json=url_params)
        self.validate_response(response)
        return response.json()

    def add_denied_ip_entity(
        self,
        list_name,
        address="string",
        maskbits="int",
        description=None,
        expires_date_time="",
    ):
        """Retrieve existing object using object name
        :param group_name: {string}
        :return: {dict} Group details
        """
        response = self.show_denied_ip_list(list_name=list_name)
        list_uuid = response[0].get("uuid")

        request_url = GET_DENIED_IP_ENTITIES.format(self.api_root, list_uuid)
        payload = copy.deepcopy(CREATE_ENTITY_PAYLOAD)
        payload["address"] = address
        payload["maskbits"] = int(maskbits)
        payload["expiresDatetime"] = expires_date_time

        if description:
            payload["description"] = description

        url_params = {k: v for k, v in list(payload.items()) if v is not None}
        response = self.session.post(request_url, json=url_params)
        self.validate_response(response)
        return response.json()

    def add_denied_domain_entity(
        self,
        list_name,
        domain="string",
        description=None,
        expires_date_time=None,
    ):
        """Retrieve existing object using object name
        :param group_name: {string}
        :return: {dict} Group details
        """
        response = self.show_denied_domain_list(list_name=list_name)
        list_uuid = response[0].get("uuid")

        request_url = GET_DENIED_DOMAIN_ENTITIES.format(self.api_root, list_uuid)
        payload = copy.deepcopy(CREATE_ENTITY_PAYLOAD)
        payload["domain"] = domain
        payload["expiresDatetime"] = expires_date_time

        if description:
            payload["description"] = description

        url_params = {k: v for k, v in list(payload.items()) if v is not None}
        response = self.session.post(request_url, json=url_params)
        self.validate_response(response)
        return response.json()

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """Validate a response
        :param response: {requests.Response} The response to validate
        :param error_msg: {str} The message to display on error
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            raise BanduraCyberException(
                f"{error_msg}: {error} - {error.response.content}",
            )
