# ============================================================================#
# title           :ThreatExchangeManager.py
# description     :This Module contain all Threat Exchange operations functionality
# author          :avital@siemplify.co
# date            :25-06-2018
# python_version  :2.7
# libreries       : requests
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #
from __future__ import annotations
import requests

# ============================== CONSTS ===================================== #
LIMIT = 1000
TEST_HASH = "d2b4a84e2b69856ba8e234f55b1fbc4b"
# ============================= CLASSES ===================================== #


class ThreatExchangeManagerError(Exception):
    """
    General Exception for Threat Exchange manager
    """

    pass


class ThreatExchangeManager:
    """
    Threat Exchange Manager
    """

    def __init__(
            self,
            api_root,
            app_id,
            app_secret,
            api_version="v3.0",
            use_ssl=False
    ):
        self.session = requests.Session()
        self.session.verify = use_ssl
        self.api_root = f"{api_root}/{api_version}"
        self.access_token = f"{app_id}|{app_secret}"

    def test_connectivity(self):
        """
        Test connectivity to Threat Exchange
        :return: {bool} True is successful, exception otherwise.
        """
        self.get_file_reputation(TEST_HASH)
        return True

    def get_file_reputation(self, filehash, since=None, until=None):
        """
        Get file reputation of the given hash
        :param filehash: {str} The hash
        :param since: {int} Returns reputation from after a timestamp, format: 1391813489
        :param until: {int} Returns reputation from before a timestamp, format: 1391813489
        :return: {list} List of reputations
        """
        url = f"{self.api_root}/malware_analyses"
        query_params = {
            "access_token": self.access_token,
            "text": filehash,
            "since": since,
            "until": until,
            "strict_text": True,
            "limit": LIMIT,
        }

        # Remove None values
        query_params = {k: v for k, v in list(query_params.items()) if v is not None}

        response = self.session.get(url, params=query_params)
        self.validate_response(
            response,
            f"Unable to get reputation of {filehash}"
        )
        return response.json()["data"]

    def get_ip_reputation(self, ip, since=None, until=None):
        """
        Get reputation of the given ip
        :param ip: {str} The ip
        :param since: {int} Returns reputation from after a timestamp, format: 1391813489
        :param until: {int} Returns reputation from before a timestamp, format: 1391813489
        :return: {list} List of reputations
        """
        return self.get_reputation(
            "threat_descriptors",
            ip,
            "IP_ADDRESS",
            since,
            until
        )

    def get_url_reputation(self, uri, since=None, until=None):
        """
        Get reputation of the given url
        :param url: {str} The url
        :param since: {int} Returns reputation from after a timestamp, format: 1391813489
        :param until: {int} Returns reputation from before a timestamp, format: 1391813489
        :return: {list} List of reputations
        """
        return self.get_reputation(
            "threat_descriptors",
            uri,
            "URI",
            since,
            until
        )

    def get_domain_reputation(self, domain, since=None, until=None):
        """
        Get reputation of the given domain
        :param domain: {str} The domain
        :param since: {int} Returns reputation from after a timestamp, format: 1391813489
        :param until: {int} Returns reputation from before a timestamp, format: 1391813489
        :return: {list} List of reputations
        """
        return self.get_reputation(
            "threat_descriptors",
            domain,
            "DOMAIN",
            since,
            until
        )

    def get_reputation(
            self,
            endpoint,
            entity,
            entity_type,
            since=None,
            until=None
    ):
        """
        Get reputation of a given entity
        :param endpoint: {str} The type of the entity. As explain in:
            https://developers.facebook.com/docs/threat-exchange/reference/apis/indicator-type/v3.0
        :param entity: {str} The entity
        :param since: {int} Returns reputation from after a timestamp, format: 1391813489
        :param until: {int} Returns reputation from before a timestamp, format: 1391813489
        :return: {list} List of reputations
        """
        url = f"{self.api_root}/{endpoint}"
        query_params = {
            "access_token": self.access_token,
            "text": entity,
            "type": entity_type,
            "since": since,
            "until": until,
            "strict_text": True,
            "limit": LIMIT,
        }

        # Remove None values
        query_params = {k: v for k, v in list(query_params.items()) if v is not None}

        response = self.session.get(url, params=query_params)
        self.validate_response(
            response,
            f"Unable to get reputation of {entity}"
        )

        return response.json()["data"]

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate a response
        :param response: {requests.Response} The response
        :param error_msg: {str} The error message to display on failure
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                error_message = response.json()["error"]["message"]
            except:
                # No JSON / error message
                raise ThreatExchangeManagerError(
                    f"{error_msg}: {error} {error.response.content}"
                )
            raise ThreatExchangeManagerError(f"{error_msg}: {error_message}")
