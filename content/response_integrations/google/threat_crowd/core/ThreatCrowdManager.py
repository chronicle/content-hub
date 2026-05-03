# ==============================================================================
# title           :ThreatCrowdManager.py
# description     :This Module contain all ThreatCrowd API functions.
# author          :zivh@siemplify.co
# date            :05-30-18
# python_version  :2.7
# libraries       :
# requirements    :
# product_version : v2.0
# doc             : https://github.com/AlienVault-OTX/ApiV2
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests

# =====================================
#             CONSTANTS               #
# =====================================
ADDRESS_TYPE = "ip"
EMAIL_TYPE = "email"
DOMAIN_TYPE = "domain"

MALICIOUS_VOTE = -1
NO_DATA_CODE = "0"

DUMMY_IP_FOR_TEST = "8.8.8.8"
API_ROOT = "http://www.threatcrowd.org/searchApi/v2/{0}/report/"
# =====================================
#              CLASSES                #
# =====================================


class ThreatCrowdlManagerError(Exception):
    """
    General Exception for ThreatCrowd manager
    """

    pass


class ThreatCrowdManager:
    def __init__(self, verify_ssl=False):
        self.session = requests.Session()
        self.session.verify = verify_ssl

    def test_connectivity(self):
        report = self.get_report(DUMMY_IP_FOR_TEST, ADDRESS_TYPE)
        if report:
            return True
        return False

    def get_report(self, resource, resource_type):
        """
        Retrieve a report on a given ip address/domain
        :param resource: {string} The ip address, domain name.
        :param resource_type: {string} indicate weather resource is domain, ip.
        :return: {dict}
        """
        params = {resource_type: resource}
        report_url = API_ROOT.format(resource_type)
        response = self.session.get(report_url, params=params)
        return response.json() if self.check_for_error(response) else None

    @staticmethod
    def check_for_error(response):
        """
        Validate response
        :param response: {requests.response} requests information
        :return: {boolean} True if scan report is valid
        """
        try:
            response.raise_for_status()

            # Check if indicator have data
            if response.json()["response_code"] == NO_DATA_CODE:
                return None

        except requests.HTTPError as e:
            raise ThreatCrowdlManagerError(f"Error: {e}. {response.text}")

        return True
