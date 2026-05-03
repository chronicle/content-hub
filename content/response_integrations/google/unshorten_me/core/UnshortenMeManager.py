# ============================================================================#
# title           :UnshortenMeManager.py
# description     :This Module contain all UnshortenMe operations functionality
# author          :avital@siemplify.co
# creation date   :11-04-2018
# update date     :02-05-2023
# python_version  :3
# libreries       :requests
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #
from __future__ import annotations
import requests
from urllib.parse import unquote

# ============================== CONSTS ===================================== #

UNSHORTENME_URL = "https://unshorten.me/json/{short_url}"
UNSHORTENME_TEST_URL = "https://unshorten.me/json/goo.gl/IGL1lE"
MAX_REQUETSTS_PER_HOUR = 10

# ============================= CLASSES ===================================== #


class UnshortenMeManagerError(Exception):
    """
    General Exception for UnshortenMe manager
    """

    pass


class UnshortenMeLimitManagerError(Exception):
    """
    Limit Reached Exception for UnshortenMe manager
    """

    pass


class UnshortenMeManager:
    """
    UnshortenMe Manager
    """

    def __init__(self, use_ssl=False):
        self.session = requests.Session()
        self.session.verify = use_ssl

    def test_connectivity(self):
        """
        Test connectivity to UnshortenMe
        :return: {bool} True if successful, exception otherwise.
        """
        response = self.session.get(UNSHORTENME_TEST_URL)
        self.validate_response(response, "Unable to connect to unshorten.me")

        return True

    def unshorten_url(self, url):
        """
        Unshorten a url
        :param url: {str} The url to unshorten
        :return: {str} The matching long url
        """
        response = self.session.get(UNSHORTENME_URL.format(short_url=url))
        self.validate_response(response, f"Unable to unshorten {url}")

        return unquote(response.json()["resolved_url"])

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            raise UnshortenMeManagerError(
                f"{error_msg}: {error} {error.response.content}"
            )

        if response.json().get("error"):
            raise UnshortenMeManagerError(response.json()["error"])

        if response.json().get("usage_count", 0) > MAX_REQUETSTS_PER_HOUR:
            raise UnshortenMeLimitManagerError("Reached API requests limit.")

        if not response.json()["success"]:
            raise UnshortenMeManagerError(
                "Unknown error occurred in unshorten.me. "
                "Request failed but no error message received."
            )
