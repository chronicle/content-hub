# ============================================================================#
# title           :TalosManager.py
# description     :This Module contain all Talos operations functionality
# author          :avital@siemplify.co
# date            :15-04-2018
# python_version  :2.7
# libreries       : requests
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #
from __future__ import annotations
import requests
from .TalosParser import TalosParser
from .constants import HEADERS, API_ROOT, ENDPOINTS, REPUTATION_TYPE_MAPPING
from urllib.parse import urljoin
from .UtilsManager import validate_response


class TalosManager:
    def __init__(self, use_ssl=False, siemplify_logger=None):
        """
        The method is used to init an object of Manager class
        :param use_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param siemplify_logger: Siemplify logger
        """
        self.siemplify_logger = siemplify_logger
        self.parser = TalosParser()
        self.session = requests.Session()
        self.session.verify = use_ssl
        self.session.headers = HEADERS

    @staticmethod
    def _get_full_url(url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(API_ROOT, ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity to Talos
        :return: {void}
        """
        url = self._get_full_url("ping")
        response = self.session.get(url)
        validate_response(response, "Unable to connect to Talos")

    def get_ip_reputation(self, ip):
        """
        Get reputation for ip
        :param ip: {str} the ip address
        :return: {}
        """
        url = self._get_full_url("get_ip_reputation")
        params = {"ip": ip}

        response = self.session.get(url, params=params)
        validate_response(response, f"Unable to get reputation for {ip}")
        return self.parser.build_reputation_object(
            response.json(), REPUTATION_TYPE_MAPPING.get("ip")
        )

    def get_domain_reputation(self, domain):
        """
        Get reputation for domain
        :param domain: {str} the domain
        :return: {}
        """
        url = self._get_full_url("get_domain_reputation")
        params = {"domain_name": domain}
        response = self.session.get(url, params=params)
        validate_response(response, f"Unable to get reputation for {domain}")
        return self.parser.build_reputation_object(
            response.json(), REPUTATION_TYPE_MAPPING.get("domain")
        )

    def get_url_reputation(self, domain):
        """
        Get reputation for domain
        :param domain: {str} the domain
        :return: {}
        """
        url = self._get_full_url("get_url_reputation")
        params = {"url": domain}
        response = self.session.get(url, params=params)
        reputation_type = "domain_url"
        validate_response(response, f"Unable to get reputation for {domain}")
        return self.parser.build_reputation_object(
            response.json(), REPUTATION_TYPE_MAPPING.get(reputation_type)
        )

    def get_hostname_reputation(self, hostname):
        """
        Get reputation for hostname
        :param hostname: {str} the hostname
        :return: {}
        """
        url = self._get_full_url("get_hostname_reputation")
        params = {"hostname": hostname}

        response = self.session.get(url, params=params)
        validate_response(response, f"Unable to get reputation for {hostname}")
        return self.parser.build_reputation_object(
            response.json(), REPUTATION_TYPE_MAPPING.get("hostname")
        )

    def get_category_info(self, query_type, identifier):
        """
        Get Category info
        :param query_type: {str} type of the query item
        :param identifier: {str} ip address, hostname or domain
        :return: {}
        """
        url = self._get_full_url("get_category_info")

        params = {
            "hostname": "SDSv3",
            "query_string": f"/score/single/json?{query_type}={identifier}",
        }

        response = self.session.get(url, params=params)
        validate_response(response, f"Unable to get category info for {identifier}")
        return self.parser.build_base_object(response.json())

    def get_blocked_info(self, query_type, identifier):
        """
        Get blocked info
        :param query_type: {str} type of the query - ipaddr or domain
        :param identifier: {str} ip address, hostname or domain
        :return: {}
        """
        url = self._get_full_url("get_blocked_info")
        params = {"query_type": query_type, "query_entry": identifier}

        response = self.session.get(url, params=params)
        validate_response(response, f"Unable to get blocked info for {identifier}")
        return self.parser.build_base_object(response.json())

    def get_whois_report(self, entity):
        """
        Get Whois report
        :param entity: {str} The entity to get report for
        :return: {WhoisReport} WhoisReport object
        """
        url = self._get_full_url("get_whois_information")
        params = {"whois_query": entity}

        response = self.session.get(url, params=params)
        validate_response(response, f"Unable to get whois report for {entity}")
        return self.parser.build_whois_report_object(response.json())
