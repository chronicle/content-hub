# ==============================================================================
# title           :DShieldManager.py
# description     :This Module contain all DShield cloud operations functionality
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
from datetime import datetime
import requests
import urllib.request, urllib.error


# =====================================
#             CONSTANTS               #
# =====================================
API_URL = "http://isc.sans.edu/api/"


# =====================================
#              CLASSES                #
# =====================================
class DShieldManagerError(Exception):
    """
    General Exception for DShield manager
    """

    pass


class DShieldManager:
    """
    Responsible for all DShield system operations functionality
    API docs: https://secure.dshield.org/api/
    """

    def __init__(self, api_url):
        self._api_url = api_url

    def test_connectivity(self):
        """
        Validates connectivity
        :return: {boolean} True/False
        """
        try:
            urllib.request.urlopen(self._api_url)
            return True
        except ValueError:
            return False  # URL not well formatted
        except urllib.error.URLError:
            return False  # URL don't seem to be alive

    def get_ip_info(self, ip):
        """
        Get ip info from DShield
        :param ip: {string} a valid IP address
        :return: {dict} [Counts, Attacks]
        Count: (also reports or records) total number of packets blocked from this IP.
        Attacks: (also targets) number of unique destination IP addresses for these packets.
        """
        response = self._get("ip/" + ip)
        if "bad IP address" in str(response):
            raise DShieldManagerError("Bad IP address " + ip)

        return response["ip"]

    def backscatter(self, date=None, rows=None):
        """Returns possible backscatter data.
        This report only includes "syn ack" data and is summarized by source port.
        :param date: optional string (in Y-M-D format) or datetime.date() object
        :param rows: optional number of rows returned (default 1000)
        :returns: list -- backscatter data.
        """
        uri = "backscatter"
        if date:
            try:
                uri = "/".join([uri, datetime.strftime(date, "%Y-%m-%d")])
            except AttributeError:
                uri = "/".join([uri, date])
            if rows:
                uri = "/".join([uri, str(rows)])
        return self._get(uri)

    def infocon(self):
        """Returns the current infocon level (green, yellow, orange, red)."""
        return self._get("infocon")

    def _get(self, func):
        """Get and return data from the API.
        :return: {dict}
        """
        r = requests.get("".join([self._api_url, func, "?json"]))
        try:
            r.raise_for_status()
        except Exception as error:
            raise DShieldManagerError(f"Error: in {func}  {error} {r.text}")
        return r.json()


if __name__ == "__main__":
    # ds = DShieldManager(API_URL)
    # a = ds.get_ip_info("8.8.8.8")
    print("")
