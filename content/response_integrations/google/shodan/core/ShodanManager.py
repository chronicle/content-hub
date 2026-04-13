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
# title           : ShodanManager.py
# description     : Responsible for all Shodan system operations functionality
# author          : zivh@siemplify.co
# date            : 12-24-18
# python_version  : 2.7
# libraries       : -
# requirements    :
# product_version : v1
# api-doc         : https://developer.shodan.io/api/exploits/rest
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
# =====================================
#              CONSTS                 #
# =====================================
BASE_URL = "https://api.shodan.io"
BASE_EXPLOITS_URL = "https://exploits.shodan.io/api"

NOT_FOUNT_RESPONSE_STATUS = 404
RATE_LIMIT_RESPONSE_STATUS = 429
ERROR_STATUS = 401

IP_NOT_FOUND_MSG = "No information available for that IP"


# =====================================
#              CLASSES                #
# =====================================


class ShodanException(Exception):
    pass


class ShodanIPNotFoundException(Exception):
    pass


class ShodanManager:
    """
    Responsible for all Shodan system operations functionality
    """

    def __init__(self, api_key, verify_ssl=False):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.verify = verify_ssl

    def test_connectivity(self):
        """
        Check connectivity by get api info
        """
        return self.get_api_info()

    def get_ip_info(self, ip, history=False, minify=False):
        """
        Get all available information on an IP
        :param ip: [String] Host IP address. e.g.('8.8.8.8')
        :param history: [Boolean] True if all historical banners should be returned (default: False)
        :param minify: [Boolean] True to only return the list of ports and the general host information, no banners.
        :return: Returns all services that have been found on the given host IP.
        """
        params = {"key": self.api_key}
        if history:
            params["history"] = history
        if minify:
            params["minify"] = minify

        url = f'{BASE_URL}/{"shodan/host"}/{ip}'
        response = self.session.get(url, params=params)
        return self.validate_response(response)

    def search(self, query, facets=None, minify=True):
        """
        Search the SHODAN database.
        :param query: {string} Search query; identical syntax to the website. e.g. find Apache webservers located in Germany ("apache country:DE")
        (apache country:"DE", city:"Berlin")
        :param facets: {string} A comma-separated list of properties to get summary information on. Property names can also be in the format of "property:count"
        :param minify: {bool} Whether to minify the banner and only return the important data
        :return: {dict}  with 2 main items: matches and total. If facets have been provided then another property called "facets" will be available at the top-level of the dictionary.
        """
        # Page number of the search results
        args = {"key": self.api_key, "query": query, "minify": minify, "page": 1}

        if facets:
            args["facets"] = facets

        url = f'{BASE_URL}/{"shodan/host/search"}'
        response = self.session.get(url, params=args)
        return self.validate_response(response)

    def scan(self, ips):
        """
        Scan a network using Shodan
        requirements: This method uses API scan credits: 1 IP consumes 1 scan credit. You must have a paid API plan (either one-time payment or subscription) in order to use this method.
        :param ips: {string} A comma-separated list of IPs or netblocks (in CIDR notation) that should get crawled.
        :return: A dictionary with a unique ID to check on the scan progress, the number of IPs that will be crawled and how many scan credits are left.
        """
        url = f'{BASE_URL}/{"shodan/scan"}'
        params = {"key": self.api_key, "ips": ips}
        response = self.session.post(url, params=params)
        return self.validate_response(response)

    def dns_resolve(self, hostnames):
        """
        Look up the IP address for the provided list of hostnames.
        :param hostnames: {string} A comma-separated list of hostnames. e.g. ("google.com,bing.com")
        :return: {dict} {hostname: ip address}
        """
        url = f'{BASE_URL}/{"dns/resolve"}'
        params = {"key": self.api_key, "hostnames": hostnames}
        response = self.session.get(url, params=params)
        return self.validate_response(response)

    def dns_reverse(self, ips):
        """
        Look up the hostnames that have been defined for the given list of IP addresses
        :param ips: {string} A comma-separated list of ip addresses. e.g. "8.8.8.8,204.79.197.200"
        :return: {dict} {ip address: hostname}
        """
        url = f'{BASE_URL}/{"dns/reverse"}'
        params = {"key": self.api_key, "ips": ips}
        response = self.session.get(url, params=params)
        return self.validate_response(response)

    def get_api_info(self):
        """
        Returns information about the API plan belonging to the given API key.
        :return: {dict} api information
        """
        url = f"{BASE_URL}/{'api-info'}"
        params = {"key": self.api_key}
        res = self.session.get(url, params=params)
        return self.validate_response(res)

    def search_for_exploits(self, query, facets=None, page=1):
        """
        Search across a variety of data sources for exploits and use facets to get summary information.
        :param query: {string} Search query used to search the database of known exploits.
        :param facets: {string}  A comma-separated list of properties to get summary information on
        :param page: {int} The page number to page through results 100 at a time.
        :return: {dict}
        """
        args = {"key": self.api_key, "query": query, "page": page}

        if facets:
            args["facets"] = facets

        url = f'{BASE_EXPLOITS_URL}/{"search"}'
        response = self.session.get(url, params=args)
        return self.validate_response(response)

    def validate_response(self, response):
        """
        Check if request response is ok
        """
        try:
            if response.status_code == ERROR_STATUS and response.content.startswith(
                "<"
            ):
                raise ShodanException("Invalid API key")

            if response.status_code == ERROR_STATUS and "upgrade" in response.content:
                raise ShodanException(
                    "Error: Please upgrade your API plan to use filters or paging."
                )

            elif response.status_code == RATE_LIMIT_RESPONSE_STATUS:
                # All API methods are rate-limited to 1 request/ second.
                # Any request that exceeds the limit will receive an HTTP 429 "Too many requests" response.
                raise ShodanException("Rate limit error.")

            response.raise_for_status()

        except requests.HTTPError as e:
            try:
                data = response.json()

                if "error" in data:
                    if IP_NOT_FOUND_MSG in data["error"]:
                        # The requested item was not found
                        raise ShodanIPNotFoundException(data["error"])

                    raise ShodanException(data["error"])

            except ValueError:
                # Response content not JSON
                pass

            raise ShodanException(self.session.encode_sensitive_data(str(e)))

        return response.json()
