from __future__ import annotations
from urllib.parse import urljoin
import requests
from .UtilsManager import validate_response
from .constants import ENDPOINTS
from .AppSheetParser import AppSheetParser
import json


class AppSheetManager:
    def __init__(
        self, api_root, app_id, access_token, verify_ssl, siemplify_logger=None
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} Api Root to use for connection
        :param app_id: {str} App ID to use for connection
        :param access_token: {str} Access token to use for connection
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root
        self.app_id = app_id
        self.access_token = access_token
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.parser = AppSheetParser()
        self.session = requests.session()
        self.session.verify = verify_ssl

        self.session.headers.update({"ApplicationAccessKey": access_token})

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
        request_url = self._get_full_url("ping", app_id=self.app_id)
        response = self.session.get(request_url)
        validate_response(response)

    def delete_record(self, table_name, query):
        """
        Function to delete a record
        :param table_name: {str} Table name from which the record should be deleted
        :param query: {str} Query to use for removal of the record
        :return: {dict} The raw output
        """
        request_url = self._get_full_url(
            "record_management", app_id=self.app_id, table_name=table_name
        )

        self.session.headers.update({"Content-Type": "application/json"})
        try:
            query = json.loads(query)
        except Exception:
            raise Exception("Invalid JSON object provided. Please check the structure.")

        payload = json.dumps({"Action": "Delete", "Properties": {}, "Rows": [query]})

        response = self.session.post(request_url, data=payload)
        validate_response(response)
        return response.json().get("Rows")

    def add_record(self, table_name, query):
        """
        Function to add a record
        :param table_name: {str} Table name from which the record should be added
        :param query: {str} Query to use to add the record
        :return: {dict} The raw output
        """
        request_url = self._get_full_url(
            "record_management", app_id=self.app_id, table_name=table_name
        )

        self.session.headers.update({"Content-Type": "application/json"})
        try:
            query = json.loads(query)
        except Exception:
            raise Exception("Invalid JSON object provided. Please check the structure.")

        payload = json.dumps({"Action": "Add", "Properties": {}, "Rows": [query]})

        response = self.session.post(request_url, data=payload)
        validate_response(response)
        return response.json().get("Rows")

    def update_record(self, table_name, query):
        """
        Function to update a record
        :param table_name: {str} Table name from which the record should be update
        :param query: {str} Query to use for update of the record
        :return: {dict} The raw output
        """
        request_url = self._get_full_url(
            "record_management", app_id=self.app_id, table_name=table_name
        )

        self.session.headers.update({"Content-Type": "application/json"})
        try:
            query = json.loads(query)
        except Exception:
            raise Exception("Invalid JSON object provided. Please check the structure.")

        payload = json.dumps({"Action": "Edit", "Properties": {}, "Rows": [query]})

        response = self.session.post(request_url, data=payload)
        validate_response(response)
        return response.json().get("Rows")

    def search_records(self, table_name, query):
        """
        Function to search for a record
        :param table_name: {str} Table name in which the record should be seachable
        :param query: {str} Selector Query, it's not a JSON Object
        :return: {dict} The raw output
        """
        request_url = self._get_full_url(
            "record_management", app_id=self.app_id, table_name=table_name
        )

        self.session.headers.update({"Content-Type": "application/json"})

        payload = json.dumps(
            {"Action": "Find", "Properties": {"Selector": query}, "Rows": []}
        )

        response = self.session.post(request_url, data=payload)
        validate_response(response)

        return self.parser.build_search_records_object(response.json())

    def list_tables(self):
        """
        List tables
        :return: {list} List Tables
        """
        request_url = self._get_full_url("list_tables", app_id=self.app_id)

        response = self.session.get(request_url)
        validate_response(response, "Unable to list tables")
        return self.parser.build_table_list(response.json().get("Tables", []))
