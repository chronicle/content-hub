# ==============================================================================
# title           :CertlyManager.py
# description     :This Module contain all Certly cloud operations functionality
# author          :zdemoniac@gmail.com
# date            :01-06-18
# python_version  :2.7
# libreries       : json, requests, urllib2
# requirments     :
# product_version :
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
import urllib.parse

# =====================================
#             CONSTANTS               #
# =====================================
API_URL = "{0}/v1/lookup?url={1}&token={2}"


# =====================================
#              CLASSES                #
# =====================================
class CertlyManagerError(Exception):
    """
    General Exception for Certly manager
    """

    pass


class CertlyManager:
    """
    Responsible for all Certly system operations functionality
    """

    def __init__(self, token, api_root):
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.api_token = token
        self.api_root = api_root

    def test_connectivity(self):
        """
        Validates connectivity
        :return: {dict} if success
        """
        return self.get_url_status("http://gumblar.cn")

    def get_url_status(self, url):
        """
        Get url status from certly
        :param url: {string}
        :return: {dict}
        """
        request_url = API_URL.format(
            self.api_root, urllib.parse.quote(url), self.api_token
        )
        r = requests.get(request_url, headers=self._headers)
        try:
            r.raise_for_status()
        except Exception as error:
            raise CertlyManagerError(f"Error: {error} {r.text}")
        if "errors" in r.json():
            raise CertlyManagerError(f"Error: {r.text}")
        return r.json()
