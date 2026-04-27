from __future__ import annotations
import requests
from urllib.parse import urljoin
from .exceptions import CheckPointThreatReputationException
from .CheckPointTRTransformationLayer import CheckPointTRTransformationLayer

ENDPOINTS = {
    "ping": "/rep-auth/service/v1.0/request",
    "get-token": "/rep-auth/service/v1.0/request",  # get session token
    "get-file-hash-reputation": "/file-rep/service/v2.0/query",
    "get-ip-reputation": "/ip-rep/service/v2.0/query",
    "get-host-reputation": "/url-rep/service/v2.0/query",
}


class CheckPointThreatReputationManager:

    def __init__(self, api_root, api_key, verify_ssl=False, siemplify_logger=None):
        """
        :param api_root: api root URI
        :param api_key: client key to generate session tokens
        :param siemplify_logger:
        """
        self.api_root = api_root
        self.api_key = api_key  # client key
        self.siemplify_logger = siemplify_logger

        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers.update({"Client-Key": self.api_key})

        # generate session token
        self.session_token = self._get_session_token()

        self.session.headers.update({"token": self.session_token})
        self.session.headers.update({"Content-Type": "application/json"})

    def _get_session_token(self):
        # get session token
        response = self.session.get(self._get_full_url("get-token"))
        self.validate_response(response, error_msg="Failed to generate session token")
        return response.text

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate response
        :param response: {requests.Response} The response to validate
        :param error_msg: {unicode} Default message to display on error
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            raise CheckPointThreatReputationException(
                f"{error_msg}: {error} {error.response.content}"
            )

        return True

    def _get_full_url(self, url_key):
        """
        Send full url from url identifier.
        :param url_key: {str} The key of the url
        :return: {str} The full url
        """
        self.api_key = self.api_key[:-1] if self.api_key.endswith("/") else self.api_key
        return urljoin(self.api_root, ENDPOINTS[url_key])

    def test_connectivity(self):
        """
        Test connectivity to the CheckPointThreatReputation
        :return: throw exception if failed
        """
        response = self.session.get(self._get_full_url("ping"))
        self.validate_response(response, error_msg=f"Failed to Ping {self.api_root}")

    def get_file_hash_reputation(self, file_hash):
        """
        :param file_hash: file hash to which reputation data is fetched
        :return: FileHashReputationModel data model for file hash reputation response
        """
        response = self.session.post(
            self._get_full_url("get-file-hash-reputation"),
            params={"resource": file_hash},
            json={"request": [{"resource": file_hash}]},
        )
        self.validate_response(
            response, error_msg=f"Failed to get file hash reputation for: {file_hash}"
        )

        return CheckPointTRTransformationLayer.build_file_hash_response_reputation(
            response.json().get("response")
        )

    def get_ip_reputation(self, ip):
        """
        :param ip: ip address to which reputation data is fetched
        :return: IPReputationModel data model for ip reputation response
        """
        response = self.session.post(
            self._get_full_url("get-ip-reputation"),
            params={"resource": ip},
            json={"request": [{"resource": ip}]},
        )
        self.validate_response(
            response, error_msg=f"Failed to get ip reputation for: {ip}"
        )

        return CheckPointTRTransformationLayer.build_ip_response_reputation(
            response.json().get("response")
        )

    def get_host_reputation(self, host):
        """
        :param host: host to which reputation data is fetched
        :return: HostReputationModel data model for host reputation response
        """
        response = self.session.post(
            self._get_full_url("get-host-reputation"),
            params={"resource": host},
            json={"request": [{"resource": host}]},
        )
        self.validate_response(
            response, error_msg=f"Failed to get host reputation for: {host}"
        )

        return CheckPointTRTransformationLayer.build_host_response_reputation(
            response.json().get("response")
        )
