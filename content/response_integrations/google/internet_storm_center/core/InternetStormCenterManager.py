from __future__ import annotations
from urllib.parse import urljoin
import requests
from .constants import ENDPOINTS, API_ROOT
from .UtilsManager import validate_response
from .InternetStormCenterParser import InternetStormCenterParser


class InternetStormCenterManager:
    def __init__(self, email_address, verify_ssl=False, siemplify_logger=None):
        """
        The method is used to init an object of Manager class
        :param email_address: {str} Email address that will be associated with API requests.
        :param verify_ssl: {bool} If enabled, verify the SSL certificate for the connection to the server is valid.
        :param siemplify_logger: Siemplify logger
        """
        self.email_address = email_address
        self.logger = siemplify_logger
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.parser = InternetStormCenterParser()
        self.session.headers.update({"User-Agent": self.email_address})

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param root_url: {str} The API root for the request
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(API_ROOT, ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity
        """
        request_url = self._get_full_url("ping")
        response = self.session.get(request_url)
        validate_response(response)

    def get_device(self, ip_address):
        """
        Get device
        :param ip_address: {str} The ip address to get device for
        :return: {Device}
        """
        request_url = self._get_full_url("get_device", address=ip_address)
        response = self.session.get(request_url)
        validate_response(response)

        return self.parser.build_device_obj(response.json())
