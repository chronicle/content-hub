# ============================================================================#
# title           :ForeScoutCounterACTManager.py
# description     :This Module contain all ForeScout CounterACT operations functionality
# author          :gabriel.munits@siemplify.co
# date            :23-06-2021
# python_version  :3.7
# product_version :1.0
# ============================================================================#
from __future__ import annotations
import base64
from urllib.parse import urljoin

import requests

from .ForeScoutCounterACTExceptions import ForeScoutCounterACTException
from .ForeScoutCounterACTParser import ForeScoutCounterACTParser
from .constants import INTEGRATION_DISPLAY_NAME


# ============================= CONSTS ===================================== #


ENDPOINTS = {
    "get-jwt-token": "/api/login",
    "get-endpoint-information-by-mac": "/api/hosts/mac/{mac_address}",
    "get-endpoint-information-by-ip": "/api/hosts/ip/{ip_address}",
}

HEADERS = {
    "Accept": "application/hal+json",
    "Content-Type": "application/x-www-form-urlencoded",
}

# Certificate file temp path
CA_CERTIFICATE_FILE_PATH = "cert.crt"


# ============================= CLASSES ===================================== #


class ForeScoutCounterACTManager:
    def __init__(
        self,
        api_root,
        username,
        password,
        verify_ssl,
        ca_certificate_file=None,
        siemplify_logger=None,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} Api Root to use for connection
        :param username: {str} Username to use for connection
        :param password: {str} Password to use for connection
        :para, ca_certificate_file: {str} Base 64 encoded ssl certificate file
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root
        self.username = username
        self.password = password
        self.siemplify_logger = siemplify_logger
        self.parser = ForeScoutCounterACTParser()
        self.session = requests.session()
        self.session.verify = self.__get_verification(
            verify_ssl=verify_ssl, certificate=ca_certificate_file
        )
        self.session.headers = HEADERS
        self.session.headers.update({"Authorization": f"{self.get_token()}"})

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def __get_verification(self, verify_ssl, certificate=None):
        """
        Validate the verification in case that VerifySSL is enabled.
        :param verify_ssl: {bool} If true, verify the SSL certificate for the connection to the LogPoint server is valid.
        :param certificate: {str} Base 64 encoded CA certificate file. Located in *.crt file and need to be encoded to base64
        :return CA_CERTIFICATE_FILE_PATH: {str} The path to the certification file that was created.
        """
        if certificate and verify_ssl:
            try:
                file_content = base64.b64decode(certificate)
                with open(CA_CERTIFICATE_FILE_PATH, "w+") as f:
                    f.write(file_content.decode())
            except Exception as e:
                raise ForeScoutCounterACTException(
                    f"Unable to decode the certificate file. Reason: {e}"
                )
            return CA_CERTIFICATE_FILE_PATH

        return verify_ssl

    def get_token(self) -> str:
        """
        Get JWT token
        :return: {str} The JWT token
        """
        request_url = self._get_full_url("get-jwt-token")
        payload = {"username": self.username, "password": self.password}
        response = self.session.post(request_url, data=payload)
        self.validate_response(
            response,
            error_msg=f"Failed to test connectivity with {INTEGRATION_DISPLAY_NAME}!",
        )
        return response.text

    @classmethod
    def validate_response(
        cls, response: requests.Response, error_msg: str = "An error occurred"
    ):
        """
        Validate response
        :param response: {requests.Response} The response to validate
        :param error_msg: {str} Default message to display on error
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            try:
                response_json = response.json()
                raise ForeScoutCounterACTException(
                    f"{error_msg}: {error} {response_json.get('message', response.text)}"
                )
            except ForeScoutCounterACTException:
                raise
            except:
                raise ForeScoutCounterACTException(
                    f"{error_msg}: {error} {error.response.content}"
                )

    def get_endpoint_info_by_mac(self, mac_address):
        """
        Get Endpoint information
        :param mac_address: {str} MAC address of the endpoint
        :return: {EndpointInfo} Endpoint information data model
        """
        request_url = self._get_full_url(
            "get-endpoint-information-by-mac", mac_address=mac_address
        )
        response = self.session.get(request_url)
        self.validate_response(
            response, error_msg=f"Failed to get endpoint information for: {mac_address}"
        )
        return self.parser.build_endpoint_info_obj(response.json())

    def get_endpoint_info_by_ip_address(self, ip_address):
        """
        Get Endpoint information
        :param ip_address: {str} IP address of the endpoint
        :return: {EndpointInfo} Endpoint information data model
        """
        request_url = self._get_full_url(
            "get-endpoint-information-by-ip", ip_address=ip_address
        )
        response = self.session.get(request_url)
        self.validate_response(
            response, error_msg=f"Failed to get endpoint information for: {ip_address}"
        )
        return self.parser.build_endpoint_info_obj(response.json())
