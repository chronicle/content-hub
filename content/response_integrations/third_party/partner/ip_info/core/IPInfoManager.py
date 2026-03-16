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

# ==============================================================================
# title           :SentinelOneV2Manager.py
# description     :SentinelOne integration logic.
# author          :victor@siemplify.co
# date            :21-3-18
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
#               CONSTS                #
# =====================================
HEADERS = {"Authorization": "Bearer {0}"}

GET_DOMAINS_INFORMATION_URL = "/domains"

TEST_IP = "8.8.8.8"

API_LIMIT_STATUS_CODE = 429

ERROR_WORD = b"error"


# =====================================
#              CLASSES                #
# =====================================
class IPInfoManagerError(Exception):
    pass


class IPInfoManager:
    def __init__(self, api_root, token, verify_ssl=False):
        """
        :param api_root: {string} IPInfo api root URL.
        :param token: {string} Authorization token.
        """
        self.api_root = api_root if api_root[-1:] == "/" else api_root + "/"
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers = copy.deepcopy(HEADERS)
        self.session.headers["Authorization"] = self.session.headers["Authorization"].format(token)

    @staticmethod
    def validate_response(response):
        """
        Validate HTTP response and raise informative Exception.
        :param response: HTTP response object.
        :return: {void}
        """
        try:
            response.raise_for_status()
            if ERROR_WORD in response.content.lower():
                raise IPInfoManagerError(f"Failed processing request., ERROR: {response.content}")
            response.json()

        except Exception as err:
            if response.status_code == API_LIMIT_STATUS_CODE:
                raise IPInfoManagerError(f"API limit exceeded. Error: {err}")
            raise IPInfoManagerError(f"Error:{err}, Content:{response.content}")

    def ping(self):
        """
        Test token validity.
        :return: {bool} True if succeed.
        """
        request_url = urllib.parse.urljoin(self.api_root, TEST_IP)
        response = self.session.get(request_url)
        self.validate_response(response)
        return True

    def get_ip_information(self, ip_address):
        """
        Fetch information for IP address.
        :param ip_address: {string} Target IP address.
        :return: {dict} Address Information.
        """
        request_url = urllib.parse.urljoin(self.api_root, ip_address)
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def get_domains_information(self, domain_name):
        """
        Get information for domain name.
        :param domain_name: {string} Target domain name.
        :return: {dict} Domain information.
        """
        request_url = (rf"{urllib.parse.urljoin(self.api_root, GET_DOMAINS_INFORMATION_URL)}/"
                       rf"{urllib.parse.quote_plus(domain_name)}")
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()


#
