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
# title           :URLVoidManager.py
# description     :This Module contain all URLVoid cloud operations functionality
# author          :zdemoniac@gmail.com
# date            :01-06-18
# python_version  :2.7
# libreries       : copy, json, requests, urllib2, xml
# requirments     :
# product_version :
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests


# =====================================
#              CLASSES                #
# =====================================
class URLVoidManagerError(Exception):
    """
    General Exception for URLVoid manager
    """

    pass


class URLVoidManager:
    """
    Responsible for all URLVoid system operations functionality
    """

    def __init__(self, api_root, api_key, verify_ssl=False):
        self.api_key = api_key
        self.api_root = api_root
        self.session = requests.Session()
        self.session.verify = verify_ssl

    def test_connectivity(self):
        """
        Test connectivity to URLVoid
        :return: {bool} True if successful, exception otherwise.
        """
        response = self.session.get(
            url=f"{self.api_root}/domainbl/v1/pay-as-you-go/?stats",
            params={"key": self.api_key},
        )
        self.validate_response(response, "Unable to connect to URLVoid")
        return True

    def get_domain_reputation(self, domain):
        """
        Get domain reputation from URLVoid
        :param domain: {string}
        :return: {dict}
        """
        response = self.session.get(
            url=f"{self.api_root}/domainbl/v1/pay-as-you-go/",
            params={"host": domain, "key": self.api_key},
        )

        self.validate_response(response, f"Unable to get reputation for {domain}")

        return response.json().get("data", {}).get("report", {})

    @staticmethod
    def create_blacklist_report_from_raw_data(reputation_data):
        """
        Create a blacklist report dict from the raw reputation data
        :param reputation_data: {dict} The raw reputation data
        :return: {dict} Blacklist report
        """
        blacklist_report = []

        for engine in list(
            reputation_data.get("blacklists", {}).get("engines", {}).values()
        ):
            if "elapsed" in engine:
                # Elapsed - How long it took to get the data.
                # This is not important data - remove it.
                del engine["elapsed"]

            blacklist_report.append(engine)

        return blacklist_report

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response.json()
            except:
                raise URLVoidManagerError(f"{error_msg}: {error} - {response.content}")

            raise URLVoidManagerError(
                f"{error_msg}: {error} - {response.json().get('error', 'No error message.')}"
            )
