# -*- coding: utf-8 -*-
# ==============================================================================
# title           :Area1Manager.py
# description     :This Module contain all Area1 operations functionality
# author          :victor@siemplify.co
# date            :12-2-19
# python_version  :2.7
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
import urllib.parse
import arrow

# =====================================
#             CONSTANTS               #
# =====================================
INDICATORS_URL = "indicators"
SEARCH_URL = "search"


# =====================================
#              CLASSES                #
# =====================================
class Area1ManagerError(Exception):
    pass


class Area1Manager:
    def __init__(self, api_root, username, password, verify_ssl=False):
        self.api_root = api_root
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.auth = (username, password)

    @staticmethod
    def validate_response(response):
        """
        Validate HTTP response.
        :param response: {HTTP response}
        :return: raise exception if the response is not valid {void}
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as err:
            raise Area1ManagerError(
                f"Status code:{response.status_code}, Content:{response.content}, Error: {err}"
            )
        except Exception as err:
            raise Exception(f"Error occurred - Error: {err}")

    def get_recent_indicators(self, since=0, end=arrow.utcnow().timestamp):
        """
        Get recent indicators between specific time.
        :param since: {integer} since unixtime.
        :param end: {integer} till unixtime.
        :return: {list} list of indicator objects.
        """
        request_url = urllib.parse.urljoin(self.api_root, INDICATORS_URL)
        params = {"since": since, "end": end}
        response = self.session.get(request_url, params=params)
        self.validate_response(response)
        return response.json().get("data", [])

    def search_indicator(self, query):
        """
        Get indicators for query.
        :param query: {string} The search query will be a lower case entity indicator.
        :return: {dict} indicator object.
        """
        request_url = urllib.parse.urljoin(self.api_root, SEARCH_URL)
        search_params = {"query": query}
        response = self.session.get(request_url, params=search_params)
        self.validate_response(response)
        return response.json()


#
