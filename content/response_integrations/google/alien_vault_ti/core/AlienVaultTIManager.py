# ==============================================================================
# title           :AlienVaultTIManager.py
# description     :This Module contain all AlienVault TI cloud operations functionality
# author          :zdemoniac@gmail.com
# date            :1-18-18
# python_version  :2.7
# libraries       : json, requests, urllib2
# requirements    :
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
API_URL = "https://otx.alienvault.com:443/api/v1/"

SKIP_FIELDS = ["general"]
IP_IS_PRIVATE_ERROR_MSG = "IP is private"


# =====================================
#              CLASSES                #
# =====================================
class AlienVaultTIManagerError(Exception):
    """
    General Exception for DShield manager
    """

    pass


class AlienVaultTIManager:
    """
    Responsible for all AlienVault TI system operations functionality
    API docs: https://otx.alienvault.com/api
        Supports only general section
    """

    def __init__(self, api_key, logger=None):
        self._api_url = API_URL
        self._headers = {"X-OTX-API-KEY": api_key, "Content-Type": "application/json"}
        self.logger = logger

    def test_connectivity(self):
        """
        Validates connectivity
        :return: {boolean} True/False
        """
        try:
            # Dummy requests
            self._get("user/me")
            return True
        except AlienVaultTIManagerError:
            return False

    def enrich_host(self, host):
        """
        Get host info from AlienVault
        :param host: {string} a valid host
        :return: {dict}
        """
        results = {}
        host_lower = host.lower()
        sections_results = self._get("indicators/hostname/" + host_lower)
        if sections_results:
            for section in sections_results["sections"]:
                results[section] = self._get(
                    f"indicators/hostname/{host_lower}/{section}"
                )
            return results

    def enrich_ip(self, ip):
        """
        Get ip info from AlienVault
        :param ip: {string} a valid IP address
        :return: {dict}
        """
        results = {}
        sections_results = self._get("indicators/IPv4/" + ip)
        if sections_results:
            for section in sections_results["sections"]:
                results[section] = self._get(
                    f"indicators/IPv4/{ip}/{section}", ignore_forbidden=True
                )
            return results

    def enrich_url(self, url):
        """
        Get ip info from AlienVault
        :param url: {string}
        :return: {dict}
        """
        results = {}
        url_lower = url.lower()
        sections_results = self._get(
            f"indicators/url/{urllib.parse.quote(url_lower)}/general"
        )
        if sections_results:
            for section in sections_results["sections"]:
                results[section] = self._get(
                    f"indicators/url/{urllib.parse.quote(url_lower)}/{section}"
                )
            return results

    def enrich_hash(self, file_hash):
        """
        Get ip info from AlienVault
        :param file_hash: {string} file hash
        :return: {dict}
        """
        results = {}
        sections_results = self._get("indicators/file/" + file_hash)
        if sections_results:
            for section in sections_results["sections"]:
                results[section] = self._get(f"indicators/file/{file_hash}/{section}")
            return results

    def _get(self, func, ignore_forbidden=False):
        """
        Get and return data from the API.
        :return: {dict}
        """
        r = requests.get("".join([self._api_url, func]), headers=self._headers)
        # Return none if no results where found
        if r.status_code == 404:
            return None
        # This situation is equivalent to 404 no results where found
        if r.status_code == 400 and IP_IS_PRIVATE_ERROR_MSG in r.text:
            return None
        # Return none if action is forbidden for IPv4
        if ignore_forbidden and r.status_code == 403:
            self.logger.error(
                f"Unable to process section \"{func.rsplit('/', 1)[-1]}\". Reason: {r.json().get('detail')}"
            )
            return None
        try:
            r.raise_for_status()
        except Exception as error:
            raise AlienVaultTIManagerError(f"Error: in {func}  {error} {r.text}")
        try:
            return r.json()
        except Exception:
            return None
