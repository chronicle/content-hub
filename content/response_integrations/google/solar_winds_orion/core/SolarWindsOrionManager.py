from __future__ import annotations
from .SolarWindsOrionParser import SolarWindsOrionParser
from soar_sdk.SiemplifyDataModel import EntityTypes
import requests
from urllib.parse import urljoin
from .UtilsManager import validate_response
from .SolarWindsOrionConstants import ENDPOINTS, HEADERS, BAD_REQUEST_STATUS_CODE
from .SolarWindsOrionExceptions import FailedQueryException


class SolarWindsOrionManager:

    def __init__(
        self, api_root, username, password, verify_ssl=False, siemplify_logger=None
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: IP address of the SolarWinds Orion instance.
        :param username: Username of the SolarWinds Orion account.
        :param password: Password of the SolarWinds Orion account.
        :param verify_ssl: If enabled, verify the SSL certificate for the connection to the SolarWinds Orion server is valid.
        :param siemplify_logger: Siemplify logger.
        """
        self.api_root = api_root if api_root[-1:] == "/" else api_root + "/"
        self.username = username
        self.password = password
        self.siemplify_logger = siemplify_logger
        self.parser = SolarWindsOrionParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers = HEADERS
        self.session.auth = (self.username, self.password)

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity to the SolarWinds Orion.
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("test_connectivity")
        payload = {
            "query": "SELECT DisplayName FROM Orion.Nodes ORDER BY DisplayName WITH ROWS 1 TO 1"
        }

        response = self.session.post(request_url, json=payload)
        validate_response(response, "Unable to connect to SolarWinds Orion.")

    def execute_query(self, query):
        """
        Execute query in SolarWinds Orion.
        :param query: {str} The query that needs to be executed.
        :return: {list} List of Query Results
        """
        request_url = self._get_full_url("test_connectivity")
        payload = {"query": query}
        response = self.session.post(request_url, json=payload)
        try:
            validate_response(response)
        except Exception as e:
            if response.status_code == BAD_REQUEST_STATUS_CODE:
                raise FailedQueryException(
                    self.parser.build_error_object(response.json()).message
                )
            raise Exception(e)
        return self.parser.build_all_query_results(response.json())

    def build_entity_query(self, query_string, entities, ip_key, hostname_key):
        """
        Build query to execute entity query
        :param query_string: {str} The query to execute
        :param entities: {list} Entities to use in query
        :param ip_key: {str} Key to use with IP entities
        :param hostname_key: {str} Key to use with Hostname entities
        :return: {str} Main query to execute
        """
        where_string = " WHERE {}".format(
            " OR ".join(
                [
                    f"{ip_key if entity.entity_type == EntityTypes.ADDRESS else hostname_key}='{entity.identifier}'"
                    for entity in entities
                ]
            )
        )
        return query_string + where_string
