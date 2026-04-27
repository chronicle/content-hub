from __future__ import annotations
from .ArcSightLoggerParser import ArcSightLoggerParser
from .UtilsManager import validate_response
from .ArcSightLoggerEncryption import encrypt, decrypt
import requests
import urllib.parse

from .ArcSightLoggerExceptions import ArcSightLoggerException, QueryExecutionException

from .constants import ENDPOINTS, LOGIN_HEADERS, REQUEST_HEADERS, LOGIN_DATA, LOGOUT_DATA


class ArcSightLoggerManager:

    def __init__(
        self,
        server_address,
        username,
        password,
        auth_token=None,
        verify_ssl=False,
        siemplify_logger=None,
    ):
        """
        The method is used to init an object of Manager class
        :param server_address: Server address of the ArcSight Logger instance
        :param username: Username of ArcSight Logger account
        :param password: Password of the ArcSight Logger account
        :param auth_token: Auth token for user authorization
        :param verify_ssl: Sets session verification
        :param siemplify_logger: Siemplify logger.
        """
        self.server_address = server_address
        self.username = username
        self.password = password
        self.siemplify_logger = siemplify_logger
        self.parser = ArcSightLoggerParser()
        self.session = requests.session()
        self.session.headers = REQUEST_HEADERS
        self.session.verify = verify_ssl
        self.auth_token = auth_token

    def _get_full_url(self, url_id):
        """
        Send full url from url identifier.
        :param url_id: {unicode} The id of url
        :return: {unicode} The full url
        """
        return urllib.parse.urljoin(self.server_address, ENDPOINTS[url_id])

    def get_auth_token(self, username, password):
        """
        Perform request to generate session.
        :param username: Username of ArcSight Logger account
        :param password: Password of the ArcSight Logger account
        :return: {unicode} The valid Authorization Token
        """
        try:
            login_url = self._get_full_url("login")
            login_data = LOGIN_DATA.format(username, password)
            login_response = self.session.post(
                login_url, headers=LOGIN_HEADERS, data=login_data
            )
            validate_response(login_response)
            return self.parser.get_auth_token(login_response.json())
        except Exception as err:
            raise ArcSightLoggerException(f"ArcSight Logger: {err}")

    def login(self):
        """
        Login to ArcSight Logger
        """
        if self.auth_token:
            return
        self.auth_token = self.get_auth_token(self.username, self.password)

    def logout(self):
        """
        Logout from ArcSight Logger (close open session)
        :return: {bool} True if successful, exception otherwise
        """
        if not self.auth_token:
            return True
        logout_data = LOGOUT_DATA.format(self.auth_token)
        logout_url = self._get_full_url("logout")
        logout_res = self.session.post(
            logout_url, headers=LOGIN_HEADERS, data=logout_data
        )
        validate_response(logout_res, "Unable to logout")
        self.auth_token = None
        return True

    def test_connectivity(self):
        """
        Test connectivity to the ArcSight Logger.
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("search")
        payload = {
            "search_session_id": 2,
            "user_session_id": self.auth_token,
            "query": "",
            "start_time": "2020-03-30T09:52:53.000+03:00",
            "end_time": "2020-03-30T11:52:53.000+03:00",
        }
        response = self.session.post(request_url, json=payload)
        validate_response(response, "Unable to connect to ArcSight Logger.")

    def send_query(
        self, search_id, query, start_time, end_time, local_search, discover_fields
    ):
        """
        Send Query to ArcSight Logger.
        :param search_id: {int} Search session ID
        :param query: {unicode} Query
        :param start_time: {unicode} The start time for fetching
        :param end_time: {unicode} The end time for fetching
        :param local_search: {bool} If True, search is local only, otherwise includes peers in the event search
        :param discover_fields: {bool} If True, search will try to discover fields in the found events
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("search")
        payload = {
            "search_session_id": search_id,
            "user_session_id": self.auth_token,
            "query": query,
            "start_time": start_time,
            "end_time": end_time,
            "local_search": local_search,
            "field_summary": discover_fields,
            "discover_fields": discover_fields,
            "uri_encoded": True,
        }
        response = self.session.post(request_url, json=payload, headers=REQUEST_HEADERS)
        try:
            validate_response(response, "Unable to send query to ArcSight Logger")
        except Exception as e:
            if response.status_code == 409:
                error_message = response.json().get("errors", [])[0].get("message")
                raise QueryExecutionException(
                    f'Unable to execute query "{query}" in ArcSight Logger. Reason: {error_message}'
                )
            else:
                raise Exception(e)
        return self.auth_token

    def get_query_status(self, search_id):
        """
        Get status of the query.
        :param search_id: {int} Search session ID
        :return: Query Status
        """
        request_url = self._get_full_url("status")
        payload = {"search_session_id": search_id, "user_session_id": self.auth_token}
        response = self.session.post(request_url, json=payload, headers=REQUEST_HEADERS)
        validate_response(response, "Unable to get status of the query")
        return self.parser.build_query_status_object(response.json())

    def get_events_from_query(
        self, search_id, include_raw_data, fields_to_fetch, sort, events_limit
    ):
        """
        Fetch events from ArcSight Logger.
        :param search_id: {int} Search session ID
        :param include_raw_data: {bool} If enabled, raw event data is included in the response
        :param fields_to_fetch: {list} List of fields to be fetched
        :param sort: {unicode} Sorting method to use for fetching
        :param events_limit: {int} The amount of events to return
        :return: {list} The query results (list of dicts)
        """
        request_url = self._get_full_url("events")
        raw_data = "true" if include_raw_data else "false"
        sorting = "forward" if sort == "ascending" else "backward"
        limit = min(10000, events_limit)
        payload = {
            "search_session_id": search_id,
            "user_session_id": self.auth_token,
            "include_raw_data": raw_data,
            "dir": sorting,
            "length": limit,
            "offset": 0,
        }

        if fields_to_fetch:
            payload["fields"] = fields_to_fetch

        response = self.session.get(request_url, json=payload)
        validate_response(response, "Unable to get events from query")

        fields = response.json().get("fields", [])
        columns = [f.get("name") for f in fields]
        results = response.json().get("results", [])
        pretty_results = []
        for event in results:
            row_data = {}
            for i, column in enumerate(columns):
                row_data[column] = event[i]
            pretty_results.append(row_data)

        return pretty_results

    @staticmethod
    def decrypt_token_json(encrypted_token, password):
        """
        Decrypt token json.
        :param encrypted_token: The encrypted token to decrypt
        :param password: {str} Password for encryption/decryption
        :return {str} Token json
        """
        return decrypt(encrypted_token, password)

    @staticmethod
    def encrypt_token_json(token_json, password):
        """
        Encrypt token json.
        :param token_json: Token json
        :param password: {str} Password for encryption/decryption
        :return {str} encrypted token json
        """
        return encrypt(token_json, password)
