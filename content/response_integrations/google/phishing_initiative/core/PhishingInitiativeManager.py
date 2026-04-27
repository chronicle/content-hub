# ==============================================================================
# title           :PhishingInitiative.py
# description     :This Module contain all Phishing-Initiative functionality
# author          :zivh@siemplify.co
# date            :3-11-18
# python_version  :2.7
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
from urllib.parse import urlencode


# =====================================
#             CONSTANTS               #
# =====================================
API_ROOT = "https://phishing-initiative.eu"

API_KEY = "bda5fa1cc9b5d9d9bb8e12d7f2ce2dbc19d4949c287973c4fed0aaaafd0afff5"

NOT_SUBMIT_STATUS = "not submitted"
PHISHING_STATUS = "phishing"

# =====================================
#              CLASSES                #
# =====================================


class PhishingInitiativeManagerError(Exception):
    """
    General Exception for Phishing Initiative manager
    """

    pass


class PhishingInitiativeManager:
    """
    Responsible for all Phishing-Initiative operations
    """

    def __init__(self, api_root, auth_token, verify_ssl=True):
        self.api_root = api_root
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update(
            {"Accept": "application/json", "Authorization": f"Token {auth_token}"}
        )

    def get_url_info(self, url):
        """
        Retrieves all information about the specified url
        :param url: {String}
        :return: {json} url details
        """
        query = [("url", url)]
        path = f"{self.api_root}/api/v1/urls/lookup/?{urlencode(query)}"
        response = self.session.get(path)
        try:
            response.raise_for_status()
        except Exception:
            raise PhishingInitiativeManagerError(f"Error: {response.text}")
        return response.json()
