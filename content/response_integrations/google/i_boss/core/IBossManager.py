from __future__ import annotations
from .IBossParser import IBossParser
from .UtilsManager import validate_response
import requests
from urllib.parse import urljoin
from .exceptions import ListIsNotBlockListException

ENDPOINTS = {
    "me": "/ibcloud/web/users/me",
    "get_fqdn": "/ibcloud/web/account/clusters",
    "login": "/json/login?ignoreAuthModule=true",
    "ping": "/json/preferences/time",
    "add_url_to_policy_block_list": "/json/controls/policyLayers/urls",
    "remove_url_from_policy_block_list": "/json/controls/policyLayers/urls",
    "list_policy_block_list_entries": "/json/controls/policyLayers/urls",
    "add_ip_to_block_list": "/json/controls/policyLayers/urls",
    "remove_ip_from_iboss_block_list": "/json/controls/policyLayers/urls",
    "url_recategorization": "/json/controls/urlLookup/recatSite",
    "settings": "json/controls/policyLayers/settings",
    "url_lookup": "json/controls/urlLookup",
}

TOKEN_ENDPOINT = "{}ibossauth/web/tokens"
AUTH_PAYLOAD = {"ignoreAuthModule": "true"}
PROTOCOL = "https://"
GET_ALL_NODES_COOKIE = "JSESSIONID={}; XSRF-TOKEN= {};"


class IBossManager:

    def __init__(
        self,
        cloud_api_root,
        account_api_root,
        username,
        password,
        verify_ssl=False,
        siemplify_logger=None,
    ):
        """
        The method is used to init an object of Manager class
        :param cloud_api_root: Cloud API Root of iBoss
        :param account_api_root: Account API Root of iBoss
        :param username: Specify username of the IBoss account
        :param password: Specify password of the IBoss account
        :param verify_ssl: Enable (True) or disable (False). If enabled, verify the SSL certificate for the connection to the IBoss public cloud server is valid
        :param siemplify_logger: Siemplify logger.
        """
        self.username = username
        self.password = password
        self.siemplify_logger = siemplify_logger
        self.parser = IBossParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.cloud_api_root = cloud_api_root
        self.account_api_root = account_api_root
        self.token = self.get_auth_token()
        self.api_root = self.get_account_setting_id()
        self.set_cookie()

    def get_account_setting_id(self):
        self.set_authorization()
        account_settings_id, xsrf_token, jsession_id = (
            self.get_account_settings_id_and_headers()
        )

        self.session.headers.update(
            {
                "Cookie": GET_ALL_NODES_COOKIE.format(jsession_id, xsrf_token),
                "X-XSRF-TOKEN": xsrf_token,
            }
        )

        params = {"accountSettingsId": account_settings_id}

        response = self.session.get(self._get_cloud_full_url("get_fqdn"), params=params)
        validate_response(response)

        return f"{PROTOCOL}{self.parser.prepare_master_admin_interface_dns(response.json())}"

    def set_authorization(self):
        """
        Set authorization header to request session.
        """
        self.session.headers.update({"Authorization": f"Token {self.token}"})

    def get_account_settings_id_and_headers(self):
        """
        Send request in order to get account settings id and headers.
        :return: {tuple} account_settings_id, xsrf_token, jsession_id
        """
        response = self.session.get(self._get_cloud_full_url("me"))
        validate_response(response)
        return self.parser.get_account_settings_id_and_headers(
            response.json(), response.cookies.get_dict()
        )

    def set_cookie(self):
        """
        Set cookie header to request session.
        """
        self.session.headers.update({"Cookie": self.get_cookie(self.token)})

    def get_cookie(self, auto_token):
        """
        Send request in order to get cookie
        :param auto_token: {str} The auth token.
        :return: {str} The uid and sessionsId
        """

        payload = {"userName": auto_token, "x": "", "ldapServer": ""}
        login_response = self.session.post(self._get_full_url("login"), json=payload)
        validate_response(login_response)
        return self.parser.get_cookie(login_response.json())

    def get_auth_token(self):
        """
        Send request in order to get generated token.
        :return: {str} The auth token to use for the next requests
        """

        token_response = self.session.get(
            TOKEN_ENDPOINT.format(self.account_api_root),
            auth=(self.username, self.password),
            params=AUTH_PAYLOAD,
        )

        validate_response(token_response)
        return self.parser.get_auth_token(token_response.json())

    def _get_cloud_full_url(self, url_id):
        """
        Get cloud full url from url identifier.
        :param url_id: {str} The id of url
        :return: {str} The cloud full url
        """
        return urljoin(self.cloud_api_root, ENDPOINTS[url_id])

    def _get_full_url(self, url_id):
        """
        Send full url from url identifier.
        :param url_id: {str} The id of url
        :return: {str} The full url
        """

        return urljoin(self.api_root, ENDPOINTS[url_id])

    def test_connectivity(self):
        """
        Test connectivity to the IBoss.
        :return: {bool} True if successful, exception otherwise
        """
        response = self.session.get(self._get_full_url("ping"))
        validate_response(response)

    def validate_if_block_list(self, category_id):
        """
        Validate if block list
        :param category_id: {int} The category id of the list to validate if block list
        :return: {bool} True if block list, ListIsNotBlockListException otherwise
        """
        payload = {"customCategoryId": category_id}

        response = self.session.get(self._get_full_url("settings"), params=payload)
        validate_response(response)
        if self.parser.custom_type_from_settings_raw_json(response.json()) == 0:
            return True

        raise ListIsNotBlockListException

    def add_url_to_policy_block_list(
        self,
        url,
        category_id,
        priority,
        direction,
        start_port,
        end_port,
        note,
        is_regex,
    ):
        """
        Add url to policy block list.
        :param url: {str} The url to add
        :param category_id: {int} Specify in which policy category do you want to list Block List entries
        :param priority: {int} Specify priority of the URL that needs to be blocked
        :param direction: {int} Specify what is the direction of the URL
        :param start_port: {int} Specify the start port related to the URL that needs to be blocked. Note: if only Start Port or End Port is specified, the value will be added to the both action parameters
        :param end_port: {int} Specify the end port related to the URL that needs to be blocked. Note: if only Start Port or End Port is specified, the value will be added to the both action parameters.
        :param note: {str} Add a note related to the URL that needs to be blocked
        :param is_regex: {bool} If enabled, URL will be considered as a regular expression
        :return: {bool} True if successful, exception otherwise
        """
        payload = {
            "url": url,
            "priority": priority,
            "direction": direction,
            "startPort": start_port,
            "endPort": end_port,
            "isRegex": is_regex,
            "note": note,
            "customCategoryId": category_id,
        }

        response = self.session.put(
            self._get_full_url("add_url_to_policy_block_list"), json=payload
        )
        validate_response(response)

        return True

    def remove_url_from_policy_block_list(self, url, category_id, start_port, end_port):
        """
        Remove url from policy block list.
        :param url: {str} The url to remove
        :param category_id: {int} Specify in which policy category do you want to list Block List entries
        :param start_port: {int} Specify start port related to the URL that needs to be deleted. This parameter is mandatory, if the desired URL has a defined start port. This is an IBoss limitation
        :param end_port: {int} Specify end port related to the URL that needs to be deleted. This parameter is mandatory, if the desired URL has a defined end port. This is an IBoss limitation
        :return: {bool} True if successful, exception otherwise
        """
        payload = {"url": url, "customCategoryId": category_id}
        if start_port:
            payload["startPort"] = start_port

        if end_port:
            payload["endPort"] = end_port

        response = self.session.delete(
            self._get_full_url("remove_url_from_policy_block_list"), params=payload
        )
        validate_response(response)

        return True

    def list_policy_block_list_entries(self, category_id, max_entries_to_return):
        """
        List policy block list entries.
        :param category_id: {str} Specify in which policy category do you want to list Block List entries
        :param max_entries_to_return: {int} Specify how many entries to return
        :return: {bool} True if successful, exception otherwise
        """
        payload = {"customCategoryId": category_id}

        response = self.session.get(
            self._get_full_url("list_policy_block_list_entries"), params=payload
        )

        validate_response(response)

        return self.parser.get_entries(response.json())[:max_entries_to_return]

    def add_ip_to_block_list(
        self, ip, category_id, priority, direction, start_port, end_port, note, is_regex
    ):
        """
        Add ip to block list.
        :param ip: {str} The ip to add
        :param category_id: {int} Specify in which policy category do you want to list Block List entries
        :param priority: {int} Specify priority of the IP that needs to be blocked
        :param direction: {int} Specify what is the direction of the IP
        :param start_port: {int} Specify the start port related to the IP that needs to be blocked. Note: if only \"Start Port\" or \"End Port\" is specified, the value will be added to the both action parameters
        :param end_port: {int} Specify the end port related to the IP that needs to be blocked. Note: if only \"Start Port\" or \"End Port\" is specified, the value will be added to the both action parameters
        :param note: {str} Add a note related to the IP that needs to be blocked
        :param is_regex: {bool} If enabled, IP will be considered as a regular expression
        :return: {bool} True if successful, exception otherwise
        """
        payload = {
            "url": ip,
            "priority": priority,
            "direction": direction,
            "startPort": start_port,
            "endPort": end_port,
            "isRegex": is_regex,
            "note": note,
            "customCategoryId": category_id,
        }

        response = self.session.put(
            self._get_full_url("add_ip_to_block_list"), json=payload
        )
        validate_response(response)

        return True

    def remove_ip_from_iboss_block_list(self, ip, category_id, start_port, end_port):
        """
        Remove ip from iBoss block list.
        :param ip: {str} The ip to remove
        :param category_id: {int} Specify in which policy category do you want to list Block List entries
        :param start_port: {int} Specify start port related to the IP that needs to be deleted. This parameter is mandatory, if the desired URL has a defined start port. This is an IBoss limitation
        :param end_port: {int} Specify end port related to the IP that needs to be deleted. This parameter is mandatory, if the desired IP has a defined end port. This is an IBoss limitation
        :return: {bool} True if successful, exception otherwise
        """
        payload = {"url": ip, "customCategoryId": category_id}

        if start_port:
            payload["startPort"] = start_port

        if end_port:
            payload["endPort"] = end_port

        response = self.session.delete(
            self._get_full_url("remove_ip_from_iboss_block_list"), params=payload
        )
        validate_response(response)

        return True

    def url_recategorization(self, url):
        """
        Submit URL for recategorization.
        :param url: {str} The url to submit
        :return: {bool} True if successful, exception otherwise
        """
        payload = {"url": url}

        response = self.session.post(
            self._get_full_url("url_recategorization"), json=payload
        )
        validate_response(response)
        return True

    def url_lookup(self, url, group_id):

        payload = {"action": "submit", "lookupUrl": url}

        if group_id:
            payload["selfLookupPageGroup"] = group_id

        response = self.session.post(self._get_full_url("url_lookup"), json=payload)
        validate_response(response)
        return self.parser.build_url_object(response.json())
