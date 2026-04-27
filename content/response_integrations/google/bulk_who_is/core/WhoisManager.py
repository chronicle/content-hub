# ============================================================================#
# title           :WhoisManager.py
# description     :This Module contain all Whois operations functionality
# author          :zivh@siemplify.co
# date            :10-01-2019
# python_version  :2.7
# libreries       :requests
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================ IMPORTS ====================================== #

from __future__ import annotations
import requests
import datetime
import hashlib
import hmac

from .WhoIsParser import WhoIsParser

# =============================== CONSTS ==================================== #

API_URL = "http://api.bulk-whois-api.com/api/query"

QUERY = "query={0}"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}

# ============================== CLASSES ==================================== #


class WhoisiException(Exception):
    """
    General Exception for Whois ThreatStream manager
    """

    pass


class WhoisManager:

    def __init__(self, api_key, secret_key, verify_ssl=False):
        self.secret_key = secret_key
        self.api_key = api_key
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers = HEADERS
        self.session.headers.update({"Key": self.api_key})
        self.whoIsParser = WhoIsParser()

    def test_connectivity(self):
        """
        Test connectivity by scanning 8.8.8.8
        """
        return self.scan("8.8.8.8")

    @staticmethod
    def validate_response(response):
        """
        Check if request response is ok
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise WhoisiException(e)
        return response.json()

    def scan(self, entity_for_search):
        """
        Scan and get details from whois
        :param entity_for_search: {string} domain name or ip address for search
        :return: {list} The incidents
        """
        # Get Time.
        str_time = datetime.datetime.utcnow().strftime(DATETIME_FORMAT)
        query_payload = QUERY.format(entity_for_search)
        data_to_sign = f"{self.api_key}{str_time}{query_payload}"
        signature = (
            hmac.new(
                bytearray(self.secret_key, "utf8"),
                bytearray(data_to_sign, "utf8"),
                digestmod=hashlib.sha512,
            )
            .hexdigest()
            .lower()
        )

        # Update headers
        self.session.headers.update({"Time": str_time})
        self.session.headers.update({"Sign": signature})

        response = self.session.post(API_URL, data=query_payload)
        response = self.validate_response(response)
        return self.whoIsParser.build_siemplify_detail_obj(response)
