# ============================================================================#
# title           :IPVoidManager.py
# description     :This Module contain all IPVoid operations functionality
# author          :avital@siemplify.co
# date            :11-04-2018
# python_version  :2.7
# libreries       : requests
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #

from __future__ import annotations
import requests

# ============================== CONSTS ===================================== #

IPVOID_BLACKLIST_URL = "http://www.ipvoid.com/ip-blacklist-check/"
IPVOID_URL = "http://www.ipvoid.com/"
IPVOID_WHOIS_URL = "http://www.ipvoid.com/whois/"
COMPLETED_STATUSES = ["completed", "failure", "reported"]
FAILURE_STATUS = "failure"
HTML_TABLE = "table-striped"

ENRICH_DATA_KEYS = ["Blacklist Status", "Reverse DNS", "Continent", "Country Code"]

# ============================= CLASSES ===================================== #


class IPVoidManagerError(Exception):
    """
    General Exception for IPVoid manager
    """

    pass


class IPVoidManager:
    """
    IPVoid Manager
    """

    def __init__(self, api_root, api_key, use_ssl=False):
        self.api_root = api_root
        self.api_key = api_key
        self.session = requests.Session()
        self.session.verify = use_ssl

    def test_connectivity(self):
        """
        Test connectivity to IPVoid
        :return: {bool} True if successful, exception otherwise.
        """
        response = self.session.get(
            url=f"{self.api_root}/iprep/v1/pay-as-you-go/?stats",
            params={"key": self.api_key},
        )
        self.validate_response(response, "Unable to connect to IPVoid")
        return True

    def get_ip_reputation(self, ip):
        """
        Get IP Reputation
        :param ip: {str} The ip address
        :return: {dict} The reputation of the ip
        """
        response = self.session.post(
            url=f"{self.api_root}/iprep/v1/pay-as-you-go/",
            params={"ip": ip, "key": self.api_key},
        )
        self.validate_response(response, f"Unable to get reputation for {ip}")

        return response.json().get("data", {}).get("report")

    def get_whois_html_report(self, entity):
        """
        Get Whois Online Lookup Report of an ip address or a domain name
        :param entity: {str} The ip address or the domain name
        :return: {str} The html content of the report
        """
        response = self.session.post(IPVOID_WHOIS_URL, data={"whois": entity})
        self.validate_response(response, f"Unable to get WhoIs report for {entity}")

        # Return HTML webpage
        return response.content

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
                raise IPVoidManagerError(f"{error_msg}: {error} - {response.content}")

            raise IPVoidManagerError(
                f"{error_msg}: {error} - {response.json().get('error', 'No error message.')}"
            )
