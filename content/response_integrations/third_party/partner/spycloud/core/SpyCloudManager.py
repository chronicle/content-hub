from __future__ import annotations
from urllib.parse import urljoin
import requests
from .constants import ENDPOINTS
from .UtilsManager import validate_response
from .SpyCloudParser import SpyCloudParser


class SpyCloudManager:
    def __init__(self, api_root, api_key, verify_ssl=False, siemplify_logger=None):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} API root of the SpyCloud instance.
        :param api_key: {str} API Key of the SpyCloud instance.
        :param verify_ssl: {bool} If enabled, verify the SSL certificate for the connection to the SpyCloud server is valid.
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.api_key = api_key
        self.logger = siemplify_logger
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.parser = SpyCloudParser()
        self.session.headers.update({"x-api-key": f"{self.api_key}"})

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
        Test connectivity
        """
        request_url = self._get_full_url("ping")
        response = self.session.get(request_url)
        validate_response(response)

    def get_catalogs(self, filter_value, start_time, end_time):
        """
        Get catalogs
        :param filter_value: {str} Value to use in the filter
        :param start_time: {int} Start time filter
        :param end_time: {int} End time filter
        :return: {list} List of Catalog objects
        """
        url = self._get_full_url("get_catalogs")
        params = {"query": filter_value, "since": start_time, "to": end_time}

        results = self._paginate_results(method="GET", url=url, params=params)
        return self.parser.build_list_of_catalog_objects(results)

    def get_breaches(self, breach_type, breach_identifier, catalog_id):
        """
        Get breaches
        :param breach_type: {str} Type of the entity
        :param breach_identifier: {str} Identifier of the entity
        :param catalog_id: {int} Catalog identifier
        :return: {list} List of Breach objects
        """
        url = self._get_full_url(
            "get_breaches", breach_type=breach_type, breach_identifier=breach_identifier
        )
        params = {"source_id": catalog_id} if catalog_id else {}

        results = self.session.get(url, params=params)
        return self.parser.build_list_of_breach_objects(results.json())

    def _paginate_results(
        self, method, url, params=None, body=None, err_msg="Unable to get results"
    ):
        """
        Paginate the results of a request
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param err_msg: {str} The message to display on error
        :return: {list} List of results
        """
        if params is None:
            params = {}

        response = self.session.request(method, url, params=params, json=body)

        validate_response(response, err_msg)
        results = response.json().get("results", [])
        cursor = response.json().get("cursor", "")

        while cursor:
            params.update({"cursor": cursor})

            response = self.session.request(method, url, params=params, json=body)
            validate_response(response, err_msg)
            cursor = response.json().get("cursor", "")
            results.extend(response.json().get("results", []))

        return results
