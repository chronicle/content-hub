# ============================================================================#
# title           :SSLLabsManager.py
# description     :This Module contain all SSL Labs operations functionality
# author          :avital@siemplify.co
# date            :07-03-2018
# python_version  :2.7
# libreries       :requests
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #

from __future__ import annotations
import requests
import time


# ============================== CONSTS ===================================== #

API_ROOT = r"https://api.ssllabs.com/api/v3"
COMPLETED_STATES = ["READY", "ERROR"]
FAILED_STATE = "ERROR"
TIMEOUT = 10

# ============================= CLASSES ===================================== #


class SSLLabsManagerError(Exception):
    """
    General Exception for SSLLabs manager
    """

    pass


class SSLLabsManager:

    def __init__(self, verify_ssl):
        self.verify = verify_ssl

    def test_connectivity(self):
        """
        Test connectivity to SSL Labs
        :return: {bool} True if connected, exception otherwise
        """
        url = f"{API_ROOT}/info"

        response = requests.get(url=url, verify=self.verify)

        response.raise_for_status()
        return True

    def analyze_url(self, url):
        """
        Analyze URL in ssl labs
        :param url: {str} The url to analyze
        :return: {JSON} Analysis report (dict)
        """
        url_req = f"{API_ROOT}/analyze"

        # Start new analysis
        response = requests.get(
            url=url_req, params={"host": url, "startNew": "on"}, verify=self.verify
        )

        response.raise_for_status()

        response = requests.get(url=url_req, params={"host": url}, verify=self.verify)

        # Wait until analysis is completed - about 60 seconds.
        while response.json()["status"] not in COMPLETED_STATES:
            time.sleep(TIMEOUT)
            response = requests.get(
                url=url_req, params={"host": url}, verify=self.verify
            )

        # Fetch full report
        response = requests.get(
            url=url_req, params={"host": url, "all": "done"}, verify=self.verify
        )

        # If analysis failed - return empty results
        if response.json()["status"] == FAILED_STATE:
            return []

        return response.json()
