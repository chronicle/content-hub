from __future__ import annotations

from urllib.parse import urljoin

import requests

from .exceptions import StairwellError, StairwellNotFoundError
from .StairwellParser import StairwellParser

DUMMY_HOSTNAME_FOR_TEST = "www.google.com"

API_ENDPOINTS = {
    "enrich_hash": "/labs/appapi/enrichment/v1/object_event/{file_hash}",
    "enrich_hostname": "/labs/appapi/enrichment/v1/hostname_event/{hostname}",
    "enrich_ip": "/labs/appapi/enrichment/v1/ip_event/{ip}",
}


class StairwellManager:
    def __init__(self, api_key, logger, org_id=None, user_id=None, verify_ssl=True, api_root=None):
        """
        Initializes the StairwellManager.
        :param api_key: Your Stairwell API key.
        :param org_id: The Organization ID to include in headers (optional).
        :param user_id: The User ID (optional, usage based on your API's needs).
        :param verify_ssl: Whether to verify SSL certificates.
        :param api_root: The base URL of the Stairwell API.
        """
        self.api_root = api_root
        self.logger = logger
        self.api_key = api_key
        self.org_id = org_id
        self.user_id = user_id

        self.session = requests.Session()
        self.session.verify = verify_ssl

        # Set common headers for all requests
        self.session.headers.update({
            "Authorization": f"{self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

        # Add Organization-Id header if it's provided
        if self.org_id:
            self.session.headers.update({"Organization-Id": self.org_id})

        # Add User-Id header if it's provided
        if self.user_id:
            self.session.headers.update({"User-Id": self.user_id})

        self.parser = StairwellParser()

    @staticmethod
    def validate_response(
        response,
        error_msg="An error occurred",
        validate_stairwell_status=False,
        handle_404=False,
        check_message=False,
    ):
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            try:
                response.json()
            except (ValueError, TypeError):
                raise StairwellError(f"{error_msg}: {error} - {response.content}")

            if handle_404 and response.status_code == 404:
                raise StairwellNotFoundError
            if check_message:
                error_message = response.json().get("error", {}).get("message", "")
                if error_message:
                    raise StairwellError(f"{error_msg}: {error} - {error_message}")
            raise StairwellError(
                f"{error_msg}: {error} - {response.json().get('error', 'No error message.')}"
            )
        if validate_stairwell_status and not response.status_code == 204:
            raise StairwellError(f"{error_msg} - please check the logs.")

    def test_connectivity(self):
        """
        Ping to server to be sure that connected
        :return: {bool}
        """
        return True if self.get_host(DUMMY_HOSTNAME_FOR_TEST) else False

    def get_host(self, hostname):
        """
        Function that enriches the HOSTNAME entity
        :param hostname: {string} hostname that will be enriched, called device in Stairwell
        :return: {Host} Host object containing enrichment data for a host
        """
        self.logger.info(f"hostname: {hostname}")
        api_url = self._get_full_url("enrich_hostname", hostname=hostname)
        response = self.session.get(api_url)
        self.logger.info(f"API URL: {api_url}")
        self.validate_response(response, f"Unable to enrich the host: {hostname} in Stairwell.")
        results = self.parser.get_host_values(response.json(), hostname, self.logger)
        if results:
            return results[0]

        raise StairwellError("Hostname {} was not found in the Stairwell.".format(hostname))

    def get_ip(self, ip):
        """
        Function that enriches the ADDRESS entity
        :param ip: {string} ip that will be enriched
        :return: {Ip} Ip object containing enrichment data for an ip
        """
        self.logger.info(f"ip: {ip}")
        api_url = self._get_full_url("enrich_ip", ip=ip)
        response = self.session.get(api_url)
        self.logger.info(f"API URL: {api_url}")
        self.validate_response(response, f"Unable to enrich the ip: {ip} in Stairwell.")
        results = self.parser.get_ip_values(response.json(), ip, self.logger)
        if results:
            return results[0]

        raise StairwellError("Ip {} was not found in the Stairwell.".format(ip))

    def get_file(self, file_hash):
        """
        Function that enriches the HASH entity
        :param hash: {string} file hash that will be enriched
        :return:
        """
        self.logger.info(f"file hash: {file_hash}")
        api_url = self._get_full_url("enrich_hash", file_hash=file_hash)
        response = self.session.get(api_url)
        self.logger.info(f"API URL: {api_url}")
        self.validate_response(
            response, f"Unable to enrich the file hash: {file_hash} in Stairwell."
        )
        results = self.parser.get_file_values(response.json(), file_hash, self.logger)
        if results:
            return results[0]

        raise StairwellError("file hash {} was not found in the Stairwell.".format(file_hash))

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier
        :param url_id: {str} the id of url
        :param kwargs: {dict} variables passed for string formatting
        :return: {str} the full url
        """

        return urljoin(self.api_root, API_ENDPOINTS[url_id].format(**kwargs))
