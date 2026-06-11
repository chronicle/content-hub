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

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
import copy
import urllib.parse
from netaddr import IPNetwork, IPAddress

# =====================================
#             CONSTANTS               #
# =====================================
HEADERS = {"Authorization": "api_key"}

# URLs
MX_LOOKUP_URL = "api/v1/lookup/mx/{0}"  # {0} - Domain Name.
BLACKLIST_LOOKUP_URL = "api/v1/lookup/blacklist/{0}"  # {0} - Domain Name.
DNS_LOOKUP_URL = "api/v1/lookup/dns/{0}"  # {0} - Domain Name.
HTTPS_LOOKUP_URL = "api/v1/lookup/https/{0}"  # {0} - Domain Name.
PING_LOOKUP_URL = "api/v1/lookup/ping/{0}"  # {0} - Domain Name.
SPF_LOOKUP_URL = "api/v1/lookup/spf/{0}"  # {0} - Domain Name.
A_LOOKUP_URL = "api/v1/lookup/a/{0}"  # {0} - Domain Name.
PTR_LOOKUP_URL = "api/v1/lookup/ptr/{0}"  # {0} - IP Address.
TCP_PORT_LOOKUP_URL = "api/v1/lookup/tcp/{0}?port={1}"  # {0} - Domain Name, {1} - Port

INVESTIGATOR_RELATED_DOMAINS_URL = "api/v1/MxToolBot/{0}"  # {0} - Domain Name.
GET_ENDPOINT_DATA_URL = (
    "api/v1/NetEndpoint?query={0}"  # {0} -  Endpoint Identifier(IP address/Domain)
)

# F12 APIs URLs.
LOCATION_LOOKUP_URL = (
    "https://api.mxtoolbox.com/api/v1/lookup/loc/{0}"  # {0} - Domain Name.
)
WHAT_IS_MY_IP_URL = "https://api.mxtoolbox.com/api/v1/utils/whatsmyip"

# Consts.
TCP_CONNECTION_NAME = "TCP Connect"
INCLUDE_TYPE = "include"
IP4_TYPE = "ip4"


# =====================================
#              CLASSES                #
# =====================================
class MXToolBoxManagerError(Exception):
    pass


class MXToolBoxManager:
    def __init__(self, api_root, api_key, verify_ssl=False):
        self.api_root = self.validate_api_root(api_root)
        # Set Session.
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers = copy.deepcopy(HEADERS)
        self.session.headers["Authorization"] = api_key

    @staticmethod
    def validate_api_root(api_root):
        """
        Validate API root string contains '/' at the end because 'urlparse' lib is used.
        :param api_root: api root url {string}
        :return: valid api root {string}
        """
        if api_root[-1] == "/":
            return api_root
        return api_root + "/"

    @staticmethod
    def validate_response(http_response):
        """
        Validated an HTTP response.
        :param http_response: HTTP response object.
        :return: {void}
        """
        try:
            http_response.raise_for_status()

        except requests.HTTPError as err:
            raise MXToolBoxManagerError(
                f"Status Code: {http_response.status_code}, Content: {http_response.content}, Error: {err}"
            )

    @staticmethod
    def is_address_in_network_range(ip_address, network_range):
        """
        Check if the ip address is included in a network range.
        :param ip_address: ip to check {string}
        :param network_range: network range with subnet mask {string}
        :return:
        """
        return IPAddress(ip_address) in IPNetwork(network_range)

    def ping(self):
        """
        Test integration connectivity.
        :return: is succeed {bool}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, MX_LOOKUP_URL.format("example.com")
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return True

    def domain_mx_lookup(self, domain_name):
        """
        Provide mx lookup over a domain name.
        :param domain_name: domain name to look for {string}
        :return: lookup results {list}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, MX_LOOKUP_URL.format(domain_name)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json().get("Information")

    def domain_blacklist_lookup(self, domain_name):
        """
        Provide blacklist lookup over a domain name.
        :param domain_name: domain name to look for {string}
        :return: lookup results {dict}
        """
        result_dict = {}
        request_url = urllib.parse.urljoin(
            self.api_root, BLACKLIST_LOOKUP_URL.format(domain_name)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        # Get all blacklists where the entity appears.
        if isinstance(response.json().get("Failed"), list):
            result_dict["Failed"] = response.json().get("Failed")
        # Get all blacklists where the entity does not appear.
        if isinstance(response.json().get("Passed"), list):
            result_dict["Passed"] = response.json().get("Passed")

        return result_dict

    def domain_dns_lookup(self, domain_name):
        """
        Provide dns lookup over a domain name.
        :param domain_name: domain name to look for {string}
        :return: lookup results {list}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, DNS_LOOKUP_URL.format(domain_name)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json().get("Information", [])

    def domain_https_lookup(self, domain_name):
        """
        Provide https lookup over a domain name.
        :param domain_name: domain name to look for {string}
        :return: lookup results {list}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, HTTPS_LOOKUP_URL.format(domain_name)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json().get("Information", [])

    def entity_ping_lookup(self, entity_identifier):
        """
        Provide ping lookup over a domain name.
        :param entity_identifier: domain name or ip address to ping {string}
        :return: lookup results {list}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, PING_LOOKUP_URL.format(entity_identifier)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json().get("Information", [])

    def what_is_my_ip(self):
        """
        Get my ip address.
        :return: ip address {string}
        """
        # Different url because uses the UI API.
        request_url = WHAT_IS_MY_IP_URL
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def investigator_get_related_domains(self, domain_name):
        """
        Get related domains for domain.
        :param domain_name: domain name {string}
        :return: list of dicts {list}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, INVESTIGATOR_RELATED_DOMAINS_URL.format(domain_name)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def investigator_get_related_ips(self, domain_name):
        """
        Get related IP addresses for domain.
        :param domain_name: domain name {string}
        :return: list of ip address objects {list}
        """
        dns_lookup_response = self.domain_dns_lookup(domain_name)
        if dns_lookup_response:
            ip_addresses = [
                address_obj.get("IP Address") for address_obj in dns_lookup_response
            ]
            return list(map(self.get_endpoint_data, ip_addresses))

        return []

    def investigator_spf_lookup(self, domain_name):
        """
        Provide spf lookup over a domain name.
        :param domain_name: domain name to look for {string}
        :return: lookup results {list}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, SPF_LOOKUP_URL.format(domain_name)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json().get("Information", [])

    def get_port_status(self, domain_name, port):
        """
        Provide tcp lookup over a port.
        :param domain_name: domain name to look for {string}
        :param port: port number {integer}
        :return: {boolean} if the port is open or not
        """
        request_url = urllib.parse.urljoin(
            self.api_root, TCP_PORT_LOOKUP_URL.format(domain_name, port)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        for connection in response.json().get("Passed", []):
            # If the TCP Connection is under the 'Passed' key, it means the port is open.
            if connection.get("Name") == TCP_CONNECTION_NAME:
                return True

        return False

    def get_endpoint_data(self, endpoint_identifier):
        """
        Get endpoint data by identifier(IP Address/ Domain Name).
        :param endpoint_identifier: identifier(ip address/ domain name) {string}
        :return: endpoint data {dict}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, GET_ENDPOINT_DATA_URL.format(endpoint_identifier)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json()

    def domain_location_lookup(self, domain_name):
        """
        Get domain name location lookup.
        :param domain_name: domain name {string}
        :return: location lookup data {list}
        """
        request_url = LOCATION_LOOKUP_URL.format(domain_name)
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json().get("Information", [])

    def domain_a_lookup(self, domain_name):
        """
        Get domain a record lookup.
        :param domain_name: domain name {string}
        :return: {list} of a record lookup data {dict}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, A_LOOKUP_URL.format(domain_name)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json().get("Information", [])

    def address_ptr_lookup(self, ip_address):
        """
        Get ip address ptr record lookup.
        :param ip_address: ip address {string}
        :return: ptr record lookup data {dict}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, PTR_LOOKUP_URL.format(ip_address)
        )
        response = self.session.get(request_url)
        self.validate_response(response)
        return response.json().get("Information", [])

    def get_spf_ips_list_for_domain(self, domain_name):
        """
        Get the list of ips that are permitted to send mail from the domain name.
        :param domain_name: domain name to check for {string}
        :return: list of ips to check {list}
        """
        ranges_list = []
        result = self.investigator_spf_lookup(domain_name)
        for record in result:
            if record.get("Type") == INCLUDE_TYPE:
                ranges_list.extend(
                    self.get_spf_ips_list_for_domain(record.get("Value"))
                )
            elif record.get("Type") == IP4_TYPE:
                ranges_list.append(record.get("Value"))
        return ranges_list


if __name__ == "__main__":
    dml = MXToolBoxManager(
        "https://mxtoolbox.com/", "a7b6e7a4-e364-4d91-986f-8b11c8af5f36"
    )
    mx_lookup = dml.domain_mx_lookup("siemplify.co")
    # b = dml.domain_a_lookup('siemplify.co')
    # dml.domain_blacklist_lookup('chinatlz.com')
    # blacklist_lookup = dml.domain_blacklist_lookup('_DNSBLNEG_.tes')
    # dns_lookup = dml.domain_dns_lookup('8.8.8.8')
    # https_lookup = dml.domain_https_lookup('example.com')
    # ping_lookup = dml.domain_ping_lookup('siemplify.co')
    # spf = dml.investigator_spf_lookup('example.com')
    # my_ip = dml.what_is_my_ip()
    # investigator_related_domains = dml.investigator_get_related_domains('example.com')
    # investigator_related_ips = dml.investigator_get_related_ips('example.com')
    # port_status = dml.get_port_status('example.com', 80)
    # res = dml.domain_location_lookup('example.com')
    # a_record = dml.domain_a_lookup('example.com')
    # ptr_record = dml.address_ptr_lookup('8.8.8.8')
    ips = dml.get_spf_ips_list_for_domain("siemplify.co")

    pass
